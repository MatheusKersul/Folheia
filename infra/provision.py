#!/usr/bin/env python3
"""Provisiona o cenário de replicação (Master + Read Replica) no Amazon RDS.

Modos:
    --create-new                 cria VPC, sub-redes, security group, primária e réplica
    --adopt-existing INSTANCE    adota uma primária já existente e cria apenas a réplica

Exemplos:
    python infra/provision.py --inspect-secret
    python infra/provision.py --adopt-existing acervo-1 --dry-run
    python infra/provision.py --adopt-existing acervo-1
    python infra/provision.py --create-new

O script é idempotente: cada etapa consulta a AWS antes de criar recursos.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from infra.aws import config as cfg
from infra.aws import db as db_mod
from infra.aws import net
from infra.aws import rds as rds_mod
from infra.aws import secrets as secrets_mod
from infra.aws import state as state_mod

TOTAL_STEPS = 6


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Provisiona Master + Read Replica PostgreSQL no Amazon RDS (Boto3).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--create-new",
        action="store_true",
        help="cria toda a infraestrutura (VPC, sub-redes, SG, primária, réplica)",
    )
    parser.add_argument(
        "--adopt-existing",
        metavar="INSTANCE_ID",
        help="usa uma instância RDS PostgreSQL já existente como primária",
    )
    parser.add_argument(
        "--inspect-secret",
        action="store_true",
        help="mostra host/porta/banco/usuário do segredo (sem exibir a senha) e encerra",
    )
    parser.add_argument(
        "--publish-secret",
        action="store_true",
        help="grava a senha no segredo PUBLISH_SECRET_NAME (cria se não existir)",
    )
    parser.add_argument("--dry-run", action="store_true", help="mostra o plano sem alterar nada")
    parser.add_argument("--skip-replica", action="store_true", help="não cria a read replica")
    parser.add_argument("--skip-db", action="store_true", help="não cria banco/tabela")
    parser.add_argument("--replica-id", help="identificador da read replica")
    parser.add_argument("--instance-class", help="classe RDS (ex.: db.t4g.micro)")
    parser.add_argument("--allowed-cidr", help="CIDR liberado no security group (ex.: 0.0.0.0/0)")
    parser.add_argument(
        "--replica-az",
        help="AZ da réplica (padrão: mesma AZ da primária)",
    )
    return parser.parse_args(argv)


def step(number: int, title: str) -> None:
    print(f"[{number}/{TOTAL_STEPS}] {title}")


def inspect_secret(settings: cfg.Settings) -> int:
    if not settings.secret_arn:
        raise SystemExit("DB_SECRET_ARN não configurado em infra/.env")

    metadata, safe = secrets_mod.inspect(settings, settings.secret_arn)
    print("Inspeção do segredo (a senha NUNCA é exibida)")
    print(f"  ARN        : {metadata.get('ARN')}")
    print(f"  nome       : {metadata.get('Name')}")
    print(f"  atualizado : {metadata.get('LastChangedDate')}")
    for key in ("username", "host", "port", "dbname", "engine"):
        print(f"  {key:<10} : {safe.get(key, '(ausente)')}")

    secret_host = safe.get("host")
    if secret_host and settings.primary_endpoint:
        same = secret_host.lower() == settings.primary_endpoint.lower()
        print()
        if same:
            print("  o host do segredo corresponde ao endpoint configurado como primária")
        else:
            print("  [atenção] o host do segredo é DIFERENTE da primária configurada:")
            print(f"    segredo  : {secret_host}")
            print(f"    primária : {settings.primary_endpoint}")
            print("    Confirme qual instância usar antes de rodar o provisionamento.")
    return 0


def adopt_primary(rds, settings: cfg.Settings, instance_id: str) -> tuple[dict, dict]:
    instance = rds_mod.find_instance(
        rds, identifier=instance_id, endpoint=settings.primary_endpoint
    )
    if not instance:
        raise SystemExit(
            f"instância '{instance_id}' não encontrada na região {settings.region}.\n"
            "Verifique o identificador com: aws rds describe-db-instances --query "
            "\"DBInstances[].DBInstanceIdentifier\""
        )

    print(f"  encontrada: {rds_mod.describe_summary(instance)}")
    if instance.get("Engine") != "postgres":
        raise SystemExit(
            f"engine {instance.get('Engine')!r} não aceita: o PRD exige PostgreSQL"
        )
    if instance.get("ReadReplicaSourceDBInstanceIdentifier"):
        raise SystemExit("a instância informada já é uma read replica; informe a primária")

    subnet_group = instance.get("DBSubnetGroup") or {}
    group_ids = rds_mod.security_group_ids(instance)
    network = {
        "mode": "adopted",
        "created_by_script": False,
        "vpc_id": subnet_group.get("VpcId"),
        "db_subnet_group": subnet_group.get("DBSubnetGroupName"),
        "subnet_ids": [
            item.get("SubnetIdentifier") for item in subnet_group.get("Subnets", [])
        ],
        "security_group_id": group_ids[0] if group_ids else None,
        "security_group_ids": group_ids,
    }
    print(
        f"  rede: VPC={network['vpc_id']} subnet group={network['db_subnet_group']} "
        f"SG={', '.join(group_ids) or '(nenhum)'}"
    )
    return instance, network


def create_network(ec2, rds, settings: cfg.Settings, dry_run: bool) -> dict:
    vpc_id = net.ensure_vpc(ec2, settings, dry_run)
    subnet_ids = net.ensure_subnets(ec2, vpc_id, settings, dry_run)
    internet_gateway_id = net.ensure_igw(ec2, vpc_id, dry_run)
    route_table_id = net.ensure_route_table(ec2, vpc_id, internet_gateway_id, subnet_ids, dry_run)
    security_group_id = net.ensure_security_group(ec2, vpc_id, dry_run)

    network = {
        "mode": "created",
        "created_by_script": True,
        "vpc_id": vpc_id,
        "subnet_ids": subnet_ids,
        "internet_gateway_id": internet_gateway_id,
        "route_table_id": route_table_id,
        "security_group_id": security_group_id,
        "security_group_ids": [security_group_id],
        "db_subnet_group": settings.db_subnet_group_name,
    }

    net.ensure_ingress(ec2, [security_group_id], settings.allowed_cidr, settings.db_port, dry_run)
    rds_mod.ensure_db_subnet_group(rds, settings, subnet_ids, dry_run)
    return network


def write_generated_env(settings: cfg.Settings, primary: dict, replica: dict | None) -> None:
    master_host = (primary.get("Endpoint") or {}).get("Address", "")
    replica_host = ((replica or {}).get("Endpoint") or {}).get("Address", "")
    try:
        cert_display = settings.ca_bundle.relative_to(cfg.REPO_ROOT).as_posix()
    except ValueError:
        cert_display = str(settings.ca_bundle)

    lines = [
        "# Gerado por infra/provision.py - nao edite manualmente.",
        f"AWS_REGION={settings.region}",
        f"DB_NAME={settings.db_name}",
        f"DB_USER={settings.db_user}",
        f"DB_PORT={settings.db_port}",
        f"MASTER_HOST={master_host}",
        f"REPLICA_HOST={replica_host}",
        f"SSL_MODE={settings.ssl_mode}",
        f"SSL_ROOT_CERT={cert_display}",
        "",
    ]
    cfg.GENERATED_ENV.write_text("\n".join(lines), encoding="utf-8")
    print(f"  endpoints gravados em {cfg.GENERATED_ENV}")


def print_summary(settings: cfg.Settings, primary: dict, replica: dict | None, dry_run: bool) -> None:
    master = (primary.get("Endpoint") or {}).get("Address") or "<pendente>"
    print()
    print("=" * 78)
    print("Resumo")
    print("=" * 78)
    print(f"  MASTER  : {master}:{settings.db_port} (banco {settings.db_name})")
    if replica:
        address = (replica.get("Endpoint") or {}).get("Address") or "<pendente>"
        print(f"  REPLICA : {address}:{settings.db_port}")
        print(f"  AZ       : master={primary.get('AvailabilityZone')} "
              f"replica={replica.get('AvailabilityZone')}")
    else:
        print("  REPLICA : (não provisionada)")

    if dry_run:
        print()
        print("  dry-run: nenhuma alteração foi aplicada na AWS")
        return

    print()
    print("  Próximos passos:")
    print("    python scripts/replication_test.py --rows 1000 --cleanup")
    print("    python infra/destroy.py            # limpeza após a apresentação")
    print("=" * 78)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.create_new and args.adopt_existing:
        raise SystemExit("escolha apenas um modo: --create-new OU --adopt-existing")

    settings = cfg.Settings.from_env().with_overrides(
        replica_instance_id=args.replica_id,
        instance_class=args.instance_class,
        allowed_cidr=args.allowed_cidr,
        replica_az=args.replica_az,
    )

    print("=" * 78)
    print("Folheia · provisionamento de replicação RDS (PostgreSQL)")
    print("=" * 78)
    print(f"  região   : {settings.region}")
    print(f"  profile  : {settings.profile or '(default)'}")
    print(f"  execução : {'DRY-RUN (sem alterações)' if args.dry_run else 'APLICAR'}")
    print(f"  banco    : {settings.db_name} (usuário {settings.db_user})")
    print(
        "  primária : "
        + (f"adotar {args.adopt_existing}" if args.adopt_existing else f"criar {settings.primary_instance_id}")
    )
    print(
        f"  réplica  : {settings.replica_instance_id} em "
        f"{settings.replica_az or 'mesma AZ da primária'}"
    )
    print(f"  acesso   : {settings.allowed_cidr}:{settings.db_port} (Security Group)")
    print()

    try:
        identity = cfg.identity(settings)
    except Exception as exc:  # credenciais ausentes/inválidas
        raise SystemExit(
            "não foi possível autenticar na AWS.\n"
            "Configure a access key (aws configure) ou um AWS_PROFILE válido.\n"
            f"erro: {type(exc).__name__}: {exc}"
        ) from exc

    account = identity.get("Account")
    print(f"  conta AWS : {account}")
    print(f"  identidade: {identity.get('Arn')}")
    secret_account = cfg.account_from_arn(settings.secret_arn)
    if secret_account and account and secret_account != account:
        print(
            f"  [aviso] o segredo pertence à conta {secret_account}, "
            f"diferente da conta atual ({account})"
        )
    print()

    if args.inspect_secret:
        return inspect_secret(settings)

    ec2 = cfg.client(settings, "ec2")
    rds = cfg.client(settings, "rds")

    if args.dry_run:
        user = settings.db_user
        password = None
        print("  credencial: não resolvida (dry-run)")
        print()
    else:
        if not args.adopt_existing and settings.secret_arn:
            print(
                "  [nota] ao criar uma primária nova, o segredo existente não define a senha "
                "(use DB_PASSWORD ou o prompt)"
            )
        user, password = secrets_mod.resolve_credentials(
            settings, allow_secret=bool(args.adopt_existing)
        )
        print()

    # ------------------------------------------------------------------ #
    # 1) rede
    # ------------------------------------------------------------------ #
    step(1, "rede e conectividade")
    if args.adopt_existing:
        primary, network = adopt_primary(rds, settings, args.adopt_existing)
    else:
        network = create_network(ec2, rds, settings, args.dry_run)
        primary = None

    # ------------------------------------------------------------------ #
    # 2) requisitos da primária
    # ------------------------------------------------------------------ #
    step(2, "validação da primária (backup automático e acesso público)")
    if primary is None:
        print("  a primária será criada já com backup e acesso público habilitados")
    else:
        primary = rds_mod.ensure_primary_settings(rds, primary, settings, args.dry_run)
        net.ensure_ingress(
            ec2,
            network["security_group_ids"],
            settings.allowed_cidr,
            settings.db_port,
            args.dry_run,
        )

    # ------------------------------------------------------------------ #
    # 3) primária
    # ------------------------------------------------------------------ #
    step(3, "instância primária")
    if primary is None:
        primary = rds_mod.create_primary(
            rds, settings, user, password or "", network, args.dry_run
        )
    else:
        print(f"  primária em uso: {primary['DBInstanceIdentifier']}")

    endpoint = (primary.get("Endpoint") or {}).get("Address")

    # ------------------------------------------------------------------ #
    # 4) banco + tabela
    # ------------------------------------------------------------------ #
    step(4, "banco e tabela de teste")
    if args.skip_db:
        print("  pulado (--skip-db)")
    elif args.dry_run:
        print(f"  [dry-run] criaria o banco '{settings.db_name}' e a tabela 'users'")
    else:
        if not endpoint:
            raise SystemExit("a primária ainda não expõe endpoint; aguarde e rode novamente")
        assert password is not None
        db_mod.wait_connectable(settings, endpoint, password, user)
        db_mod.ensure_database(settings, endpoint, user, password)
        db_mod.ensure_users_table(settings, endpoint, user, password)

    # ------------------------------------------------------------------ #
    # 5) read replica
    # ------------------------------------------------------------------ #
    step(5, "read replica")
    replica: dict | None = None
    if args.skip_replica:
        print("  pulado (--skip-replica)")
    else:
        replica = rds_mod.create_replica(rds, settings, primary, network, args.dry_run)

    # ------------------------------------------------------------------ #
    # 6) segredo + estado
    # ------------------------------------------------------------------ #
    step(6, "segredo e estado local")
    created_secret_arn: str | None = None
    should_publish = args.publish_secret or (
        not args.adopt_existing and not settings.secret_arn and not args.dry_run
    )
    if should_publish:
        if args.dry_run:
            print(f"  [dry-run] publicaria a senha no segredo {settings.publish_secret_name}")
        else:
            assert password is not None
            created_secret_arn = secrets_mod.upsert(
                settings, settings.publish_secret_name, user, password, dry_run=False
            )
    else:
        if settings.secret_arn:
            print(f"  segredo existente mantido: {settings.secret_arn}")
        else:
            print("  nenhum segredo configurado (defina DB_SECRET_ARN ou use --publish-secret)")

    if args.dry_run:
        print_summary(settings, primary, replica, dry_run=True)
        return 0

    state = state_mod.load()
    state_mod.record(
        state,
        "run",
        account=account,
        region=settings.region,
        profile=settings.profile,
        mode=network.get("mode"),
        db_name=settings.db_name,
    )
    state_mod.record(
        state,
        "primary",
        identifier=primary["DBInstanceIdentifier"],
        endpoint=endpoint,
        port=(primary.get("Endpoint") or {}).get("Port", settings.db_port),
        availability_zone=primary.get("AvailabilityZone"),
        engine=primary.get("Engine"),
        engine_version=primary.get("EngineVersion"),
        instance_class=primary.get("DBInstanceClass"),
        security_group_ids=rds_mod.security_group_ids(primary),
        db_subnet_group=(primary.get("DBSubnetGroup") or {}).get("DBSubnetGroupName"),
        adopted=bool(args.adopt_existing),
    )
    if replica:
        state_mod.record(
            state,
            "replica",
            identifier=replica.get("DBInstanceIdentifier", settings.replica_instance_id),
            endpoint=(replica.get("Endpoint") or {}).get("Address"),
            port=(replica.get("Endpoint") or {}).get("Port", settings.db_port),
            availability_zone=replica.get("AvailabilityZone"),
            instance_class=replica.get("DBInstanceClass"),
        )
    state_mod.record(state, "network", **network)
    state_mod.record(state, "database", name=settings.db_name, table="users")
    if created_secret_arn:
        state_mod.record(
            state,
            "secret",
            arn=created_secret_arn,
            name=settings.publish_secret_name,
            created_by_script=True,
        )
    state_mod.save(state)

    write_generated_env(settings, primary, replica)
    print_summary(settings, primary, replica, dry_run=False)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\ninterrompido pelo usuário")
        raise SystemExit(130)
