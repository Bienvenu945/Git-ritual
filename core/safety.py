"""Garde-fous avant publication : fichiers sensibles et .gitignore."""

from __future__ import annotations

import fnmatch
from pathlib import Path, PurePosixPath
from typing import Iterable

RISKY_PATTERNS = (
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "*.keystore",
    "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa", "secrets.*", "credentials*.json",
)
SAFE_SUFFIXES = (".example", ".sample", ".template", ".dist")

PYTHON_GITIGNORE = """\
__pycache__/
*.py[cod]
.venv/
venv/
.env
build/
dist/
*.egg-info/
.pytest_cache/
.DS_Store
"""


def risky_files(paths: Iterable[str]) -> list[str]:
    """Chemins dont le nom évoque un secret (clé privée, .env, jeton…)."""
    found = []
    for path in paths:
        name = PurePosixPath(path).name.lower()
        if name.endswith(SAFE_SUFFIXES):
            continue
        if any(fnmatch.fnmatch(name, pattern) for pattern in RISKY_PATTERNS):
            found.append(path)
    return found


def add_to_gitignore(project: str | Path, entries: Iterable[str]) -> Path:
    """Ajoute des chemins (ancrés à la racine) au .gitignore, sans doublon."""
    path = Path(project) / ".gitignore"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    present = set(existing.splitlines())
    new = [f"/{PurePosixPath(e).as_posix()}" for e in entries]
    new = [line for line in new if line not in present]
    if new:
        if existing and not existing.endswith("\n"):
            existing += "\n"
        path.write_text(existing + "\n".join(new) + "\n", encoding="utf-8")
    return path


def looks_like_python(project: str | Path) -> bool:
    root = Path(project)
    return any(root.glob("*.py")) or any(root.glob("*/*.py"))


def write_default_gitignore(project: str | Path) -> Path:
    path = Path(project) / ".gitignore"
    if not path.exists():
        path.write_text(PYTHON_GITIGNORE, encoding="utf-8")
    return path
