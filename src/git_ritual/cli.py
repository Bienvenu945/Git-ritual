"""Git-Ritual — publier un projet sur GitHub sans les galères : point d'entrée."""

from __future__ import annotations

import sys

from git_ritual import __version__

HELP = """Git-Ritual {version} — publier un projet sur GitHub sans les galères.

Usage : ritual            lance le menu interactif
        ritual --version  affiche la version
        ritual --help     affiche cette aide
"""


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    # These two flags must work even if "rich" is missing (packaging smoke tests).
    if args and args[0] in ("-V", "--version"):
        print(f"git-ritual {__version__}")
        return 0
    if args and args[0] in ("-h", "--help"):
        print(HELP.format(version=__version__))
        return 0
    try:
        from git_ritual.interface import menus
    except ModuleNotFoundError as exc:
        if (exc.name or "").split(".")[0] == "rich":
            print("Le module « rich » est requis : pip install rich", file=sys.stderr)
            return 1
        raise
    _configure_stdio()
    try:
        menus.run()
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
