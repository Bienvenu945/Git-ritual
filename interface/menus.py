"""Menu principal, réglages et gestion uniforme des erreurs."""

from __future__ import annotations

from typing import Callable

from core import git_ops, shell, ssh, storage
from interface import display, prompts
from utils.validators import ValidationError, validate_branch, validate_commit_message, validate_username
from workflows import publish, setup, sync
from workflows.errors import Cancelled, FlowError

Handler = Callable[[], None]

MAIN_OPTIONS = [
    ("1", "🚀 Publier un projet sur GitHub"),
    ("2", "🔄 Mettre à jour un projet"),
    ("3", "🔍 Statut d'un projet"),
    ("4", "🔧 Corriger l'adresse du dépôt"),
    ("5", "🧙 Assistant de configuration"),
    ("s", "⚙️  Réglages"),
    ("0", "Quitter"),
]
TERMUX_PACKAGES = {"git": "git", "ssh": "openssh", "ssh-keygen": "openssh", "gh": "gh"}


def _run(handler: Handler) -> None:
    """Exécute un parcours : aucune erreur attendue ne ferme l'application."""
    try:
        handler()
    except Cancelled:
        display.warning("Annulé.")
    except (FlowError, ValidationError) as exc:
        display.error(str(exc))
    except git_ops.GitError as exc:
        display.error(f"Erreur Git : {exc}")
    except shell.ToolMissingError as exc:
        package = TERMUX_PACKAGES.get(exc.tool, exc.tool)
        display.error(f"Outil introuvable : {exc.tool}. Dans Termux : pkg install {package}")
    except (KeyboardInterrupt, EOFError):
        display.console.print()
        display.warning("Opération annulée.")
    prompts.pause()


def health_checks() -> list[tuple[str, bool, str]]:
    """Vérifications locales rapides (aucun accès réseau)."""
    installed = git_ops.git_installed()
    name, email = git_ops.get_identity() if installed else ("", "")
    keys = ssh.find_public_keys()
    username = storage.load_settings()["github_username"]
    return [
        ("Git", installed, git_ops.git_version() if installed else "pkg install git openssh"),
        ("Identité", bool(name and email), f"{name} <{email}>" if name and email else "à configurer (5)"),
        ("Clé SSH", bool(keys), keys[0].name if keys else "à créer (5)"),
        ("Compte GitHub", bool(username), username or "pas encore testé (5)"),
    ]


# --------------------------------------------------------------------------- #
# Réglages
# --------------------------------------------------------------------------- #
def _save(settings: dict) -> None:
    if storage.save_settings(settings):
        display.success("Réglages enregistrés.")
    else:
        display.error("Impossible d'enregistrer les réglages (dossier de données inaccessible).")


def _ask_validated(label: str, validator, default: str) -> str:
    while True:
        try:
            return validator(prompts.ask_text(label, default=default))
        except ValidationError as exc:
            display.error(str(exc))


def _change_setting(key: str) -> None:
    settings = storage.load_settings()
    if key == "accent":
        settings[key] = prompts.ask_choice(
            f"Couleur ({', '.join(storage.ACCENT_CHOICES)})", storage.ACCENT_CHOICES, default=settings[key]
        )
        display.set_accent(settings[key])
    elif key == "github_username":
        settings[key] = _ask_validated("Pseudo GitHub", validate_username, settings[key])
    elif key == "default_branch":
        settings[key] = _ask_validated("Branche par défaut", validate_branch, settings[key])
    elif key == "default_commit_message":
        settings[key] = _ask_validated("Message de commit par défaut", validate_commit_message, settings[key])
    else:
        settings[key] = prompts.ask_text("Dossier des projets", default=settings[key]).strip() or "~"
    _save(settings)


def _reset_settings() -> None:
    if prompts.ask_confirm("Remettre tous les réglages par défaut ?", default=False):
        display.set_accent(storage.DEFAULT_SETTINGS["accent"])
        _save(dict(storage.DEFAULT_SETTINGS))


def settings_menu() -> None:
    entries: list[tuple[str, str, Handler]] = [
        ("1", "Pseudo GitHub", lambda: _change_setting("github_username")),
        ("2", "Branche par défaut", lambda: _change_setting("default_branch")),
        ("3", "Message de commit par défaut", lambda: _change_setting("default_commit_message")),
        ("4", "Dossier des projets", lambda: _change_setting("projects_dir")),
        ("5", "Couleur d'accent", lambda: _change_setting("accent")),
        ("6", "Réinitialiser", _reset_settings),
    ]
    handlers = {key: handler for key, _, handler in entries}
    while True:
        s = storage.load_settings()
        display.show_summary("Réglages", [
            ("Pseudo GitHub", s["github_username"] or "(non défini)"),
            ("Branche par défaut", s["default_branch"]),
            ("Message par défaut", s["default_commit_message"]),
            ("Dossier des projets", s["projects_dir"]),
            ("Couleur", s["accent"]),
            ("Données", str(storage.app_home())),
        ])
        try:
            choice = prompts.choose("Réglages", [(k, label) for k, label, _ in entries] + [("0", "Retour")])
        except (KeyboardInterrupt, EOFError):
            display.console.print()
            return
        if choice == "0":
            return
        _run(handlers[choice])


# --------------------------------------------------------------------------- #
# Boucle principale
# --------------------------------------------------------------------------- #
def run() -> None:
    display.set_accent(storage.load_settings()["accent"])
    actions: dict[str, Handler] = {
        "1": lambda: _run(publish.publish),
        "2": lambda: _run(sync.update_project),
        "3": lambda: _run(sync.show_status),
        "4": lambda: _run(sync.fix_remote),
        "5": lambda: _run(setup.wizard),
        "s": settings_menu,
    }
    while True:
        display.clear()
        display.show_banner()
        display.show_health(health_checks())
        display.show_menu("Que voulez-vous faire ?", MAIN_OPTIONS)
        try:
            choice = prompts.ask_choice("Votre choix", [*actions, "0"])
        except (KeyboardInterrupt, EOFError):
            choice = "0"
        if choice == "0":
            display.info("À bientôt !")
            return
        actions[choice]()
