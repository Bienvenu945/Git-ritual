"""Adresses de dépôts, CLI `gh` (facultative) et ouverture de liens."""

from __future__ import annotations

import difflib
import re
import webbrowser
from dataclasses import dataclass

from core import shell
from utils.validators import ValidationError, validate_repo_name, validate_username

GITHUB_HOST = "github.com"
_PART = r"[A-Za-z0-9_.-]+"
_SSH_RE = re.compile(rf"^(?:ssh://)?git@({_PART})[:/]({_PART})/({_PART}?)(?:\.git)?/?$")
_HTTPS_RE = re.compile(rf"^https://({_PART})/({_PART})/({_PART}?)(?:\.git)?/?$")
_SLUG_RE = re.compile(rf"^({_PART})/({_PART}?)(?:\.git)?$")
_BARE_RE = re.compile(rf"^{_PART}$")


@dataclass(frozen=True)
class RemoteTarget:
    url: str
    host: str | None = None
    owner: str | None = None
    name: str | None = None

    @property
    def is_github(self) -> bool:
        return self.host == GITHUB_HOST

    @property
    def web_url(self) -> str | None:
        if self.is_github and self.owner and self.name:
            return f"https://{GITHUB_HOST}/{self.owner}/{self.name}"
        return None


def ssh_url(owner: str, name: str, host: str = GITHUB_HOST) -> str:
    return f"git@{host}:{owner}/{name}.git"


def is_bare_name(raw: str) -> bool:
    """Vrai si la saisie est un simple nom de dépôt (sans pseudo)."""
    return bool(_BARE_RE.match("".join(raw.split())))


def parse_target(raw: str, default_owner: str | None = None) -> RemoteTarget:
    """Interprète une saisie : « pseudo/depot », « depot », adresse SSH/HTTPS ou chemin local.

    Les espaces parasites (ex. « github.com: pseudo/depot.git ») sont supprimés, et les
    adresses HTTPS de GitHub sont converties en SSH.
    """
    stripped = raw.strip()
    if stripped.startswith(("/", "file://")):  # dépôt local (utile pour tester)
        return RemoteTarget(url=stripped)
    text = "".join(stripped.split())
    if not text:
        raise ValidationError("Aucune adresse indiquée.")
    if text.startswith("-"):
        raise ValidationError("Adresse invalide.")

    for pattern in (_SSH_RE, _HTTPS_RE):
        match = pattern.match(text)
        if match:
            host, owner, name = match.groups()
            if host == GITHUB_HOST:
                return RemoteTarget(ssh_url(owner, name), host, owner, name)
            return RemoteTarget(text, host, owner, name)

    match = _SLUG_RE.match(text)
    if match:
        owner, name = match.groups()
    elif _BARE_RE.match(text):
        if not default_owner:
            raise ValidationError("Indiquez aussi votre pseudo GitHub (format pseudo/depot).")
        owner, name = default_owner, text.removesuffix(".git")
    else:
        raise ValidationError(
            "Format non reconnu. Exemples : pseudo/depot, depot, git@github.com:pseudo/depot.git"
        )
    owner, name = validate_username(owner), validate_repo_name(name)
    return RemoteTarget(ssh_url(owner, name), GITHUB_HOST, owner, name)


def _norm(name: str) -> str:
    return name.lower().replace("-", "_")


def suggest_names(typed: str, existing: list[str], limit: int = 3) -> list[str]:
    """Noms de dépôts proches de la saisie (insensible à la casse et à « - » / « _ »)."""
    by_norm: dict[str, str] = {}
    for name in existing:
        by_norm.setdefault(_norm(name), name)
    close = difflib.get_close_matches(_norm(typed), list(by_norm), n=limit, cutoff=0.6)
    return [by_norm[c] for c in close if by_norm[c] != typed]


# --------------------------------------------------------------------------- #
# CLI gh (facultative)
# --------------------------------------------------------------------------- #
def gh_available() -> bool:
    return shell.which("gh") is not None


def gh_logged_in() -> bool:
    return gh_available() and shell.run(["gh", "auth", "status"], timeout=20).ok


def list_repos(owner: str) -> list[str]:
    result = shell.run(
        ["gh", "repo", "list", owner, "--limit", "200", "--json", "name", "--jq", ".[].name"],
        timeout=40,
    )
    return result.stdout.split() if result.ok else []


def create_repo(owner: str, name: str, private: bool, description: str = "") -> shell.CommandResult:
    command = ["gh", "repo", "create", f"{owner}/{name}", "--private" if private else "--public"]
    if description:
        command += ["--description", description]
    return shell.run(command, timeout=60)


def open_url(url: str) -> bool:
    """Ouvre un lien dans le navigateur (Termux : termux-open-url)."""
    for tool in ("termux-open-url", "xdg-open"):
        if shell.which(tool):
            return shell.run([tool, url], timeout=15).ok
    try:
        return webbrowser.open(url)
    except webbrowser.Error:
        return False
