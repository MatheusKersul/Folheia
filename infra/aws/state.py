"""Persistência local do estado do provisionamento (``infra/state.json``).

O arquivo permite que ``destroy.py`` remova somente o que o script criou e
nunca contém senhas — apenas identificadores, endpoints e ARNs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import STATE_FILE


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load(path: Path = STATE_FILE) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"  [aviso] {path} inválido; começando um estado vazio")
        return {}


def save(state: dict, path: Path = STATE_FILE, dry_run: bool = False) -> None:
    path = Path(path)
    if dry_run:
        print(f"  [dry-run] não gravando {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  estado gravado em {path}")


def record(state: dict, section: str, **values) -> dict:
    """Cria/atualiza uma seção do estado com timestamp de atualização."""
    target = state.setdefault(section, {})
    target.update({key: value for key, value in values.items() if value is not None})
    target["updated_at"] = utcnow()
    return target
