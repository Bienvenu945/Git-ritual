"""Exécution de commandes externes, de façon sûre (sans shell) et prévisible."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


class ToolMissingError(Exception):
    """L'outil demandé n'est pas installé."""

    def __init__(self, tool: str):
        super().__init__(tool)
        self.tool = tool


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def output(self) -> str:
        """Sortie combinée (stderr d'abord : c'est là que git écrit ses messages)."""
        return "\n".join(p for p in (self.stderr.strip(), self.stdout.strip()) if p)


def which(tool: str) -> str | None:
    return shutil.which(tool)


def _env(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["LC_ALL"] = "C"           # messages en anglais : classification fiable
    env["LANGUAGE"] = "C"
    env["GIT_TERMINAL_PROMPT"] = "0"  # jamais de demande de mot de passe HTTPS
    if extra:
        env.update(extra)
    return env


def run(
    args: Sequence[str],
    cwd: str | Path | None = None,
    timeout: int = 60,
    input_text: str | None = None,
    env: Mapping[str, str] | None = None,
) -> CommandResult:
    """Exécute une commande et capture sa sortie. Ne lève pas sur code d'erreur."""
    command = tuple(str(a) for a in args)
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            input=input_text,
            stdin=None if input_text is not None else subprocess.DEVNULL,
            env=_env(env),
        )
    except FileNotFoundError:
        raise ToolMissingError(command[0]) from None
    except subprocess.TimeoutExpired:
        return CommandResult(command, 124, "", f"Délai dépassé ({timeout} s) : {command[0]}")
    return CommandResult(command, proc.returncode, proc.stdout, proc.stderr)


def run_interactive(args: Sequence[str], cwd: str | Path | None = None) -> int:
    """Exécute une commande en lui laissant le terminal (questions oui/non, etc.)."""
    command = tuple(str(a) for a in args)
    try:
        return subprocess.run(command, cwd=cwd).returncode
    except FileNotFoundError:
        raise ToolMissingError(command[0]) from None
