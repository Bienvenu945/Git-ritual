"""Réglages persistants (JSON) : pseudo GitHub, branche, projets récents…"""

from __future__ import annotations

import json
import os
from pathlib import Path

APP_DIR_NAME = ".git-ritual"
ACCENT_CHOICES = ("cyan", "green", "magenta", "yellow", "blue", "red", "white")
RECENT_LIMIT = 8
DEFAULT_SETTINGS = {
    "github_username": "",
    "default_branch": "main",
    "default_commit_message": "Mise à jour",
    "projects_dir": "~",
    "accent": "cyan",
    "recent_projects": [],
}


def app_home() -> Path:
    """Dossier de données (surchargeable via GIT_RITUAL_HOME)."""
    override = os.environ.get("GIT_RITUAL_HOME")
    return Path(override).expanduser() if override else Path.home() / APP_DIR_NAME


def settings_path() -> Path:
    return app_home() / "settings.json"


def load_settings() -> dict:
    """Réglages valides ; toute valeur absente ou incorrecte retombe sur le défaut."""
    settings = {k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULT_SETTINGS.items()}
    try:
        stored = json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return settings
    if isinstance(stored, dict):
        for key, default in DEFAULT_SETTINGS.items():
            if isinstance(stored.get(key), type(default)):
                settings[key] = stored[key]
    if settings["accent"] not in ACCENT_CHOICES:
        settings["accent"] = DEFAULT_SETTINGS["accent"]
    settings["recent_projects"] = [p for p in settings["recent_projects"] if isinstance(p, str)]
    return settings


def save_settings(settings: dict) -> bool:
    path = settings_path()
    payload = {k: settings.get(k, v) for k, v in DEFAULT_SETTINGS.items()}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        return False
    return True


def add_recent_project(project: str | Path) -> bool:
    """Place un projet en tête de la liste des récents (sans doublon)."""
    settings = load_settings()
    value = str(project)
    recents = [value] + [p for p in settings["recent_projects"] if p != value]
    settings["recent_projects"] = recents[:RECENT_LIMIT]
    return save_settings(settings)
