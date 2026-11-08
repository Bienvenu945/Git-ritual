"""Entry script for PyInstaller (it needs a plain script, not a package module)."""

import sys

from git_ritual.cli import main

if __name__ == "__main__":
    sys.exit(main())
