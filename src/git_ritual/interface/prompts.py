"""Saisies interactives : choix, texte, confirmations, pauses."""

from __future__ import annotations

from typing import Sequence

from rich.prompt import Confirm, Prompt
from rich.text import Text

from git_ritual.interface import display
from git_ritual.interface.display import console


def ask_choice(label: str, choices: Sequence[str], default: str | None = None) -> str:
    return Prompt.ask(
        f"[bold {display.accent()}]{label}[/]",
        console=console,
        choices=list(choices),
        default=default,
        show_choices=False,
    )


def ask_text(label: str, default: str | None = None) -> str:
    kwargs = {} if default is None else {"default": default, "show_default": bool(default)}
    return Prompt.ask(f"[bold {display.accent()}]{label}[/]", console=console, **kwargs)


def ask_confirm(label: str, default: bool = True) -> bool:
    return Confirm.ask(f"[bold {display.accent()}]{label}[/]", console=console, default=default)


def choose(title: str, options: Sequence[tuple[str, str]], default: str | None = None) -> str:
    """Affiche un petit menu et retourne la touche choisie."""
    display.show_menu(title, options)
    return ask_choice("Votre choix", [key for key, _ in options], default=default)


def wait_enter(message: str) -> None:
    console.input(Text(f"\n{message}", style="dim"))


def pause() -> None:
    try:
        wait_enter("Appuyez sur Entrée pour continuer…")
    except (EOFError, KeyboardInterrupt):
        console.print()
