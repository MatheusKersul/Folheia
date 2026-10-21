"""Conexões PostgreSQL e preparação do banco/tabela do experimento."""

from __future__ import annotations

import time

from . import certs
from .config import Settings

USERS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    permissoes VARCHAR(20) NOT NULL DEFAULT 'usuario',
    CONSTRAINT users_permissoes_check
        CHECK (permissoes IN ('usuario', 'funcionario', 'admin'))
)
""".strip()

# O mesmo índice parcial da aplicação: permite apenas um administrador.
USERS_ADMIN_INDEX_DDL = """
CREATE UNIQUE INDEX IF NOT EXISTS unique_admin
    ON users (permissoes)
    WHERE permissoes = 'admin'
""".strip()


def _psycopg2():
    try:
        import psycopg2
        import psycopg2.extras  # noqa: F401  (registra helpers usados nos scripts)
    except ModuleNotFoundError as exc:  # pragma: no cover - depende do ambiente
        raise SystemExit(
            "psycopg2 não está instalado.\n"
            "Rode: pip install -r infra/requirements.txt"
        ) from exc
    return psycopg2


def connect(
    settings: Settings,
    host: str,
    dbname: str | None = None,
    user: str | None = None,
    password: str | None = None,
    application_name: str = "folheia-replication",
):
    """Abre uma conexão TLS com o host indicado (Master ou Réplica)."""
    psycopg2 = _psycopg2()
    params = {
        "host": host,
        "port": settings.db_port,
        "dbname": dbname or settings.db_name,
        "user": user or settings.db_user,
        "password": password,
        "connect_timeout": settings.connection_timeout,
        "application_name": application_name,
    }
    if settings.ssl_mode:
        params["sslmode"] = settings.ssl_mode
        if settings.ssl_mode in ("verify-ca", "verify-full"):
            params["sslrootcert"] = str(certs.ensure_ca_bundle(settings.ca_bundle))

    return psycopg2.connect(**params)


def wait_connectable(
    settings: Settings,
    host: str,
    password: str,
    user: str | None = None,
    dbname: str | None = None,
    timeout_seconds: int = 600,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            connection = connect(settings, host, dbname=dbname, user=user, password=password)
            connection.close()
            return
        except Exception as exc:  # rede/DNS ainda propagando após criar a instância
            last_error = exc
            print(f"  aguardando {host} aceitar conexões ({type(exc).__name__})...")
            time.sleep(10)
    raise SystemExit(
        f"não foi possível conectar em {host}: {last_error}\n"
        "Verifique: (1) regra 5432 no Security Group para o seu IP, "
        "(2) PubliclyAccessible=true na instância e "
        "(3) sub-rede com rota 0.0.0.0/0 para um Internet Gateway."
    )


def ensure_database(settings: Settings, host: str, user: str, password: str) -> bool:
    """Cria o banco alvo se não existir (idempotente, fora de transação)."""
    psycopg2 = _psycopg2()
    from psycopg2 import sql as pgsql

    connection = connect(
        settings,
        host,
        dbname=settings.maintenance_db,
        user=user,
        password=password,
        application_name="folheia-bootstrap",
    )
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (settings.db_name,))
            if cursor.fetchone():
                print(f"  banco '{settings.db_name}' já existe")
                return False
            cursor.execute(
                pgsql.SQL("CREATE DATABASE {}").format(pgsql.Identifier(settings.db_name))
            )
            print(f"  banco '{settings.db_name}' criado")
            return True
    finally:
        connection.close()


def ensure_users_table(settings: Settings, host: str, user: str, password: str) -> None:
    connection = connect(
        settings,
        host,
        user=user,
        password=password,
        application_name="folheia-bootstrap",
    )
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute(USERS_TABLE_DDL)
            cursor.execute(USERS_ADMIN_INDEX_DDL)
        print(f"  tabela 'users' pronta em '{settings.db_name}'")
    finally:
        connection.close()


def drop_database(settings: Settings, host: str, user: str, password: str) -> None:
    """Remove o banco alvo (usado apenas pelo destroy com --drop-database)."""
    psycopg2 = _psycopg2()
    from psycopg2 import sql as pgsql

    connection = connect(
        settings,
        host,
        dbname=settings.maintenance_db,
        user=user,
        password=password,
        application_name="folheia-destroy",
    )
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (settings.db_name,))
            if not cursor.fetchone():
                print(f"  banco '{settings.db_name}' já não existe")
                return
            cursor.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (settings.db_name,),
            )
            cursor.execute(pgsql.SQL("DROP DATABASE {}").format(pgsql.Identifier(settings.db_name)))
            print(f"  banco '{settings.db_name}' removido")
    finally:
        connection.close()
