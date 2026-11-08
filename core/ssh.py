"""Clés SSH et test de connexion à GitHub."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from core import shell
from core.diagnostics import ErrorKind, classify

GITHUB_HOST = "github.com"
_HI = re.compile(r"Hi ([A-Za-z0-9-]+)! You've successfully authenticated")


class SshError(Exception):
    """Erreur de gestion des clés SSH."""


@dataclass(frozen=True)
class SshTest:
    status: str            # "ok" | "denied" | "hostkey" | "network" | "error"
    username: str | None
    detail: str


def ssh_dir() -> Path:
    return Path.home() / ".ssh"


def find_public_keys() -> list[Path]:
    directory = ssh_dir()
    keys = list(directory.glob("*.pub")) if directory.is_dir() else []
    return sorted(keys, key=lambda p: (not p.stem.endswith("ed25519"), p.name))


def generate_key(email: str, filename: str = "id_ed25519") -> Path:
    """Crée une clé ed25519 sans phrase secrète. Ne remplace jamais une clé existante."""
    directory = ssh_dir()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    private = directory / filename
    public = Path(str(private) + ".pub")
    if private.exists() or public.exists():
        raise SshError(f"Une clé existe déjà : {private}")
    result = shell.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-C", email, "-f", str(private), "-N", ""], timeout=30
    )
    if not result.ok:
        raise SshError(result.output or "ssh-keygen a échoué.")
    return public


def public_key_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise SshError(f"Lecture impossible de {path} : {exc.strerror or exc}") from exc


def known_host(host: str = GITHUB_HOST) -> bool:
    """Vrai si l'empreinte du serveur est déjà enregistrée (known_hosts)."""
    result = shell.run(["ssh-keygen", "-F", host])
    return result.ok and bool(result.stdout.strip())


def trust_host_interactively() -> int:
    """Première connexion : laisse SSH poser sa question yes/no dans le terminal."""
    return shell.run_interactive(
        ["ssh", "-T", "-o", "StrictHostKeyChecking=ask", f"git@{GITHUB_HOST}"]
    )


def test_github() -> SshTest:
    """Teste l'authentification SSH auprès de GitHub et lit le pseudo associé."""
    result = shell.run(["ssh", "-T", "-o", "ConnectTimeout=10", f"git@{GITHUB_HOST}"], timeout=40)
    text = result.output
    match = _HI.search(text)
    if match:
        return SshTest("ok", match.group(1), text)
    kind = classify(text)
    status = {
        ErrorKind.AUTH_SSH: "denied",
        ErrorKind.HOSTKEY: "hostkey",
        ErrorKind.NETWORK: "network",
    }.get(kind, "error")
    return SshTest(status, None, text)
