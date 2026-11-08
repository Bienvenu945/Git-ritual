"""Assistant de configuration : identité Git et clé SSH GitHub."""

from __future__ import annotations

from core import git_ops, github, shell, ssh, storage
from interface import display, prompts
from utils.validators import ValidationError, validate_email, validate_name
from workflows.errors import Cancelled, FlowError

SSH_KEYS_URL = "https://github.com/settings/ssh/new"
MAX_SSH_RETRIES = 3


def _ask_valid(label: str, validator, default: str | None = None) -> str:
    while True:
        try:
            return validator(prompts.ask_text(label, default=default))
        except ValidationError as exc:
            display.error(str(exc))


def setup_identity() -> None:
    """Nom, e-mail et réglages de fusion/branche par défaut."""
    if not git_ops.git_installed():
        raise FlowError("Git n'est pas installé. Dans Termux : pkg install git openssh")
    name, email = git_ops.get_identity()
    if name or email:
        display.info(f"Identité actuelle : {name or '?'} <{email or '?'}>")
    name = _ask_valid("Votre nom", validate_name, default=name or None)
    email = _ask_valid("Votre e-mail", validate_email, default=email or None)
    outcome = git_ops.set_identity(name, email)
    if not outcome.ok:
        raise FlowError(f"Impossible d'enregistrer l'identité : {outcome.output}")
    display.success(f"Identité enregistrée : {name} <{email}>")

    branch = storage.load_settings()["default_branch"]
    if prompts.ask_confirm(f"Régler aussi Git (fusion sans rebase, branche par défaut « {branch} ») ?"):
        outcome = git_ops.set_defaults(branch)
        if outcome.ok:
            display.success("Réglages Git appliqués (évite l'erreur « divergent branches »).")
        else:
            display.warning(f"Réglages non appliqués : {outcome.output}")


def _copy_to_clipboard(text: str) -> bool:
    return shell.which("termux-clipboard-set") is not None and shell.run(
        ["termux-clipboard-set"], input_text=text, timeout=10
    ).ok


def _show_public_key(key_path) -> None:
    key = ssh.public_key_text(key_path)
    display.show_key(key)
    if shell.which("termux-clipboard-set") and prompts.ask_confirm("Copier la clé dans le presse-papiers ?"):
        if _copy_to_clipboard(key):
            display.success("Clé copiée.")
        else:
            display.warning("Copie impossible (Termux:API installé ?). Copiez le texte à la main.")
    display.info("Sur GitHub : Settings → SSH and GPG keys → New SSH key, puis collez la clé.")
    if prompts.ask_confirm("Ouvrir la page GitHub correspondante ?"):
        if not github.open_url(SSH_KEYS_URL):
            display.warning(f"Ouverture impossible. Adresse : {SSH_KEYS_URL}")
    prompts.wait_enter("Appuyez sur Entrée quand la clé est ajoutée sur GitHub…")


def _ensure_host_trusted() -> None:
    if ssh.known_host():
        return
    display.info("Première connexion à GitHub : SSH va demander de confirmer le serveur.")
    display.dim("Répondez « yes » (empreintes officielles : docs.github.com → « GitHub's SSH key fingerprints »).")
    ssh.trust_host_interactively()


def setup_ssh() -> bool:
    """Crée la clé si besoin, guide son ajout sur GitHub et teste la connexion."""
    for tool in ("ssh", "ssh-keygen"):
        if not shell.which(tool):
            raise FlowError("OpenSSH est absent. Dans Termux : pkg install openssh")

    keys = ssh.find_public_keys()
    if keys:
        key_path = keys[0]
        display.info(f"Clé SSH trouvée : {key_path}")
    else:
        display.warning("Aucune clé SSH trouvée.")
        if not prompts.ask_confirm("Créer une clé ed25519 maintenant ?"):
            raise Cancelled()
        email = git_ops.get_identity()[1] or _ask_valid("Votre e-mail", validate_email)
        try:
            key_path = ssh.generate_key(email)
        except ssh.SshError as exc:
            raise FlowError(str(exc)) from exc
        display.success(f"Clé créée : {key_path}")
        display.dim("Sans phrase secrète : pratique sur mobile, mais gardez votre téléphone verrouillé.")

    if prompts.ask_confirm("Afficher la clé publique pour l'ajouter à GitHub ?", default=not keys):
        _show_public_key(key_path)

    _ensure_host_trusted()
    for attempt in range(1, MAX_SSH_RETRIES + 1):
        display.info("Test de la connexion à GitHub…")
        result = ssh.test_github()
        if result.status == "ok":
            settings = storage.load_settings()
            settings["github_username"] = result.username or settings["github_username"]
            storage.save_settings(settings)
            display.success(f"Connecté à GitHub en tant que {result.username}.")
            return True
        messages = {
            "denied": "GitHub ne reconnaît pas cette clé : est-elle ajoutée sur le bon compte ?",
            "hostkey": "L'empreinte du serveur n'est pas validée.",
            "network": "Pas de connexion à Internet.",
        }
        display.error(messages.get(result.status, "Réponse inattendue de GitHub."))
        display.dim(result.detail[-300:])
        if attempt == MAX_SSH_RETRIES or not prompts.ask_confirm("Réessayer le test ?"):
            return False
        if result.status == "hostkey":
            _ensure_host_trusted()
    return False


def wizard() -> None:
    """Assistant de premier lancement : identité puis SSH."""
    display.step(1, 2, "Identité Git")
    setup_identity()
    display.step(2, 2, "Connexion SSH à GitHub")
    if setup_ssh():
        display.success("Tout est prêt : vous pouvez publier un projet.")
    else:
        display.warning("SSH n'est pas encore opérationnel. Relancez l'assistant après correction.")
