"""Exceptions de contrôle de flux des parcours interactifs."""


class Cancelled(Exception):
    """L'utilisateur a abandonné le parcours."""


class FlowError(Exception):
    """Problème bloquant, à afficher tel quel à l'utilisateur."""
