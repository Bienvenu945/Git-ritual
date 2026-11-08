"""Briques partagées par les parcours : projet, commit, adresse distante, envoi."""

from __future__ import annotations

import re
from pathlib import Path

from core import git_ops, github, safety, storage
from core.diagnostics import ErrorKind
from interface import display, prompts
from utils.paths import resolve_project_path
from utils.validators import ValidationError, validate_commit_message, validate_username
from workflows import setup
from workflows.errors import Cancelled, FlowError

MAX_PUSH_ATTEMPTS = 3


# --------------------------------------------------------------------------- #
# Prérequis
# --------------------------------------------------------------------------- #
def require_git() -> None:
    if not git_ops.git_installed():
        raise FlowError("Git n'est pas installé. Dans Termux : pkg install git openssh")


def ensure_identity() -> None:
    name, email = git_ops.get_identity()
    if name and email:
        return
    display.warning("Git ne connaît pas encore votre identité : configurons-la.")
    setup.setup_identity()


def choose_project() -> Path:
    settings = storage.load_settings()
    recents = [p for p in settings["recent_projects"] if Path(p).expanduser().is_dir()]
    options = [("c", f"Dossier courant : {Path.cwd()}")]
    options += [(str(i), path) for i, path in enumerate(recents, 1)]
    options += [("a", "Autre dossier…"), ("0", "Annuler")]
    while True:
        choice = prompts.choose("Quel projet ?", options, default="c")
        if choice == "0":
            raise Cancelled()
        if choice == "c":
            raw = str(Path.cwd())
        elif choice == "a":
            raw = prompts.ask_text("Chemin du dossier (ex. ~/mon-projet ou juste mon-projet)")
        else:
            raw = recents[int(choice) - 1]
        try:
            return resolve_project_path(raw, base_dir=settings["projects_dir"])
        except ValidationError as exc:
            display.error(str(exc))


# --------------------------------------------------------------------------- #
# Commit
# --------------------------------------------------------------------------- #
def _ask_message(default: str) -> str:
    while True:
        try:
            return validate_commit_message(prompts.ask_text("Message du commit", default=default))
        except ValidationError as exc:
            display.error(str(exc))


def _guard_secrets(repo: git_ops.Repo, changes: list[git_ops.Change]) -> None:
    tracked = safety.risky_files(c.path for c in changes if not c.untracked)
    if tracked:
        display.warning(
            "Fichiers sensibles déjà suivis par Git : " + ", ".join(tracked)
            + " (retirez-les avec : git rm --cached <fichier>)."
        )
    risky = safety.risky_files(c.path for c in changes if c.untracked)
    if not risky:
        return
    display.warning("Ces fichiers ressemblent à des secrets (clés, .env…) :")
    for path in risky:
        display.dim(f"  {path}")
    keep_out = prompts.ask_confirm("Les exclure de la publication (ajout au .gitignore) ?", default=True)
    if not keep_out:
        keep_out = not prompts.ask_confirm(
            "Vraiment les publier ? Un secret publié doit être considéré comme compromis.", default=False
        )
    if keep_out:
        safety.add_to_gitignore(repo.path, risky)
        display.success("Exclus via .gitignore.")
    else:
        display.warning("Ils seront publiés.")


def commit_changes(repo: git_ops.Repo) -> bool:
    """Ajoute et valide les modifications. Retourne False s'il n'y avait rien à valider."""
    changes = repo.changes()
    if not changes:
        return False
    display.show_changes(changes)
    _guard_secrets(repo, changes)
    if not repo.changes():  # tout a été exclu
        return False
    settings = storage.load_settings()
    default = settings["default_commit_message"] if repo.has_commits() else "Initial commit"
    message = _ask_message(default)
    outcome = repo.add_all()
    if outcome.ok:
        outcome = repo.commit(message)
    if not outcome.ok:
        if outcome.kind is ErrorKind.NOTHING_TO_COMMIT:
            return False
        display.explain_error(outcome.kind, outcome.output)
        raise FlowError("Le commit a échoué.")
    display.success(f"Commit créé : « {message} »")
    return True


# --------------------------------------------------------------------------- #
# Adresse distante
# --------------------------------------------------------------------------- #
def _ask_target(repo: git_ops.Repo) -> github.RemoteTarget:
    settings = storage.load_settings()
    username = settings["github_username"]
    folder = re.sub(r"[^A-Za-z0-9._-]+", "-", repo.path.name).strip("-") or "projet"
    default = f"{username}/{folder}" if username else folder
    while True:
        raw = prompts.ask_text("Dépôt GitHub (pseudo/depot, depot ou adresse complète)", default=default)
        try:
            if github.is_bare_name(raw) and not username:
                username = validate_username(prompts.ask_text("Votre pseudo GitHub"))
                settings["github_username"] = username
                storage.save_settings(settings)
            target = github.parse_target(raw, default_owner=username or None)
        except ValidationError as exc:
            display.error(str(exc))
            continue
        display.info(f"Adresse utilisée : {target.url}")
        return target


def _suggest_similar(target: github.RemoteTarget) -> github.RemoteTarget | None:
    """Si `gh` est connecté, propose les dépôts du compte dont le nom ressemble."""
    if not (target.is_github and target.owner and target.name and github.gh_logged_in()):
        return None
    names = github.suggest_names(target.name, github.list_repos(target.owner))
    if not names:
        return None
    display.info("Dépôts proches sur votre compte : " + ", ".join(names))
    if prompts.ask_confirm(f"Utiliser « {names[0]} » ?"):
        return github.parse_target(f"{target.owner}/{names[0]}")
    return None


def _create_with_gh(target: github.RemoteTarget) -> None:
    private = prompts.choose(
        "Visibilité", [("1", "Privé"), ("2", "Public")], default="1"
    ) == "1"
    description = prompts.ask_text("Description (facultatif)", default="").strip()
    result = github.create_repo(target.owner, target.name, private, description)
    if result.ok:
        display.success(f"Dépôt créé : {target.owner}/{target.name}")
    else:
        display.error("Création impossible avec gh.")
        display.dim(result.output[-300:])


def _handle_remote_failure(kind: ErrorKind, target: github.RemoteTarget) -> github.RemoteTarget | None:
    """Retourne l'adresse à revérifier, ou None pour en saisir une autre. Lève Cancelled."""
    if kind is ErrorKind.NOT_FOUND:
        replacement = _suggest_similar(target)
        if replacement:
            return replacement
    if kind in (ErrorKind.AUTH_SSH, ErrorKind.HOSTKEY):
        if prompts.ask_confirm("Lancer l'assistant SSH maintenant ?"):
            setup.setup_ssh()
            return target
    options = [("1", "Réessayer la même adresse")]
    can_create = kind is ErrorKind.NOT_FOUND and target.is_github and target.owner and github.gh_logged_in()
    if can_create:
        options.append(("2", "Créer le dépôt avec gh"))
    if kind is ErrorKind.NOT_FOUND and target.is_github:
        options.append(("3", "Ouvrir github.com/new (création dans le navigateur)"))
    options += [("4", "Saisir une autre adresse"), ("0", "Annuler")]
    choice = prompts.choose("Que faire ?", options, default="1")
    if choice == "0":
        raise Cancelled()
    if choice == "2":
        _create_with_gh(target)
    elif choice == "3":
        if not github.open_url("https://github.com/new"):
            display.warning("Ouverture impossible : allez sur https://github.com/new")
        display.dim("Créez un dépôt VIDE (sans README ni licence).")
        prompts.wait_enter("Appuyez sur Entrée quand le dépôt est créé…")
    return None if choice == "4" else target


def configure_remote(repo: git_ops.Repo, offer_keep: bool = True) -> github.RemoteTarget:
    """Détermine, vérifie puis enregistre l'adresse « origin » du dépôt."""
    pending: github.RemoteTarget | None = None
    current = repo.get_remote_url()
    if current and offer_keep:
        display.info(f"Adresse actuelle : {current}")
        if prompts.ask_confirm("Garder cette adresse ?"):
            try:
                pending = github.parse_target(current)
            except ValidationError:
                pending = github.RemoteTarget(url=current)
    while True:
        target = pending or _ask_target(repo)
        pending = None
        display.info("Vérification de l'adresse…")
        outcome = git_ops.check_remote(target.url)
        if outcome.ok:
            break
        display.explain_error(outcome.kind, outcome.output)
        pending = _handle_remote_failure(outcome.kind, target)
    saved = repo.set_remote(target.url)
    if not saved.ok:
        raise FlowError(f"Impossible d'enregistrer l'adresse : {saved.output}")
    display.success(f"Adresse « origin » enregistrée : {target.url}")
    return target


# --------------------------------------------------------------------------- #
# Fusion et envoi
# --------------------------------------------------------------------------- #
def _resolve_conflicts(repo: git_ops.Repo) -> bool:
    files = repo.conflicted_files()
    display.warning(f"{len(files)} fichier(s) en conflit :")
    for path in files[:10]:
        display.dim(f"  {path}")
    display.dim("Seuls ces fichiers sont concernés ; les autres fichiers de GitHub sont conservés.")
    choice = prompts.choose(
        "Quelle version garder ?",
        [("1", "La mienne (celle de mon téléphone)"), ("2", "Celle de GitHub"), ("3", "Annuler la fusion")],
        default="1",
    )
    if choice == "3":
        repo.abort_merge()
        display.warning("Fusion annulée : vos fichiers sont inchangés.")
        return False
    outcome = repo.resolve_conflicts("ours" if choice == "1" else "theirs")
    if not outcome.ok:
        display.explain_error(outcome.kind, outcome.output)
        return False
    display.success("Conflits résolus et fusion validée.")
    return True


def merge_remote(repo: git_ops.Repo, branch: str) -> bool:
    display.info("Récupération des fichiers de GitHub…")
    outcome = repo.pull_merge(branch)
    if outcome.ok:
        display.success("Fusion réussie.")
        return True
    if outcome.kind is ErrorKind.CONFLICT:
        return _resolve_conflicts(repo)
    display.explain_error(outcome.kind, outcome.output)
    return False


def push_with_recovery(repo: git_ops.Repo, branch: str) -> bool:
    """Envoie la branche ; en cas de rejet, propose la fusion puis réessaie. Jamais de --force."""
    for _ in range(MAX_PUSH_ATTEMPTS):
        display.info(f"Envoi de « {branch} » vers le dépôt distant…")
        outcome = repo.push(branch)
        if outcome.ok:
            display.success("Envoi réussi.")
            return True
        display.explain_error(outcome.kind, outcome.output)
        if outcome.kind in (ErrorKind.REJECTED, ErrorKind.DIVERGENT, ErrorKind.UNRELATED):
            if not prompts.ask_confirm("Fusionner les fichiers de GitHub avec les vôtres, puis réessayer ?"):
                display.dim("Cet outil n'effectue jamais d'envoi forcé (--force).")
                return False
            if not merge_remote(repo, branch):
                return False
        elif outcome.kind in (ErrorKind.AUTH_SSH, ErrorKind.HOSTKEY):
            if not prompts.ask_confirm("Lancer l'assistant SSH ?") or not setup.setup_ssh():
                return False
        else:
            return False
    display.error("Trop de tentatives : arrêt par sécurité.")
    return False
