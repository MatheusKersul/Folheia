"""Operações no Amazon RDS: adoção, ajustes, criação e exclusão de instâncias."""

from __future__ import annotations

import time

from .config import Settings, tags


def security_group_ids(instance: dict) -> list[str]:
    """Extrai os Security Groups de uma resposta de ``describe_db_instances``.

    Atenção: na resposta a chave é ``VpcSecurityGroups`` (lista de objetos);
    ``VpcSecurityGroupIds`` existe apenas como parâmetro de requisição.
    """
    groups = instance.get("VpcSecurityGroups") or []
    return [
        group["VpcSecurityGroupId"]
        for group in groups
        if group.get("VpcSecurityGroupId")
    ]


def find_instance(rds, identifier: str | None = None, endpoint: str | None = None) -> dict | None:
    """Localiza uma instância por identificador ou por endpoint (DNS do RDS)."""
    if identifier:
        try:
            return rds.describe_db_instances(DBInstanceIdentifier=identifier)["DBInstances"][0]
        except rds.exceptions.DBInstanceNotFoundFault:
            pass

    if endpoint:
        paginator = rds.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for instance in page["DBInstances"]:
                address = (instance.get("Endpoint") or {}).get("Address")
                if address and address.lower() == endpoint.lower():
                    return instance
    return None


def wait_available(rds, identifier: str, timeout_minutes: int = 45) -> dict:
    print(f"  aguardando {identifier} ficar 'available' (pode levar 10-20 min)...")
    waiter = rds.get_waiter("db_instance_available")
    waiter.wait(
        DBInstanceIdentifier=identifier,
        WaiterConfig={"Delay": 20, "MaxAttempts": max(3, timeout_minutes * 3)},
    )
    return rds.describe_db_instances(DBInstanceIdentifier=identifier)["DBInstances"][0]


def describe_summary(instance: dict) -> str:
    endpoint = instance.get("Endpoint") or {}
    return (
        f"{instance['DBInstanceIdentifier']} | "
        f"{instance.get('Engine')} {instance.get('EngineVersion')} | "
        f"{instance.get('DBInstanceClass')} | AZ {instance.get('AvailabilityZone')} | "
        f"{endpoint.get('Address')}:{endpoint.get('Port')} | "
        f"público={instance.get('PubliclyAccessible')} | "
        f"backup={instance.get('BackupRetentionPeriod')}d"
    )


def ensure_primary_settings(rds, instance: dict, settings: Settings, dry_run: bool) -> dict:
    """Garante os pré-requisitos de uma read replica na instância primária."""
    changes: dict[str, object] = {}
    if settings.publicly_accessible and not instance.get("PubliclyAccessible"):
        changes["PubliclyAccessible"] = True
    if instance.get("BackupRetentionPeriod", 0) < settings.backup_retention:
        changes["BackupRetentionPeriod"] = settings.backup_retention

    if not changes:
        print("  instância já atende aos requisitos (pública, backup ativo)")
        return instance

    print(f"  ajustando {instance['DBInstanceIdentifier']}: {', '.join(sorted(changes))}")
    if dry_run:
        print("  [dry-run] nenhuma alteração aplicada")
        return instance

    if instance.get("DBInstanceStatus") not in ("available", None):
        wait_available(rds, instance["DBInstanceIdentifier"])

    rds.modify_db_instance(
        DBInstanceIdentifier=instance["DBInstanceIdentifier"],
        ApplyImmediately=True,
        **changes,
    )
    updated = wait_available(rds, instance["DBInstanceIdentifier"])
    print(f"  instância atualizada: {describe_summary(updated)}")
    return updated


def ensure_db_subnet_group(rds, settings: Settings, subnet_ids: list[str], dry_run: bool) -> str:
    name = settings.db_subnet_group_name
    try:
        rds.describe_db_subnet_groups(DBSubnetGroupName=name)
        print(f"  DB subnet group existente: {name}")
        return name
    except rds.exceptions.DBSubnetGroupNotFoundFault:
        pass

    if dry_run:
        print(f"  [dry-run] criaria DB subnet group {name} com {len(subnet_ids)} sub-redes")
        return name

    rds.create_db_subnet_group(
        DBSubnetGroupName=name,
        DBSubnetGroupDescription="Sub-redes do experimento de replicacao RDS (Folheia)",
        SubnetIds=subnet_ids,
        Tags=tags(name),
    )
    print(f"  DB subnet group criado: {name}")
    return name


def create_primary(
    rds, settings: Settings, username: str, password: str, network: dict, dry_run: bool
) -> dict:
    identifier = settings.primary_instance_id
    existing = find_instance(rds, identifier=identifier)
    if existing:
        print(f"  primária já existe, reutilizando: {describe_summary(existing)}")
        return existing

    if dry_run:
        print(
            f"  [dry-run] criaria primária {identifier} ({settings.instance_class}, "
            f"{settings.engine}, público={settings.publicly_accessible})"
        )
        return {
            "DBInstanceIdentifier": identifier,
            "DBInstanceStatus": "dry-run",
            "Engine": settings.engine,
            "EngineVersion": settings.engine_version or "(default)",
            "DBInstanceClass": settings.instance_class,
            "AvailabilityZone": "(a definir)",
            "PubliclyAccessible": settings.publicly_accessible,
            "BackupRetentionPeriod": settings.backup_retention,
            "VpcSecurityGroupIds": [network.get("security_group_id")],
            "DBSubnetGroupName": settings.db_subnet_group_name,
            "Endpoint": {"Address": "<primaria>.rds.amazonaws.com", "Port": settings.db_port},
        }

    params: dict[str, object] = {
        "DBInstanceIdentifier": identifier,
        "Engine": settings.engine,
        "DBInstanceClass": settings.instance_class,
        "MasterUsername": username,
        "MasterUserPassword": password,
        "AllocatedStorage": settings.allocated_storage,
        "StorageType": settings.storage_type,
        "PubliclyAccessible": settings.publicly_accessible,
        "BackupRetentionPeriod": settings.backup_retention,
        "MultiAZ": False,
        "AutoMinorVersionUpgrade": True,
        "CopyTagsToSnapshot": True,
        "DeletionProtection": False,
        "DBSubnetGroupName": settings.db_subnet_group_name,
        "VpcSecurityGroupIds": [network["security_group_id"]],
        "Tags": tags(identifier),
    }
    if settings.engine_version:
        params["EngineVersion"] = settings.engine_version

    print(f"  criando primária {identifier} ({settings.instance_class})...")
    try:
        rds.create_db_instance(**params)
    except rds.exceptions.DBInstanceAlreadyExistsFault:
        print("  primária já existia (corrida); reutilizando")
        return wait_available(rds, identifier)

    instance = wait_available(rds, identifier)
    print(f"  primária disponível: {describe_summary(instance)}")
    return instance


def create_replica(
    rds, settings: Settings, primary: dict, network: dict, dry_run: bool
) -> dict:
    identifier = settings.replica_instance_id
    existing = find_instance(rds, identifier=identifier)
    if existing:
        print(f"  réplica já existe, reutilizando: {describe_summary(existing)}")
        if existing.get("DBInstanceStatus") == "available":
            return existing
        return wait_available(rds, identifier)

    availability_zone = settings.replica_az or primary.get("AvailabilityZone") or "(mesma AZ da primária)"
    group_ids = security_group_ids(primary) or (
        [network["security_group_id"]] if network.get("security_group_id") else []
    )

    if dry_run:
        print(
            f"  [dry-run] criaria read replica {identifier} de "
            f"{primary['DBInstanceIdentifier']} em {availability_zone}"
        )
        return {
            "DBInstanceIdentifier": identifier,
            "DBInstanceStatus": "dry-run",
            "Engine": primary.get("Engine"),
            "EngineVersion": primary.get("EngineVersion"),
            "DBInstanceClass": settings.instance_class,
            "AvailabilityZone": availability_zone,
            "PubliclyAccessible": settings.publicly_accessible,
            "Endpoint": {"Address": "<replica>.rds.amazonaws.com", "Port": settings.db_port},
        }

    params: dict[str, object] = {
        "DBInstanceIdentifier": identifier,
        "SourceDBInstanceIdentifier": primary["DBInstanceIdentifier"],
        "DBInstanceClass": settings.instance_class,
        "PubliclyAccessible": settings.publicly_accessible,
        "AutoMinorVersionUpgrade": True,
        "CopyTagsToSnapshot": True,
        "Tags": tags(identifier),
    }
    if settings.replica_az:
        params["AvailabilityZone"] = settings.replica_az
    elif primary.get("AvailabilityZone"):
        params["AvailabilityZone"] = primary["AvailabilityZone"]
    if group_ids:
        params["VpcSecurityGroupIds"] = [
            group_id for group_id in group_ids if group_id and not str(group_id).endswith("dry-run")
        ]

    print(f"  criando read replica {identifier} de {primary['DBInstanceIdentifier']}...")
    try:
        rds.create_db_instance_read_replica(**params)
    except rds.exceptions.DBInstanceAlreadyExistsFault:
        print("  réplica já existia (corrida); reutilizando")
        return wait_available(rds, identifier)

    instance = wait_available(rds, identifier)
    print(f"  réplica disponível: {describe_summary(instance)}")
    return instance


def delete_instance(rds, identifier: str, dry_run: bool, timeout_minutes: int = 30) -> None:
    existing = find_instance(rds, identifier=identifier)
    if not existing:
        print(f"  {identifier} já não existe")
        return

    if dry_run:
        print(f"  [dry-run] removeria {identifier} (SkipFinalSnapshot=True)")
        return

    print(f"  removendo {identifier}...")
    try:
        rds.delete_db_instance(
            DBInstanceIdentifier=identifier,
            SkipFinalSnapshot=True,
            DeleteAutomatedBackups=True,
        )
    except rds.exceptions.DBInstanceNotFoundFault:
        print(f"  {identifier} já não existe")
        return

    waiter = rds.get_waiter("db_instance_deleted")
    waiter.wait(
        DBInstanceIdentifier=identifier,
        WaiterConfig={"Delay": 20, "MaxAttempts": max(3, timeout_minutes * 3)},
    )
    print(f"  {identifier} removido")


def wait_for_replica(
    rds, identifier: str, timeout_seconds: int = 900, interval_seconds: int = 10
) -> dict:
    """Espera a réplica existir e estar disponível (usado no teste)."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        instance = find_instance(rds, identifier=identifier)
        if instance and instance.get("DBInstanceStatus") == "available":
            return instance
        time.sleep(interval_seconds)
    raise SystemExit(f"tempo esgotado esperando a réplica {identifier} ficar disponível")
