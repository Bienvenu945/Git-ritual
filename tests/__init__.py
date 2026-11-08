"""Tests run from a plain checkout (`python -m unittest`) or against an installed package."""

import sys
from pathlib import Path

try:
    import git_ritual  # noqa: F401  (already installed, e.g. `pip install -e .` or CI)
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
