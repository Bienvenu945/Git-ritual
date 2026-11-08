#!/usr/bin/env python3
"""Run Git-Ritual straight from a checkout, a zip or a USB stick (no install needed).

Only the `rich` package is required: pip install rich
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from git_ritual.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
