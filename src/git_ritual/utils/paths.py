"""Résolution des chemins de projets saisis par l'utilisateur."""

from __future__ import annotations

from pathlib import Path

from git_ritual.utils.validators import ValidationError


def resolve_project_path(
    raw: str, base_dir: str | Path | None = None, home: Path | None = None
) -> Path:
    """Retourne le dossier de projet désigné par `raw`.

    Un chemin relatif est cherché dans le dossier courant, puis dans `base_dir`.
    Le dossier personnel et la racine sont refusés : on publie un projet, pas tout son téléphone.
    """
    text = raw.strip().strip("\"'")
    if not text:
        raise ValidationError("Aucun dossier indiqué.")
    path = Path(text).expanduser()
    if not path.is_absolute():
        in_cwd = Path.cwd() / path
        if in_cwd.exists() or base_dir is None:
            path = in_cwd
        else:
            path = Path(base_dir).expanduser() / path
    if not path.exists():
        raise ValidationError(f"Dossier introuvable : {path}")
    if not path.is_dir():
        raise ValidationError(f"Ce chemin n'est pas un dossier : {path}")
    path = path.resolve()
    forbidden = {(home or Path.home()).resolve(), Path(path.anchor)}
    if path in forbidden:
        raise ValidationError(
            "Choisissez le dossier du projet, pas votre dossier personnel ni la racine."
        )
    return path
