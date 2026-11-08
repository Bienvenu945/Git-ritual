"""Allow `python -m git_ritual`."""

import sys

from git_ritual.cli import main

if __name__ == "__main__":
    sys.exit(main())
