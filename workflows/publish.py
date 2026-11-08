"""Le rituel complet : init → commit → branche → remote → push."""

from __future__ import annotations

from core import git_ops, safety, storage
from interface import display, prompts
from workflows import common
from workflows.errors import Cancelled, FlowError

TOTAL_STEPS = 5


def _ensure_local_repo(repo: git_ops.Repo) -> None:
    if repo.is_repo():
        display.info(f"Dépôt Git déjà initialisé (branche « {repo.current_branch()} »).")
        return
    parent = repo.parent_repo()
    if parent:
        display.warning(f"Ce dossier se trouve déjà dans un autre dépôt Git : {parent}")
        if not prompts.ask_confirm("Créer quand même un dépôt séparé ici ?", default=False):
            raise Cancelled()
    elif not prompts.ask_confirm("Ce dossier n'est pas un dépôt Git. L'initialiser ?"):
        raise Cancelled()
    repo.init(storage.load_settings()["default_branch"])
    display.success("Dépôt Git initialisé.")


def _offer_gitignore(repo: git_ops.Repo) -> None:
    if (repo.path / ".gitignore").exists() or not safety.looks_like_python(repo.path):
        return
    if prompts.ask_confirm("Ajouter un .gitignore Python (cache, venv, .env) ?"):
        safety.write_default_gitignore(repo.path)
        display.success(".gitignore créé.")


def _ensure_branch(repo: git_ops.Repo) -> str:
    wanted = storage.load_settings()["default_branch"]
    current = repo.current_branch()
    if current is None:
        raise FlowError("HEAD détaché : revenez d'abord sur une branche (git switch main).")
    if current == wanted:
        display.info(f"Branche : {current}")
        return current
    if prompts.ask_confirm(f"La branche s'appelle « {current} ». La renommer en « {wanted} » ?"):
        outcome = repo.rename_branch(wanted)
        if not outcome.ok:
            display.explain_error(outcome.kind, outcome.output)
            raise FlowError("Renommage de la branche impossible.")
        display.success(f"Branche renommée en « {wanted} ».")
        return wanted
    return current


def publish() -> None:
    """Publie un dossier sur GitHub en gérant les cas qui posent problème."""
    common.require_git()
    common.ensure_identity()
    project = common.choose_project()
    repo = git_ops.Repo(project)

    display.step(1, TOTAL_STEPS, "Dépôt local")
    _ensure_local_repo(repo)

    display.step(2, TOTAL_STEPS, "Fichiers et commit")
    _offer_gitignore(repo)
    committed = common.commit_changes(repo)
    if not repo.has_commits():
        raise FlowError("Le dossier ne contient rien à publier.")
    if not committed:
        display.info("Aucune nouvelle modification à valider.")

    display.step(3, TOTAL_STEPS, "Branche")
    branch = _ensure_branch(repo)

    display.step(4, TOTAL_STEPS, "Adresse du dépôt")
    target = common.configure_remote(repo)

    display.step(5, TOTAL_STEPS, "Envoi")
    if not common.push_with_recovery(repo, branch):
        raise FlowError("Publication interrompue. Rien n'est perdu : vous pouvez relancer le rituel.")

    storage.add_recent_project(project)
    last = (repo.log(1) or ["-"])[0]
    display.show_summary("🎉 Publié !", [
        ("Dossier", str(project)),
        ("Branche", branch),
        ("Adresse", target.url),
        ("Page", target.web_url or target.url),
        ("Dernier commit", last),
    ])
