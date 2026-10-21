"""Acesso ao AWS Secrets Manager e resolução de credenciais.

Precedência (documentada no README):
1. ``DB_PASSWORD`` / ``DB_USER`` do ambiente ou de ``infra/.env``;
2. segredo existente apontado por ``DB_SECRET_ARN``;
3. prompt interativo (``getpass``), nunca argumento de linha de comando.
"""

from __future__ import annotations

import getpass
import json

from .config import Settings, client


def _manager(settings: Settings):
    return client(settings, "secretsmanager")


def describe(settings: Settings, secret_id: str) -> dict | None:
    manager = _manager(settings)
    try:
        return manager.describe_secret(SecretId=secret_id)
    except manager.exceptions.ResourceNotFoundException:
        return None


def get_json(settings: Settings, secret_id: str) -> dict:
    """Lê o segredo e devolve um dicionário (aceita JSON ou string pura)."""
    manager = _manager(settings)
    payload = manager.get_secret_value(SecretId=secret_id).get("SecretString", "")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {"password": payload}
    if isinstance(data, str):
        return {"password": data}
    return data if isinstance(data, dict) else {"password": str(data)}


def inspect(settings: Settings, secret_id: str) -> tuple[dict, dict]:
    """Retorna metadados do segredo e os campos não sensíveis (sem a senha)."""
    metadata = describe(settings, secret_id)
    if not metadata:
        raise SystemExit(f"segredo não encontrado: {secret_id}")

    data = get_json(settings, secret_id)
    allowed = ("username", "host", "port", "dbname", "engine")
    safe = {key: data[key] for key in allowed if key in data}
    return metadata, safe


def resolve_credentials(
    settings: Settings, prompt: bool = True, allow_secret: bool = True
) -> tuple[str, str]:
    """Resolve usuário e senha sem nunca imprimir a senha.

    ``allow_secret=False`` é usado ao criar uma instância nova: o segredo
    existente pertence a outra instância e não deve definir a senha do Master.
    """
    user = settings.db_user
    password = settings.db_password
    source = "env" if password else None

    if allow_secret and settings.secret_arn:
        try:
            data = get_json(settings, settings.secret_arn)
        except Exception as exc:
            print(f"  [aviso] não foi possível ler o segredo ({type(exc).__name__}: {exc})")
        else:
            if not password and data.get("password"):
                password = data["password"]
                source = "secretsmanager"
            if data.get("username") and not settings.db_user:
                user = data["username"]

    if not password:
        if not prompt:
            raise SystemExit(
                "senha ausente: defina DB_PASSWORD em infra/.env ou configure DB_SECRET_ARN"
            )
        password = getpass.getpass(f"Senha do usuário {user} (não será exibida): ")
        source = "prompt"

    if not password:
        raise SystemExit("senha vazia; abortando")

    print(f"  credencial resolvida: usuário={user} senha=*** (origem: {source})")
    return user, password


def upsert(settings: Settings, name: str, username: str, password: str, dry_run: bool) -> str:
    """Cria ou atualiza o segredo ``name`` com as credenciais informadas."""
    manager = _manager(settings)
    payload = json.dumps({"username": username, "password": password})

    existing = describe(settings, name)
    if existing:
        if dry_run:
            print(f"  [dry-run] atualizaria o segredo {name}")
            return existing["ARN"]
        manager.put_secret_value(SecretId=existing["ARN"], SecretString=payload)
        print(f"  segredo atualizado: {name}")
        return existing["ARN"]

    if dry_run:
        print(f"  [dry-run] criaria o segredo {name}")
        return "arn:aws:secretsmanager:dry-run"

    arn = manager.create_secret(
        Name=name,
        Description="Credencial do banco money - experimento de replicacao RDS (Folheia)",
        SecretString=payload,
    )["ARN"]
    print(f"  segredo criado: {name}")
    return arn


def delete(settings: Settings, secret_id: str, dry_run: bool) -> None:
    manager = _manager(settings)
    existing = describe(settings, secret_id)
    if not existing:
        print(f"  segredo {secret_id} já não existe")
        return
    if dry_run:
        print(f"  [dry-run] removeria o segredo {secret_id}")
        return
    manager.delete_secret(SecretId=existing["ARN"], ForceDeleteWithoutRecovery=True)
    print(f"  segredo removido: {secret_id}")
