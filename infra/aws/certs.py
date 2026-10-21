"""Download do CA bundle da AWS, necessário para ``sslmode=verify-full``."""

from __future__ import annotations

import shutil
import urllib.request
from pathlib import Path

from .config import CA_BUNDLE, CA_BUNDLE_URL


def ensure_ca_bundle(path: Path = CA_BUNDLE, dry_run: bool = False, force: bool = False) -> Path:
    """Garante que o ``global-bundle.pem`` exista e pareça um PEM válido."""
    path = Path(path)
    if path.exists() and path.stat().st_size > 1024 and not force:
        return path

    if dry_run:
        print(f"  [dry-run] baixaria {CA_BUNDLE_URL} -> {path}")
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"  baixando CA bundle da AWS: {CA_BUNDLE_URL}")
    try:
        with urllib.request.urlopen(CA_BUNDLE_URL, timeout=60) as response, path.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    except OSError as exc:
        raise SystemExit(
            "não foi possível baixar o CA bundle da AWS.\n"
            f"Baixe manualmente {CA_BUNDLE_URL} e salve em {path}\n"
            f"erro: {exc}"
        ) from exc

    payload = path.read_bytes()
    if b"BEGIN CERTIFICATE" not in payload:
        path.unlink(missing_ok=True)
        raise SystemExit("o arquivo baixado não parece ser um CA bundle PEM válido")

    print(f"  CA bundle salvo em {path} ({len(payload)} bytes)")
    return path
