"""Opérations Git : dépôt local, commits, remote, push, fusion et conflits."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from git_ritual.core import shell
from git_ritual.core.diagnostics import ErrorKind, classify

REMOTE = "origin"


class GitError(Exception):
    """Erreur Git inattendue (le message contient la sortie de Git)."""


@dataclass(frozen=True)
class Outcome:
    ok: bool
    kind: ErrorKind
    output: str


@dataclass(frozen=True)
class Change:
    code: str   # code « porcelain » à 2 caractères : "??", " M", "A ", " D"…
    path: str

    @property
    def untracked(self) -> bool:
        return self.code == "??"


def _outcome(result: shell.CommandResult) -> Outcome:
    if result.ok:
        return Outcome(True, ErrorKind.NONE, result.output)
    return Outcome(False, classify(result.output), result.output)


# --------------------------------------------------------------------------- #
# Configuration globale
# --------------------------------------------------------------------------- #
def git_installed() -> bool:
    return shell.which("git") is not None


def git_version() -> str:
    result = shell.run(["git", "--version"])
    return result.stdout.strip().removeprefix("git version ") if result.ok else ""


def get_identity() -> tuple[str, str]:
    name = shell.run(["git", "config", "--get", "user.name"]).stdout.strip()
    email = shell.run(["git", "config", "--get", "user.email"]).stdout.strip()
    return name, email


def set_identity(name: str, email: str) -> Outcome:
    for key, value in (("user.name", name), ("user.email", email)):
        result = shell.run(["git", "config", "--global", key, value])
        if not result.ok:
            return _outcome(result)
    return Outcome(True, ErrorKind.NONE, "")


def set_defaults(branch: str = "main") -> Outcome:
    """Fusion par défaut (pas de rebase) et branche initiale."""
    for key, value in (("pull.rebase", "false"), ("init.defaultBranch", branch)):
        result = shell.run(["git", "config", "--global", key, value])
        if not result.ok:
            return _outcome(result)
    return Outcome(True, ErrorKind.NONE, "")


def check_remote(url: str, timeout: int = 30) -> Outcome:
    """Vérifie qu'une adresse est joignable et que le dépôt existe (git ls-remote)."""
    if url.startswith("-"):
        return Outcome(False, ErrorKind.OTHER, "Adresse invalide.")
    return _outcome(shell.run(["git", "ls-remote", url], timeout=timeout))


# --------------------------------------------------------------------------- #
# Dépôt local
# --------------------------------------------------------------------------- #
class Repo:
    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()

    def _git(self, *args: str, timeout: int = 60) -> shell.CommandResult:
        return shell.run(["git", "-c", "core.quotepath=false", *args], cwd=self.path, timeout=timeout)

    # -- état ---------------------------------------------------------------
    def toplevel(self) -> Path | None:
        result = self._git("rev-parse", "--show-toplevel")
        return Path(result.stdout.strip()).resolve() if result.ok else None

    def is_repo(self) -> bool:
        return self.toplevel() == self.path.resolve()

    def parent_repo(self) -> Path | None:
        """Dépôt Git qui contient ce dossier sans en être la racine (cas à éviter)."""
        top = self.toplevel()
        return top if top and top != self.path.resolve() else None

    def has_commits(self) -> bool:
        return self._git("rev-parse", "-q", "--verify", "HEAD").ok

    def current_branch(self) -> str | None:
        result = self._git("symbolic-ref", "--short", "HEAD")
        return result.stdout.strip() if result.ok else None

    def changes(self) -> list[Change]:
        result = self._git("status", "--porcelain=v1", "-z", "-uall")
        if not result.ok:
            raise GitError(result.output)
        entries = result.stdout.split("\0")
        found: list[Change] = []
        i = 0
        while i < len(entries):
            entry = entries[i]
            i += 1
            if len(entry) < 4:
                continue
            code, path = entry[:2], entry[3:]
            if "R" in code or "C" in code:
                i += 1  # saute l'ancien nom
            found.append(Change(code, path))
        return found

    def log(self, count: int = 5) -> list[str]:
        result = self._git("log", "--oneline", "-n", str(count))
        return result.stdout.strip().splitlines() if result.ok else []

    def ahead_behind(self) -> tuple[int, int] | None:
        """(commits à envoyer, commits à récupérer), ou None sans branche suivie."""
        result = self._git("rev-list", "--left-right", "--count", "HEAD...@{u}")
        if not result.ok:
            return None
        ahead, behind = result.stdout.split()
        return int(ahead), int(behind)

    # -- modifications ------------------------------------------------------
    def init(self, branch: str = "main") -> None:
        result = self._git("init")
        if result.ok:
            result = self._git("symbolic-ref", "HEAD", f"refs/heads/{branch}")
        if not result.ok:
            raise GitError(result.output)

    def rename_branch(self, name: str) -> Outcome:
        if self.has_commits():
            return _outcome(self._git("branch", "-M", name))
        return _outcome(self._git("symbolic-ref", "HEAD", f"refs/heads/{name}"))

    def add_all(self) -> Outcome:
        return _outcome(self._git("add", "-A"))

    def commit(self, message: str) -> Outcome:
        return _outcome(self._git("commit", "-m", message))

    # -- remote -------------------------------------------------------------
    def get_remote_url(self, name: str = REMOTE) -> str | None:
        result = self._git("remote", "get-url", name)
        return result.stdout.strip() if result.ok else None

    def set_remote(self, url: str, name: str = REMOTE) -> Outcome:
        if self.get_remote_url(name) is None:
            return _outcome(self._git("remote", "add", name, url))
        return _outcome(self._git("remote", "set-url", name, url))

    def push(self, branch: str) -> Outcome:
        """Envoi simple. N'utilise jamais --force."""
        return _outcome(self._git("push", "-u", REMOTE, branch, timeout=180))

    def pull_merge(self, branch: str) -> Outcome:
        """Récupère et fusionne la branche distante (historiques sans lien autorisés)."""
        result = self._git(
            "pull", REMOTE, branch, "--allow-unrelated-histories", "--no-rebase", "--no-edit",
            timeout=180,
        )
        outcome = _outcome(result)
        if not outcome.ok and self.merge_in_progress():
            return Outcome(False, ErrorKind.CONFLICT, outcome.output)
        return outcome

    # -- conflits -----------------------------------------------------------
    def merge_in_progress(self) -> bool:
        return self._git("rev-parse", "-q", "--verify", "MERGE_HEAD").ok

    def conflicted_files(self) -> list[str]:
        result = self._git("diff", "--name-only", "--diff-filter=U", "-z")
        return [p for p in result.stdout.split("\0") if p]

    def resolve_conflicts(self, strategy: str) -> Outcome:
        """`ours` garde vos fichiers, `theirs` ceux du dépôt distant ; puis finalise la fusion."""
        if strategy not in ("ours", "theirs"):
            raise ValueError("strategy doit être 'ours' ou 'theirs'")
        for file in self.conflicted_files():
            result = self._git("checkout", f"--{strategy}", "--", file)
            if result.ok:
                result = self._git("add", "--", file)
            else:  # fichier supprimé d'un côté : on applique la suppression
                result = self._git("rm", "-f", "--", file)
            if not result.ok:
                return _outcome(result)
        return _outcome(self._git("commit", "--no-edit"))

    def abort_merge(self) -> Outcome:
        return _outcome(self._git("merge", "--abort"))
