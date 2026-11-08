#!/usr/bin/env python3
"""Build a standalone binary with PyInstaller (OPTIONAL, never used on Termux).

    pip install ".[bin]" && python packaging/build_binary.py

Output (in dist/bin/), named after the build machine:
  - Linux / macOS : ritual-<os>-<arch>          (one file)
  - Windows       : ritual-windows-<arch>.zip   (one folder, zipped)
Windows uses --onedir on purpose: --onefile self-extracting executables are the pattern
antivirus engines flag most often.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCH = {"amd64": "x86_64", "x86_64": "x86_64", "arm64": "arm64", "aarch64": "arm64"}


def target_name() -> tuple[str, str]:
    system = {"Linux": "linux", "Darwin": "macos", "Windows": "windows"}.get(platform.system())
    arch = ARCH.get(platform.machine().lower())
    if not system or not arch:
        raise SystemExit(f"Unsupported build machine: {platform.system()} {platform.machine()}")
    return system, arch


def main() -> int:
    system, arch = target_name()
    onedir = system == "windows"
    work, dist = ROOT / "build" / "pyinstaller", ROOT / "dist" / "bin"
    shutil.rmtree(work, ignore_errors=True)
    dist.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--name", "ritual", "--onedir" if onedir else "--onefile",
        "--paths", str(ROOT / "src"),
        "--collect-submodules", "git_ritual", "--collect-submodules", "rich",
        "--distpath", str(work / "out"), "--workpath", str(work / "tmp"),
        "--specpath", str(work),
        str(ROOT / "packaging" / "pyinstaller_entry.py"),
    ]
    subprocess.run(command, check=True)

    exe_name = "ritual.exe" if system == "windows" else "ritual"
    built = work / "out" / ("ritual" if onedir else exe_name)
    exe = built / exe_name if onedir else built

    smoke = subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=120)
    if smoke.returncode != 0 or "git-ritual" not in smoke.stdout:
        print(smoke.stdout + smoke.stderr, file=sys.stderr)
        return 1

    base = f"ritual-{system}-{arch}"
    if onedir:
        archive = dist / f"{base}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(built.rglob("*")):
                zf.write(path, Path("ritual") / path.relative_to(built))
        print(f"{archive} -> {smoke.stdout.strip()}")
    else:
        final = dist / base
        shutil.copy2(exe, final)
        final.chmod(0o755)
        print(f"{final} -> {smoke.stdout.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
