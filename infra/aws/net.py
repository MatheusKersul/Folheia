"""Recursos de rede: VPC, sub-redes públicas, IGW, rotas e Security Group.

Todas as funções são *check-before-create*: rodar o script duas vezes não
recria nem duplica recursos (requisito de idempotência do PRD).
"""

from __future__ import annotations

import ipaddress
import time

from .config import PROJECT, SG_RULE_DESCRIPTION, Settings, tags

SG_NAME = "folheia-replication-sg"


def _retry(action, label: str, attempts: int = 6, delay: int = 5, **kwargs) -> bool:
    """Repete uma remoção: a AWS pode levar alguns segundos para liberar dependências."""
    for attempt in range(1, attempts + 1):
        try:
            action(**kwargs)
            return True
        except Exception as exc:
            if attempt == attempts:
                print(f"    [aviso] {label}: {type(exc).__name__}: {exc}")
                return False
            print(f"    {label}: aguardando liberação de dependências (tentativa {attempt})")
            time.sleep(delay)
    return False


def _project_filter() -> list[dict]:
    return [{"Name": "tag:Project", "Values": [PROJECT]}]


def _tag_specs(resource_type: str, name: str) -> list[dict]:
    return [{"ResourceType": resource_type, "Tags": tags(name)}]


def _ignore_missing(callable_, *args, **kwargs):
    """Executa e ignora erros de recurso já removido."""
    try:
        return callable_(*args, **kwargs)
    except Exception as exc:  # boto3 expõe dezenas de exceções distintas
        print(f"    [aviso] {type(exc).__name__}: {exc}")
        return None


# --------------------------------------------------------------------------- #
# VPC / sub-redes / IGW / rotas
# --------------------------------------------------------------------------- #
def find_vpc(ec2) -> str | None:
    response = ec2.describe_vpcs(Filters=_project_filter())
    vpcs = response.get("Vpcs", [])
    return vpcs[0]["VpcId"] if vpcs else None


def ensure_vpc(ec2, settings: Settings, dry_run: bool) -> str:
    vpc_id = find_vpc(ec2)
    if vpc_id:
        print(f"  VPC existente: {vpc_id}")
        return vpc_id

    if dry_run:
        print(f"  [dry-run] criaria VPC {settings.vpc_cidr}")
        return "vpc-dry-run"

    response = ec2.create_vpc(
        CidrBlock=settings.vpc_cidr,
        TagSpecifications=_tag_specs("vpc", "folheia-replication-vpc"),
    )
    vpc_id = response["Vpc"]["VpcId"]
    ec2.get_waiter("vpc_available").wait(VpcIds=[vpc_id])
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={"Value": True})
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={"Value": True})
    print(f"  VPC criada: {vpc_id} ({settings.vpc_cidr})")
    return vpc_id


def ensure_subnets(ec2, vpc_id: str, settings: Settings, dry_run: bool) -> list[str]:
    existing = ec2.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}] + _project_filter()
    )["Subnets"]
    if len(existing) >= 2:
        ordered = sorted(existing, key=lambda item: item["AvailabilityZone"])
        ids = [item["SubnetId"] for item in ordered[:2]]
        print(f"  sub-redes existentes: {', '.join(ids)}")
        return ids

    if dry_run:
        print(f"  [dry-run] criaria 2 sub-redes /24 em {settings.vpc_cidr} (2 AZs)")
        return ["subnet-dry-run-a", "subnet-dry-run-b"]

    zones = [
        zone["ZoneName"]
        for zone in ec2.describe_availability_zones(
            Filters=[{"Name": "state", "Values": ["available"]}]
        )["AvailabilityZones"]
    ]
    if len(zones) < 2:
        raise SystemExit("a região escolhida precisa de pelo menos 2 AZs disponíveis")

    network = ipaddress.ip_network(settings.vpc_cidr)
    reserved = {item["CidrBlock"] for item in existing}
    used_zones = {item["AvailabilityZone"] for item in existing}
    blocks = [
        block for block in network.subnets(new_prefix=24) if str(block) not in reserved
    ][: 2 - len(existing)]
    free_zones = [zone for zone in sorted(zones) if zone not in used_zones][: len(blocks)]

    ids: list[str] = [item["SubnetId"] for item in existing]
    for zone, block in zip(free_zones, blocks):
        response = ec2.create_subnet(
            VpcId=vpc_id,
            CidrBlock=str(block),
            AvailabilityZone=zone,
            TagSpecifications=_tag_specs("subnet", f"folheia-replication-{zone}"),
        )
        subnet_id = response["Subnet"]["SubnetId"]
        print(f"  sub-rede criada: {subnet_id} ({zone} / {block})")
        ids.append(subnet_id)
    return ids


def ensure_igw(ec2, vpc_id: str, dry_run: bool) -> str:
    existing = ec2.describe_internet_gateways(
        Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}]
    )["InternetGateways"]
    if existing:
        igw_id = existing[0]["InternetGatewayId"]
        print(f"  internet gateway existente: {igw_id}")
        return igw_id

    if dry_run:
        print("  [dry-run] criaria internet gateway + attach")
        return "igw-dry-run"

    igw_id = ec2.create_internet_gateway(
        TagSpecifications=_tag_specs("internet-gateway", "folheia-replication-igw")
    )["InternetGateway"]["InternetGatewayId"]
    ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
    print(f"  internet gateway criado e anexado: {igw_id}")
    return igw_id


def ensure_route_table(
    ec2, vpc_id: str, igw_id: str, subnet_ids: list[str], dry_run: bool
) -> str:
    tables = ec2.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}] + _project_filter()
    )["RouteTables"]

    if tables:
        table = tables[0]
        route_table_id = table["RouteTableId"]
        routes = table.get("Routes", [])
        associations = table.get("Associations", [])
        print(f"  route table existente: {route_table_id}")
    else:
        if dry_run:
            print("  [dry-run] criaria route table pública")
            return "rtb-dry-run"
        route_table_id = ec2.create_route_table(
            VpcId=vpc_id,
            TagSpecifications=_tag_specs("route-table", "folheia-replication-rt"),
        )["RouteTable"]["RouteTableId"]
        routes, associations = [], []
        print(f"  route table criada: {route_table_id}")

    if not any(route.get("DestinationCidrBlock") == "0.0.0.0/0" for route in routes):
        if not dry_run:
            ec2.create_route(
                RouteTableId=route_table_id,
                DestinationCidrBlock="0.0.0.0/0",
                GatewayId=igw_id,
            )
            print("  rota 0.0.0.0/0 -> IGW criada")
        else:
            print("  [dry-run] criaria rota 0.0.0.0/0 -> IGW")

    associated = {item.get("SubnetId") for item in associations}
    for subnet_id in subnet_ids:
        if subnet_id in associated:
            continue
        if dry_run:
            print(f"  [dry-run] associaria {subnet_id} à route table")
            continue
        ec2.associate_route_table(RouteTableId=route_table_id, SubnetId=subnet_id)
        print(f"  rota associada à sub-rede {subnet_id}")
    return route_table_id


# --------------------------------------------------------------------------- #
# Security Group
# --------------------------------------------------------------------------- #
def ensure_security_group(ec2, vpc_id: str, dry_run: bool) -> str:
    existing = ec2.describe_security_groups(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc_id]},
            {"Name": "group-name", "Values": [SG_NAME]},
        ]
    )["SecurityGroups"]
    if existing:
        group_id = existing[0]["GroupId"]
        print(f"  security group existente: {group_id}")
        return group_id

    if dry_run:
        print(f"  [dry-run] criaria security group {SG_NAME}")
        return "sg-dry-run"

    group_id = ec2.create_security_group(
        GroupName=SG_NAME,
        Description="Acesso ao PostgreSQL do experimento de replicacao RDS",
        VpcId=vpc_id,
        TagSpecifications=_tag_specs("security-group", SG_NAME),
    )["GroupId"]
    print(f"  security group criado: {group_id}")
    return group_id


def _has_rule(group: dict, cidr: str, port: int) -> bool:
    for permission in group.get("IpPermissions", []):
        if permission.get("IpProtocol") not in ("tcp", "6"):
            continue
        if permission.get("FromPort") != port or permission.get("ToPort") != port:
            continue
        for ip_range in permission.get("IpRanges", []):
            if ip_range.get("CidrIp") == cidr:
                return True
    return False


def ensure_ingress(
    ec2,
    group_ids: list[str] | None,
    cidr: str,
    port: int,
    dry_run: bool,
) -> list[str]:
    """Garante a regra de entrada do PostgreSQL; retorna os SGs alterados."""
    added: list[str] = []
    for group_id in group_ids or []:
        if not group_id or group_id.endswith("dry-run"):
            continue
        group = ec2.describe_security_groups(GroupIds=[group_id])["SecurityGroups"][0]
        if _has_rule(group, cidr, port):
            print(f"  SG {group_id} já libera {port}/tcp para {cidr}")
            continue
        if dry_run:
            print(f"  [dry-run] liberaria {port}/tcp para {cidr} no SG {group_id}")
            continue
        ec2.authorize_security_group_ingress(
            GroupId=group_id,
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": port,
                    "ToPort": port,
                    "IpRanges": [{"CidrIp": cidr, "Description": SG_RULE_DESCRIPTION}],
                }
            ],
        )
        print(f"  regra {port}/tcp -> {cidr} adicionada ao SG {group_id}")
        added.append(group_id)
    return added


def remove_ingress(
    ec2,
    group_ids: list[str] | None,
    cidr: str,
    port: int,
    dry_run: bool,
) -> None:
    """Remove apenas as regras criadas por este script (identificadas pela descrição)."""
    for group_id in group_ids or []:
        if not group_id or group_id.endswith("dry-run"):
            continue
        try:
            group = ec2.describe_security_groups(GroupIds=[group_id])["SecurityGroups"][0]
        except Exception as exc:
            print(f"  [aviso] SG {group_id} indisponível ({type(exc).__name__})")
            continue

        permissions = []
        for permission in group.get("IpPermissions", []):
            if permission.get("IpProtocol") not in ("tcp", "6"):
                continue
            if permission.get("FromPort") != port or permission.get("ToPort") != port:
                continue
            ranges = [
                ip_range
                for ip_range in permission.get("IpRanges", [])
                if ip_range.get("CidrIp") == cidr
                and ip_range.get("Description", "").startswith(SG_RULE_DESCRIPTION)
            ]
            if ranges:
                permissions.append(
                    {"IpProtocol": "tcp", "FromPort": port, "ToPort": port, "IpRanges": ranges}
                )

        if not permissions:
            print(f"  nenhuma regra gerenciada pelo script no SG {group_id}")
            continue
        if dry_run:
            print(f"  [dry-run] removeria {len(permissions)} regra(s) do SG {group_id}")
            continue
        ec2.revoke_security_group_ingress(GroupId=group_id, IpPermissions=permissions)
        print(f"  regra(s) de {port}/tcp removida(s) do SG {group_id}")


# --------------------------------------------------------------------------- #
# Destruição da rede criada pelo script
# --------------------------------------------------------------------------- #
def destroy_network(ec2, rds, network: dict, dry_run: bool) -> None:
    if not network or not network.get("created_by_script"):
        print("  rede não foi criada por este script; nada a destruir")
        return

    subnet_group = network.get("db_subnet_group")
    if subnet_group:
        if dry_run:
            print(f"  [dry-run] removeria DB subnet group {subnet_group}")
        else:
            _ignore_missing(rds.delete_db_subnet_group, DBSubnetGroupName=subnet_group)
            print(f"  DB subnet group removido: {subnet_group}")

    group_id = network.get("security_group_id")
    if group_id:
        if dry_run:
            print(f"  [dry-run] removeria security group {group_id}")
        else:
            _retry(ec2.delete_security_group, f"security group {group_id}", GroupId=group_id)
            print(f"  security group removido: {group_id}")

    for subnet_id in network.get("subnet_ids", []):
        if dry_run:
            print(f"  [dry-run] removeria sub-rede {subnet_id}")
        else:
            _retry(ec2.delete_subnet, f"sub-rede {subnet_id}", SubnetId=subnet_id)
            print(f"  sub-rede removida: {subnet_id}")

    route_table_id = network.get("route_table_id")
    if route_table_id:
        if dry_run:
            print(f"  [dry-run] removeria route table {route_table_id}")
        else:
            try:
                table = ec2.describe_route_tables(RouteTableIds=[route_table_id])["RouteTables"][0]
                for association in table.get("Associations", []):
                    if association.get("Main"):
                        continue
                    _ignore_missing(
                        ec2.disassociate_route_table,
                        AssociationId=association["RouteTableAssociationId"],
                    )
            except Exception:
                pass
            _ignore_missing(ec2.delete_route_table, RouteTableId=route_table_id)
            print(f"  route table removida: {route_table_id}")

    igw_id = network.get("internet_gateway_id")
    vpc_id = network.get("vpc_id")
    if igw_id:
        if dry_run:
            print(f"  [dry-run] removeria internet gateway {igw_id}")
        else:
            if vpc_id:
                _ignore_missing(
                    ec2.detach_internet_gateway, InternetGatewayId=igw_id, VpcId=vpc_id
                )
            _ignore_missing(ec2.delete_internet_gateway, InternetGatewayId=igw_id)
            print(f"  internet gateway removido: {igw_id}")

    if vpc_id:
        if dry_run:
            print(f"  [dry-run] removeria VPC {vpc_id}")
        else:
            _retry(ec2.delete_vpc, f"VPC {vpc_id}", VpcId=vpc_id)
            print(f"  VPC removida: {vpc_id}")
