"""Validation des saisies utilisateur."""

from __future__ import annotations

import re

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_USERNAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_REPO = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
_BRANCH = re.compile(r"^[A-Za-z0-9._/-]+$")


class ValidationError(ValueError):
    """Levée lorsqu'une saisie est invalide."""


def validate_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValidationError("Le nom ne peut pas être vide.")
    return value


def validate_email(value: str) -> str:
    value = value.strip()
    if not _EMAIL.match(value):
        raise ValidationError("Adresse e-mail invalide (ex. nom@exemple.com).")
    return value


def validate_username(value: str) -> str:
    value = value.strip()
    if not _USERNAME.match(value):
        raise ValidationError(
            "Pseudo GitHub invalide : lettres, chiffres et tirets uniquement (39 caractères max)."
        )
    return value


def validate_repo_name(value: str) -> str:
    value = value.strip()
    if value in {".", ".."} or not _REPO.match(value):
        raise ValidationError(
            "Nom de dépôt invalide : lettres, chiffres, « . », « - » et « _ » uniquement."
        )
    return value


def validate_branch(value: str) -> str:
    value = value.strip()
    bad = (
        not value
        or not _BRANCH.match(value)
        or ".." in value
        or "//" in value
        or value[0] in "-/."
        or value[-1] in "/."
        or value.endswith(".lock")
    )
    if bad:
        raise ValidationError("Nom de branche invalide (ex. main, dev, feature/login).")
    return value


def validate_commit_message(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValidationError("Le message du commit ne peut pas être vide.")
    return value
