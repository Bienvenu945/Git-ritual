"""Reconnaissance des erreurs Git / SSH courantes et explications en français."""

from __future__ import annotations

import re
from enum import Enum


class ErrorKind(Enum):
    NONE = "none"
    NOT_FOUND = "not_found"
    AUTH_SSH = "auth_ssh"
    AUTH_HTTPS = "auth_https"
    HOSTKEY = "hostkey"
    NETWORK = "network"
    REJECTED = "rejected"
    DIVERGENT = "divergent"
    UNRELATED = "unrelated"
    CONFLICT = "conflict"
    NO_COMMITS = "no_commits"
    NO_IDENTITY = "no_identity"
    NOTHING_TO_COMMIT = "nothing_to_commit"
    OTHER = "other"


# Ordre important : le premier motif reconnu l'emporte.
_PATTERNS: tuple[tuple[ErrorKind, str], ...] = (
    (ErrorKind.HOSTKEY, r"Host key verification failed"),
    (ErrorKind.AUTH_SSH, r"Permission denied \(publickey"),
    (ErrorKind.AUTH_HTTPS, r"Authentication failed|Invalid username or token|Password authentication is not supported|could not read Username"),
    (ErrorKind.NOT_FOUND, r"Repository not found|repository '.*' not found|does not appear to be a git repository|remote: Not Found"),
    (ErrorKind.NETWORK, r"Could not resolve host|Network is unreachable|Connection timed out|Operation timed out|Connection refused|Temporary failure in name resolution|Délai dépassé|kex_exchange_identification|Connection closed by|Could not resolve hostname"),
    (ErrorKind.UNRELATED, r"refusing to merge unrelated histories"),
    (ErrorKind.DIVERGENT, r"Need to specify how to reconcile divergent branches"),
    (ErrorKind.CONFLICT, r"CONFLICT \(|Automatic merge failed"),
    (ErrorKind.NO_COMMITS, r"src refspec .* does not match any|does not have any commits yet"),
    (ErrorKind.REJECTED, r"\[rejected\]|failed to push some refs|non-fast-forward|\(fetch first\)"),
    (ErrorKind.NO_IDENTITY, r"Please tell me who you are|unable to auto-detect email address|empty ident name"),
    (ErrorKind.NOTHING_TO_COMMIT, r"nothing to commit|nothing added to commit|no changes added to commit"),
)
_COMPILED = tuple((kind, re.compile(pattern, re.IGNORECASE)) for kind, pattern in _PATTERNS)

_EXPLANATIONS: dict[ErrorKind, tuple[str, str]] = {
    ErrorKind.NOT_FOUND: (
        "Dépôt introuvable à cette adresse.",
        "Soit il n'existe pas encore, soit le nom diffère (majuscules, « - » ou « _ »). "
        "Le plus sûr : copier l'adresse depuis GitHub (bouton Code → SSH).",
    ),
    ErrorKind.AUTH_SSH: (
        "GitHub refuse votre clé SSH.",
        "La clé publique n'est pas dans GitHub (Settings → SSH and GPG keys), "
        "ou elle est sur un autre compte. L'assistant de configuration vous guide.",
    ),
    ErrorKind.AUTH_HTTPS: (
        "Authentification HTTPS refusée.",
        "GitHub n'accepte plus les mots de passe. Utilisez une adresse SSH (git@github.com:…).",
    ),
    ErrorKind.HOSTKEY: (
        "L'empreinte du serveur n'a pas été validée.",
        "Lancez l'assistant SSH pour confirmer github.com une première fois.",
    ),
    ErrorKind.NETWORK: (
        "Impossible de joindre le serveur.",
        "Vérifiez le Wi-Fi ou les données mobiles, puis réessayez.",
    ),
    ErrorKind.REJECTED: (
        "Le dépôt distant contient des fichiers absents de votre dossier.",
        "Souvent un README ou une licence créés par GitHub. Il faut les fusionner avant d'envoyer.",
    ),
    ErrorKind.DIVERGENT: (
        "Les historiques local et distant ont divergé.",
        "Une fusion est nécessaire pour les réconcilier.",
    ),
    ErrorKind.UNRELATED: (
        "Les deux historiques n'ont aucun ancêtre commun.",
        "Normal quand GitHub a créé un premier commit : la fusion doit être explicitement autorisée.",
    ),
    ErrorKind.CONFLICT: (
        "Conflit de fusion : un même fichier existe des deux côtés avec un contenu différent.",
        "Choisissez quelle version garder.",
    ),
    ErrorKind.NO_COMMITS: (
        "Il n'y a encore aucun commit à envoyer.",
        "Ajoutez des fichiers et validez-les d'abord.",
    ),
    ErrorKind.NO_IDENTITY: (
        "Git ne connaît pas votre identité.",
        "Renseignez votre nom et votre e-mail dans l'assistant de configuration.",
    ),
    ErrorKind.NOTHING_TO_COMMIT: (
        "Aucune modification à valider.",
        "Le dossier est déjà à jour.",
    ),
    ErrorKind.OTHER: (
        "L'opération a échoué.",
        "Détail de Git ci-dessous.",
    ),
}


def classify(text: str) -> ErrorKind:
    """Devine la nature d'une erreur à partir du message de Git ou d'SSH."""
    for kind, pattern in _COMPILED:
        if pattern.search(text):
            return kind
    return ErrorKind.OTHER


def explain(kind: ErrorKind) -> tuple[str, str]:
    """Retourne (titre, conseil) en français."""
    return _EXPLANATIONS.get(kind, _EXPLANATIONS[ErrorKind.OTHER])
