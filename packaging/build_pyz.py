#!/usr/bin/env python3
"""Build dist/ritual.pyz: ONE file, runs on any OS that has Python >= 3.9.

Every dependency (rich, markdown-it-py, mdurl, pygments) is pure Python, so the same
archive works on Termux, Linux, macOS and Windows:  python ritual.pyz
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = "import sys\nfrom git_ritual.cli import main\n\nsys.exit(main())\n"


def build(output: Path) -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "app"
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "--no-compile",
             "--target", str(target), str(ROOT)],
            check=True,
        )
        shutil.rmtree(target / "bin", ignore_errors=True)  # console scripts are useless here
        (target / "__main__.py").write_text(MAIN, encoding="utf-8")
        output.parent.mkdir(parents=True, exist_ok=True)
        # No "interpreter" shebang: users run `python ritual.pyz` (works everywhere, Termux included).
        zipapp.create_archive(target, output, compressed=True)
    return output


def main() -> int:
    out = build(ROOT / "dist" / "ritual.pyz")
    check = subprocess.run([sys.executable, str(out), "--version"], capture_output=True, text=True)
    if check.returncode != 0 or "git-ritual" not in check.stdout:
        print(check.stdout + check.stderr, file=sys.stderr)
        return 1
    print(f"{out} ({out.stat().st_size // 1024} KiB) -> {check.stdout.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
