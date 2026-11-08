"""Environnement Git isolé pour les tests (HOME et config globale temporaires)."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from git_ritual.core import git_ops


def run_git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


class GitCase(unittest.TestCase):
    """Fournit un HOME temporaire, une identité Git et un dossier de travail."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        patcher = mock.patch.dict(os.environ, {
            "HOME": str(self.home),
            "USERPROFILE": str(self.home),  # Windows: Path.home() ignores HOME
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": str(self.home / ".gitconfig"),
            "GIT_RITUAL_HOME": str(self.home / ".git-ritual"),
        })
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)
        git_ops.set_identity("Test User", "test@example.com")
        git_ops.set_defaults("main")

    def make_bare_remote(self, name="remote.git") -> Path:
        path = self.root / name
        run_git(self.root, "init", "--bare", "-b", "main", str(path))
        return path

    def make_project(self, name="proj", files=None) -> git_ops.Repo:
        path = self.root / name
        path.mkdir()
        for filename, content in (files or {"a.txt": "hello\n"}).items():
            (path / filename).parent.mkdir(parents=True, exist_ok=True)
            (path / filename).write_text(content)
        return git_ops.Repo(path)
