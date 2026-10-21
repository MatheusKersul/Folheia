#!/usr/bin/env python3
"""Teste de replicação Master -> Read Replica (Amazon RDS / PostgreSQL).

O roteamento é explícito e proposital:

* conexão ``master``  -> usada APENAS para escrita (INSERT/DELETE de teste);
* conexão ``replica`` -> usada APENAS para leitura (SELECT).

Antes de qualquer operação o script confirma os papéis com
``pg_is_in_recovery()`` (False no Master, True na Réplica) e, ao final,
tenta um INSERT na Réplica para provar que ela é somente leitura.

Exemplo:
    python scripts/replication_test.py --rows 1000 --cleanup
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    import bcrypt
except ModuleNotFoundError:  # pragma: no cover - depende do ambiente
    raise SystemExit(
        "bcrypt não está instalado.\nRode: pip install -r infra/requirements.txt"
    )

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ModuleNotFoundError:  # pragma: no cover - depende do ambiente
    raise SystemExit(
        "psycopg2 não está instalado.\nRode: pip install -r infra/requirements.txt"
    )

from infra.aws import config as cfg
from infra.aws import db as db_mod
from infra.aws import secrets as secrets_mod
from infra.aws import state as state_mod

EMAIL_TAG = "replica-test"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prova a replicação Master -> Read Replica medindo o lag (eventual consistency)."
    )
    parser.add_argument("--rows", type=int, help="quantidade de registros inseridos no Master")
    parser.add_argument(
        "--interval",
        type=float,
        default=0.1,
        help="intervalo entre polls na réplica em segundos (padrão: 0.1)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="tempo máximo de espera pela convergência em segundos (padrão: 60)",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="remove os registros de teste do Master ao final",
    )
    parser.add_argument("--master-host", help="sobrescreve o endpoint do Master")
    parser.add_argument("--replica-host", help="sobrescreve o endpoint da Réplica")
    parser.add_argument(
        "--no-readonly-check",
        action="store_true",
        help="não tenta escrever na réplica (a prova de read-only é feita por padrão)",
    )
    return parser.parse_args(argv)


def resolve_hosts(settings: cfg.Settings, args: argparse.Namespace) -> tuple[str, str]:
    state = state_mod.load()
    primary = state.get("primary") or {}
    replica = state.get("replica") or {}

    master = (
        args.master_host
        or os.getenv("MASTER_HOST")
        or primary.get("endpoint")
        or settings.primary_endpoint
    )
    replica_host = args.replica_host or os.getenv("REPLICA_HOST") or replica.get("endpoint")

    if not master:
        raise SystemExit(
            "endpoint do Master desconhecido.\n"
            "Rode `python infra/provision.py` (gera state.json/generated.env) "
            "ou defina MASTER_HOST."
        )
    if not replica_host:
        raise SystemExit(
            "endpoint da Réplica desconhecido.\n"
            "Rode `python infra/provision.py` ou defina REPLICA_HOST."
        )
    return master, replica_host


def in_recovery(connection) -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_is_in_recovery()")
        return bool(cursor.fetchone()[0])


def tls_active(connection) -> bool:
    try:
        return bool(connection.info.ssl_in_use)
    except Exception:
        return False


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = cfg.Settings.from_env()
    rows = args.rows or settings.rows
    if rows <= 0:
        raise SystemExit("--rows deve ser maior que zero")

    master_host, replica_host = resolve_hosts(settings, args)
    user, password = secrets_mod.resolve_credentials(settings)

    print("=" * 78)
    print("Folheia · teste de replicação RDS (Master -> Read Replica)")
    print("=" * 78)
    print(f"[MASTER  {master_host}:{settings.db_port} -> WRITE]")
    print(f"[REPLICA {replica_host}:{settings.db_port} -> READ]")
    print(f"  banco   : {settings.db_name} | tabela: users")
    print(f"  TLS     : {settings.ssl_mode}")
    print()

    master = db_mod.connect(
        settings, master_host, user=user, password=password, application_name="folheia/replication-master"
    )
    try:
        replica = db_mod.connect(
            settings,
            replica_host,
            user=user,
            password=password,
            application_name="folheia/replication-replica",
        )
    except Exception:
        master.close()
        raise

    try:
        # -------------------------------------------------------------- #
        # 0) validação de papéis
        # -------------------------------------------------------------- #
        print("[0/5] validando papéis das instâncias")
        master_recovery = in_recovery(master)
        replica_recovery = in_recovery(replica)
        print(f"  master  pg_is_in_recovery() = {master_recovery} (esperado: False)")
        print(f"  replica pg_is_in_recovery() = {replica_recovery} (esperado: True)")
        print(f"  TLS ativo: master={tls_active(master)} replica={tls_active(replica)}")
        if master_recovery:
            raise SystemExit("o host do Master está em recovery: confira os endpoints")
        if not replica_recovery:
            raise SystemExit("o host da Réplica NÃO está em recovery: confira os endpoints")
        print()

        try:
            db_mod.ensure_users_table(settings, master_host, user, password)
        except psycopg2.OperationalError as exc:
            raise SystemExit(
                "não foi possível preparar a tabela 'users' no Master.\n"
                "Rode `python infra/provision.py` para criar o banco/tabela e a réplica.\n"
                f"erro: {exc}"
            ) from exc

        # -------------------------------------------------------------- #
        # 1) escrita no Master
        # -------------------------------------------------------------- #
        run_id = uuid.uuid4().hex[:8]
        prefix = f"{EMAIL_TAG}-{run_id}-"
        pattern = f"{prefix}%"
        password_hash = bcrypt.hashpw(b"replica-test", bcrypt.gensalt(rounds=4)).decode()

        batch = [
            (
                f"Replica Test {index:05d}",
                f"{prefix}{index:05d}@example.com",
                password_hash,
                "usuario",
            )
            for index in range(1, rows + 1)
        ]

        print(f"[1/5] INSERT de {rows} registros no MASTER (prefixo {prefix})")
        started = time.perf_counter()
        with master.cursor() as cursor:
            execute_values(
                cursor,
                "INSERT INTO users (nome, email, senha, permissoes) VALUES %s",
                batch,
                page_size=500,
            )
        master.commit()
        write_ms = (time.perf_counter() - started) * 1000.0
        committed_at = time.perf_counter()
        print(f"  commit concluído em {write_ms:.1f} ms")
        print()

        # -------------------------------------------------------------- #
        # 2) leitura na Réplica com medição de lag
        # -------------------------------------------------------------- #
        print(
            f"[2/5] polling na RÉPLICA a cada {args.interval * 1000:.0f} ms "
            f"(timeout {args.timeout:.0f}s)"
        )
        trace: list[tuple[float, int]] = []
        deadline = committed_at + args.timeout
        visible = 0
        lag_ms: float | None = None

        while True:
            with replica.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM users WHERE email LIKE %s", (pattern,))
                visible = int(cursor.fetchone()[0])

            elapsed_ms = (time.perf_counter() - committed_at) * 1000.0
            trace.append((elapsed_ms, visible))
            print(f"  +{elapsed_ms:8.1f} ms -> {visible:5d}/{rows} registros visíveis na réplica")

            if visible >= rows:
                lag_ms = elapsed_ms
                break
            if time.perf_counter() > deadline:
                break
            time.sleep(args.interval)

        if lag_ms is None:
            print()
            print(f"  [FALHA] a réplica não convergiu em {args.timeout:.0f}s "
                  f"(último count={visible})")
            return 2
        print()

        # -------------------------------------------------------------- #
        # 3) comprovação de leitura
        # -------------------------------------------------------------- #
        print("[3/5] leitura de comprovação na RÉPLICA")
        with replica.cursor() as cursor:
            cursor.execute(
                "SELECT id, nome, email, permissoes FROM users "
                "WHERE email LIKE %s ORDER BY id LIMIT 5",
                (pattern,),
            )
            for row in cursor.fetchall():
                print("  {:<5} {:<22} {:<45} {}".format(*row))
        print()

        # -------------------------------------------------------------- #
        # 4) prova de que a réplica é somente leitura
        # -------------------------------------------------------------- #
        readonly_ok: bool | None = None
        if args.no_readonly_check:
            print("[4/5] checagem de read-only ignorada (--no-readonly-check)")
        else:
            print("[4/5] tentativa de escrita na RÉPLICA (deve ser rejeitada)")
            try:
                with replica.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO users (nome, email, senha, permissoes) "
                        "VALUES (%s, %s, %s, %s)",
                        ("blocked", f"{prefix}blocked@example.com", "x", "usuario"),
                    )
                replica.rollback()
                readonly_ok = False
                print("  [aviso] a réplica ACEITOU o INSERT: confirme se o host é uma read replica")
            except psycopg2.Error as exc:
                replica.rollback()
                readonly_ok = True
                first_line = str(exc).strip().splitlines()[0] if str(exc).strip() else ""
                print(f"  escrita rejeitada: {type(exc).__name__}: {first_line}")
        print()

        # -------------------------------------------------------------- #
        # 5) limpeza opcional
        # -------------------------------------------------------------- #
        if args.cleanup:
            print("[5/5] removendo registros de teste do MASTER")
            with master.cursor() as cursor:
                cursor.execute("DELETE FROM users WHERE email LIKE %s", (pattern,))
                deleted = cursor.rowcount
            master.commit()
            print(f"  {deleted} registro(s) removido(s) do master (a réplica acompanha a replicação)")
        else:
            print("[5/5] registros de teste mantidos")
            print(f"  para remover depois: DELETE FROM users WHERE email LIKE '{pattern}';")
        print()

        # -------------------------------------------------------------- #
        # resumo
        # -------------------------------------------------------------- #
        first_visible = next((elapsed for elapsed, count in trace if count > 0), None)
        lags = [elapsed for elapsed, _ in trace]

        print("=" * 78)
        print("Resultado")
        print("=" * 78)
        print(f"  registros inseridos no Master : {rows}")
        print(f"  tempo do INSERT + commit      : {write_ms:.1f} ms")
        if first_visible is not None:
            print(f"  primeiro registro na Réplica  : {first_visible:.1f} ms")
        print(f"  lag total de replicação       : {lag_ms:.1f} ms")
        print(f"  polls na réplica              : {len(trace)}")
        if len(lags) > 1:
            print(f"  intervalo p50 entre polls     : {statistics.median(lags):.1f} ms")
        if readonly_ok is not None:
            print(f"  réplica somente leitura       : {'SIM' if readonly_ok else 'NÃO'}")
        print("=" * 78)
        return 0
    finally:
        master.close()
        replica.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\ninterrompido pelo usuário")
        raise SystemExit(130)
