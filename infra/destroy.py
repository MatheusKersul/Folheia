#!/usr/bin/env python3
"""Remove os recursos criados por ``infra/provision.py``.

Por segurança, a instância primária adotada (ex.: ``acervo-1``) NUNCA é
removida sem ``--force-delete-primary``. O script também só apaga o que
estiver registrado em ``infra/state.json``.

Exemplos:
    python infra/destroy.py --dry-run
    python infra/destroy.py
    python infra/destroy.py --drop-database --delete-secret
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Destrói a read replica e os recursos de rede criados pelo provision.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true", help="mostra o que seria removido")
    parser.add_argument(
        "--drop-database",
        action="store_true",
        help="remove o banco alvo da primária (DROP DATABASE)",
    )
    parser.add_argument(
        "--delete-secret",
        action="store_true",
        help="remove o segredo criado pelo provision (PUBLISH_SECRET_NAME)",
    )
    parser.add_argument(
        "--keep-secret",
        action="store_true",
        help="mantém o segredo mesmo com --delete-secret",
    )
    parser.add_argument(
        "--force-delete-primary",
        action="store_true",
        help="PERIGO: remove também a instância primária (inclusive adotada)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = cfg.Settings.from_env()
    state = state_mod.load()

    if not state:
        raise SystemExit(
            "infra/state.json ausente: não há registro do que foi criado.\n"
            "Se você provisionou manualmente, remova os recursos pelo console."
        )

    print("=" * 78)
    print("Folheia · destruição dos recursos de replicação")
    print("=" * 78)
    print(f"  região : {settings.region}")
    print(f"  execução: {'DRY-RUN (sem alterações)' if args.dry_run else 'REMOVER'}")
    print()

    try:
        identity = cfg.identity(settings)
        print(f"  conta AWS : {identity.get('Account')}")
    except Exception as exc:
        raise SystemExit(
            "não foi possível autenticar na AWS.\n"
            f"erro: {type(exc).__name__}: {exc}"
        ) from exc

    if args.force_delete_primary:
        print("  [PERIGO] --force-delete-primary ativo: a primária também será removida")

    ec2 = cfg.client(settings, "ec2")
    rds = cfg.client(settings, "rds")

    # 1) réplica
    print("[1/5] read replica")
    replica = state.get("replica") or {}
    if replica.get("identifier"):
        rds_mod.delete_instance(rds, replica["identifier"], args.dry_run)
    else:
        print("  nenhuma réplica registrada")

    # 2) regra de security group
    print("[2/5] regra de acesso ao PostgreSQL")
    network = state.get("network") or {}
    group_ids = network.get("security_group_ids") or []
    if not group_ids:
        primary = state.get("primary") or {}
        group_ids = primary.get("security_group_ids") or []
    net.remove_ingress(ec2, group_ids, settings.allowed_cidr, settings.db_port, args.dry_run)

    # 3) banco alvo
    print("[3/5] banco de dados")
    if args.drop_database:
        primary = state.get("primary") or {}
        endpoint = primary.get("endpoint")
        if not endpoint:
            print("  [aviso] endpoint da primária ausente; DROP DATABASE ignorado")
        elif args.dry_run:
            print(f"  [dry-run] removeria o banco '{settings.db_name}' em {endpoint}")
        else:
            user, password = secrets_mod.resolve_credentials(settings)
            db_mod.drop_database(settings, endpoint, user, password)
    else:
        print(f"  banco '{settings.db_name}' preservado (use --drop-database para remover)")

    # 4) segredo
    print("[4/5] segredo")
    secret = state.get("secret") or {}
    if secret.get("created_by_script") and args.delete_secret and not args.keep_secret:
        secrets_mod.delete(settings, secret.get("arn") or secret.get("name"), args.dry_run)
    else:
        print("  segredo preservado")

    # 5) rede criada pelo script
    print("[5/5] rede")
    net.destroy_network(ec2, rds, network, args.dry_run)

    primary = state.get("primary") or {}
    if args.force_delete_primary and primary.get("identifier"):
        print("[extra] removendo a primária por --force-delete-primary")
        rds_mod.delete_instance(rds, primary["identifier"], args.dry_run)
    elif primary.get("identifier"):
        print(
            f"  primária preservada: {primary['identifier']} "
            "(use --force-delete-primary para removê-la)"
        )

    if not args.dry_run:
        state["destroyed_at"] = state_mod.utcnow()
        state_mod.save(state)

    print()
    print("=" * 78)
    print("Limpeza concluída" if not args.dry_run else "Dry-run concluído (nada foi alterado)")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\ninterrompido pelo usuário")
        raise SystemExit(130)
