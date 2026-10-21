"""Configuração central do experimento de replicação RDS (AWS).

Regras do PRD aplicadas aqui:

* nenhuma credencial é escrita no código: a senha vem de ``DB_PASSWORD``,
  do Secrets Manager ou de prompt interativo;
* todo recurso criado carrega as tags ``Project=folheia-replication`` e
  ``ManagedBy=folheia-infra``, o que permite adotar e limpar recursos de
  forma idempotente;
* os caminhos são derivados do próprio arquivo, então os scripts funcionam
  a partir de qualquer diretório de trabalho.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

from dotenv import load_dotenv

INFRA_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = INFRA_DIR.parent
ENV_FILE = INFRA_DIR / ".env"
GENERATED_ENV = INFRA_DIR / "generated.env"
STATE_FILE = INFRA_DIR / "state.json"
CERTS_DIR = INFRA_DIR / "certs"
CA_BUNDLE = CERTS_DIR / "global-bundle.pem"

PROJECT = "folheia-replication"
MANAGED_BY = "folheia-infra"
SG_RULE_DESCRIPTION = "folheia-replication-test"
CA_BUNDLE_URL = "https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem"
DEFAULT_AWS_REGION = "us-east-1"


def load_env() -> None:
    """Carrega ``infra/.env`` e, como complemento, ``infra/generated.env``.

    O ``override=False`` garante que valores definidos explicitamente no
    ambiente ou no ``.env`` tenham prioridade sobre o arquivo gerado.
    """
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE, override=False)
    if GENERATED_ENV.exists():
        load_dotenv(GENERATED_ENV, override=False)

    # Um AWS_PROFILE vazio no .env confunde o boto3: ele tentaria o profile ""
    # e abortaria com ProfileNotFound. Removemos a variável nesse caso.
    for name in ("AWS_PROFILE", "AWS_DEFAULT_PROFILE"):
        if os.environ.get(name) == "":
            os.environ.pop(name, None)


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(f"valor inválido para {name}: {raw!r} (esperado inteiro)") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "y", "on"}


def tags(name: str | None = None) -> list[dict[str, str]]:
    """Tags padrão aplicadas a todo recurso criado pelo script."""
    items = [
        {"Key": "Project", "Value": PROJECT},
        {"Key": "ManagedBy", "Value": MANAGED_BY},
    ]
    if name:
        items.append({"Key": "Name", "Value": name})
    return items


@dataclass(frozen=True)
class Settings:
    """Configuração efetiva de uma execução."""

    region: str = DEFAULT_AWS_REGION
    profile: str | None = None

    # Banco alvo
    db_name: str = "money"
    db_user: str = "postgres"
    db_password: str | None = None
    db_port: int = 5432
    maintenance_db: str = "postgres"

    # Secrets Manager
    secret_arn: str | None = None
    publish_secret_name: str = "folheia/db/money"

    # Instâncias
    primary_instance_id: str = "folheia-money-primary"
    primary_endpoint: str | None = None
    replica_instance_id: str = "folheia-money-replica"
    instance_class: str = "db.t4g.micro"
    engine: str = "postgres"
    engine_version: str | None = None
    allocated_storage: int = 20
    storage_type: str = "gp3"
    backup_retention: int = 1
    publicly_accessible: bool = True
    replica_az: str | None = None

    # Rede
    allowed_cidr: str = "0.0.0.0/0"
    vpc_cidr: str = "10.0.0.0/16"
    db_subnet_group_name: str = "folheia-replication-subnet-group"

    # TLS / conexão
    ssl_mode: str = "verify-full"
    ca_bundle: Path = CA_BUNDLE
    connection_timeout: int = 15

    # Teste de replicação
    rows: int = 1000

    @classmethod
    def from_env(cls) -> "Settings":
        load_env()
        ssl_root = Path(_env("SSL_ROOT_CERT", str(CA_BUNDLE)) or str(CA_BUNDLE))
        if not ssl_root.is_absolute():
            ssl_root = (REPO_ROOT / ssl_root).resolve()

        engine_version = _env("ENGINE_VERSION")

        return cls(
            region=_env("AWS_REGION", _env("AWS_DEFAULT_REGION", DEFAULT_AWS_REGION)) or DEFAULT_AWS_REGION,
            profile=_env("AWS_PROFILE"),
            db_name=_env("DB_NAME", "money") or "money",
            db_user=_env("DB_USER", "postgres") or "postgres",
            db_password=_env("DB_PASSWORD"),
            db_port=_env_int("DB_PORT", 5432),
            maintenance_db=_env("MAINTENANCE_DB", "postgres") or "postgres",
            secret_arn=_env("DB_SECRET_ARN"),
            publish_secret_name=_env("PUBLISH_SECRET_NAME", "folheia/db/money") or "folheia/db/money",
            primary_instance_id=_env("PRIMARY_INSTANCE_ID", "folheia-money-primary") or "folheia-money-primary",
            primary_endpoint=_env("PRIMARY_ENDPOINT"),
            replica_instance_id=_env("REPLICA_INSTANCE_ID", "folheia-money-replica") or "folheia-money-replica",
            instance_class=_env("INSTANCE_CLASS", "db.t4g.micro") or "db.t4g.micro",
            engine=_env("ENGINE", "postgres") or "postgres",
            engine_version=engine_version,
            allocated_storage=_env_int("ALLOCATED_STORAGE", 20),
            storage_type=_env("STORAGE_TYPE", "gp3") or "gp3",
            backup_retention=_env_int("BACKUP_RETENTION", 1),
            publicly_accessible=_env_bool("PUBLICLY_ACCESSIBLE", True),
            replica_az=_env("REPLICA_AZ"),
            allowed_cidr=_env("ALLOWED_CIDR", "0.0.0.0/0") or "0.0.0.0/0",
            vpc_cidr=_env("VPC_CIDR", "10.0.0.0/16") or "10.0.0.0/16",
            db_subnet_group_name=_env("DB_SUBNET_GROUP", "folheia-replication-subnet-group")
            or "folheia-replication-subnet-group",
            ssl_mode=_env("SSL_MODE", "verify-full") or "verify-full",
            ca_bundle=ssl_root,
            connection_timeout=_env_int("CONNECT_TIMEOUT", 15),
            rows=_env_int("ROWS", 1000),
        )

    def with_overrides(self, **overrides) -> "Settings":
        """Retorna uma cópia com apenas os valores não nulos sobrescritos."""
        clean = {key: value for key, value in overrides.items() if value is not None}
        return replace(self, **clean)


def _import_boto3():
    try:
        import boto3
    except ModuleNotFoundError as exc:  # pragma: no cover - depende do ambiente
        raise SystemExit(
            "boto3 não está instalado.\n"
            "Rode: pip install -r infra/requirements.txt"
        ) from exc
    return boto3


def boto3_session(settings: Settings):
    """Sessão Boto3 usando o profile/região configurados (sem credenciais no código)."""
    boto3 = _import_boto3()
    kwargs = {"region_name": settings.region}
    if settings.profile:
        kwargs["profile_name"] = settings.profile
    return boto3.Session(**kwargs)


def client(settings: Settings, service: str):
    return boto3_session(settings).client(service)


def identity(settings: Settings) -> dict:
    """Retorna o resultado de ``sts:GetCallerIdentity`` (conta/ARN)."""
    return client(settings, "sts").get_caller_identity()


def account_from_arn(arn: str | None) -> str | None:
    if not arn:
        return None
    parts = arn.split(":")
    return parts[4] if len(parts) > 5 else None


def mask(value: str | None, visible: int = 2) -> str:
    """Mascara a maior parte de um valor sensível para uso em logs."""
    if not value:
        return "<vazio>"
    if len(value) <= visible:
        return "*" * len(value)
    return value[:visible] + "*" * max(1, len(value) - visible)
