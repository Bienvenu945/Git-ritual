"""Affichage : bannière, menus, panneaux, tableaux et messages."""

from __future__ import annotations

from typing import Iterable, Sequence

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from git_ritual.core.diagnostics import ErrorKind, explain
from git_ritual.core.git_ops import Change

console = Console()
_accent = "cyan"

_CODE_LABELS = {"?": "nouveau", "M": "modifié", "A": "ajouté", "D": "supprimé", "R": "renommé", "C": "copié", "U": "conflit"}


def set_accent(color: str) -> None:
    global _accent
    _accent = color


def accent() -> str:
    return _accent


# --------------------------------------------------------------------------- #
# Messages
# --------------------------------------------------------------------------- #
def _message(symbol: str, style: str, message: str) -> None:
    console.print(Text.assemble((f"{symbol} ", f"bold {style}"), message))


def success(message: str) -> None:
    _message("✔", "green", message)


def error(message: str) -> None:
    _message("✘", "red", message)


def warning(message: str) -> None:
    _message("!", "yellow", message)


def info(message: str) -> None:
    _message("•", _accent, message)


def dim(message: str) -> None:
    console.print(Text(message, style="dim"))


def explain_error(kind: ErrorKind, detail: str = "") -> None:
    """Explication en français + dernières lignes de la sortie brute de Git."""
    title, hint = explain(kind)
    error(title)
    console.print(Text(f"  → {hint}", style="yellow"))
    lines = [line for line in detail.strip().splitlines() if line.strip()]
    if lines:
        console.print(Text("  " + "\n  ".join(lines[-6:]), style="dim"))


# --------------------------------------------------------------------------- #
# Structure
# --------------------------------------------------------------------------- #
def clear() -> None:
    console.clear()


def show_banner() -> None:
    title = Text("🚀 GIT-RITUAL", style=f"bold {_accent}", justify="center")
    subtitle = Text("init • commit • push — sans les galères", style="dim", justify="center")
    console.print(Panel(Group(title, subtitle), box=box.DOUBLE, border_style=_accent, padding=(0, 2)))


def show_menu(title: str, options: Sequence[tuple[str, str]]) -> None:
    table = Table(box=box.ROUNDED, border_style=_accent, show_header=False, title=title,
                  title_style=f"bold {_accent}")
    table.add_column("Touche", style=f"bold {_accent}", justify="right", no_wrap=True)
    table.add_column("Action", overflow="fold")
    for key, label in options:
        table.add_row(Text(key), Text(label))
    console.print(table)


def step(index: int, total: int, title: str) -> None:
    console.print()
    console.print(Text(f"[{index}/{total}] {title}", style=f"bold {_accent}"))


def show_panel(title: str, content: str, style: str | None = None) -> None:
    console.print(Panel(Text(content), title=title, title_align="left", border_style=style or _accent))


def show_key(public_key: str) -> None:
    show_panel("Votre clé publique (à coller dans GitHub)", public_key)


def show_summary(title: str, rows: Iterable[tuple[str, str]]) -> None:
    table = Table(box=box.SIMPLE_HEAD, show_header=False, title=title, title_style=f"bold {_accent}")
    table.add_column("Clé", style=f"bold {_accent}", no_wrap=True)
    table.add_column("Valeur", overflow="fold")
    for key, value in rows:
        table.add_row(Text(key), Text(value))
    console.print(table)


def show_health(items: Sequence[tuple[str, bool, str]]) -> None:
    lines = []
    for label, ok, detail in items:
        symbol, style = ("✔", "green") if ok else ("✘", "red")
        lines.append(Text.assemble((f"{symbol} ", f"bold {style}"), f"{label}", (f"  {detail}" if detail else "", "dim")))
    console.print(Panel(Group(*lines), title="Diagnostic rapide", title_align="left", border_style="dim"))


def show_changes(changes: Sequence[Change], limit: int = 12) -> None:
    table = Table(box=box.SIMPLE_HEAD, header_style=f"bold {_accent}",
                  title=f"{len(changes)} fichier(s) à valider", title_style=f"bold {_accent}")
    table.add_column("État", no_wrap=True)
    table.add_column("Fichier", overflow="fold")
    for change in changes[:limit]:
        symbol = (change.code.strip() or " ")[0]
        table.add_row(Text(_CODE_LABELS.get(symbol, change.code.strip())), Text(change.path))
    if len(changes) > limit:
        table.add_row(Text("…"), Text(f"et {len(changes) - limit} autre(s)"))
    console.print(table)


def show_commits(lines: Sequence[str]) -> None:
    if lines:
        console.print(Text("Derniers commits :", style=f"bold {_accent}"))
        for line in lines:
            console.print(Text("  " + line, style="dim"))
