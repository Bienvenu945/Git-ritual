"""Mise à jour d'un projet déjà publié, statut et correction de l'adresse distante."""

from __future__ import annotations

from git_ritual.core import git_ops, storage
from git_ritual.interface import display
from git_ritual.workflows import common
from git_ritual.workflows.errors import FlowError


def _open_repo() -> git_ops.Repo:
    common.require_git()
    repo = git_ops.Repo(common.choose_project())
    if not repo.is_repo():
        raise FlowError("Ce dossier n'est pas un dépôt Git. Utilisez « Publier un projet ».")
    return repo


def update_project() -> None:
    """add + commit + push, avec récupération automatique en cas de rejet."""
    common.require_git()
    common.ensure_identity()
    repo = _open_repo()
    if repo.get_remote_url() is None:
        raise FlowError("Aucune adresse distante : utilisez « Publier un projet » ou « Corriger l'adresse ».")
    branch = repo.current_branch()
    if branch is None:
        raise FlowError("HEAD détaché : revenez d'abord sur une branche (git switch main).")

    display.step(1, 2, "Commit")
    if not common.commit_changes(repo):
        display.info("Aucune nouvelle modification locale.")
    display.step(2, 2, "Envoi")
    if not common.push_with_recovery(repo, branch):
        raise FlowError("Mise à jour interrompue. Rien n'est perdu.")
    storage.add_recent_project(repo.path)


def _sync_text(state: tuple[int, int] | None) -> str:
    if state is None:
        return "aucune branche suivie (jamais envoyé ?)"
    ahead, behind = state
    if ahead and behind:
        return f"divergence : {ahead} à envoyer, {behind} à récupérer"
    if ahead:
        return f"{ahead} commit(s) à envoyer"
    if behind:
        return f"{behind} commit(s) à récupérer"
    return "à jour (d'après la dernière synchronisation)"


def show_status() -> None:
    common.require_git()
    project = common.choose_project()
    repo = git_ops.Repo(project)
    rows = [("Dossier", str(project))]
    if not repo.is_repo():
        rows.append(("Git", "pas encore initialisé"))
        display.show_summary("Statut", rows)
        return
    changes = repo.changes()
    rows += [
        ("Branche", repo.current_branch() or "HEAD détaché"),
        ("Adresse", repo.get_remote_url() or "aucune"),
        ("Synchronisation", _sync_text(repo.ahead_behind()) if repo.has_commits() else "aucun commit"),
        ("Modifications", f"{len(changes)} fichier(s)" if changes else "aucune"),
    ]
    display.show_summary("Statut", rows)
    if changes:
        display.show_changes(changes)
    display.show_commits(repo.log(5))


def fix_remote() -> None:
    """Remplace l'adresse « origin » (faute de frappe, mauvais nom…), après vérification."""
    repo = _open_repo()
    common.configure_remote(repo, offer_keep=False)
