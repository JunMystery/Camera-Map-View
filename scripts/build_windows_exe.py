"""Build the Windows EXE package for Camera Map View with PyInstaller.

This script intentionally does not install dependencies. Install PyInstaller
manually when needed:

    python -m pip install pyinstaller
"""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

APP_NAME = "CameraMapView"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = PROJECT_ROOT / "bin"
BUILD_DIR = PROJECT_ROOT / "build" / "pyinstaller"
WORK_DIR = BUILD_DIR / "work"
SPEC_DIR = BUILD_DIR


def build_command() -> list[str]:
    """Return the PyInstaller command used for the Windows package."""
    add_data_separator = os.pathsep
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(WORK_DIR),
        "--specpath",
        str(SPEC_DIR),
        "--add-data",
        f"{PROJECT_ROOT / 'assets'}{add_data_separator}assets",
        "--add-data",
        f"{PROJECT_ROOT / 'config'}{add_data_separator}config",
        "--hidden-import",
        "PyQt6.QtSvg",
        "--hidden-import",
        "PyQt6.QtPrintSupport",
        "--hidden-import",
        "PIL",
        "--hidden-import",
        "cv2",
        "--hidden-import",
        "ping3",
        "--hidden-import",
        "aiohttp",
        str(PROJECT_ROOT / "main.py"),
    ]


def main(argv: list[str] | None = None) -> int:
    """Run PyInstaller unless dry-run is requested."""
    parser = argparse.ArgumentParser(description="Build Camera Map View Windows EXE package.")
    parser.add_argument("--dry-run", action="store_true", help="Print the PyInstaller command without running it.")
    args = parser.parse_args(argv)

    command = build_command()
    if args.dry_run:
        print(subprocess.list2cmdline(command))
        return 0

    if importlib.util.find_spec("PyInstaller") is None:
        print("PyInstaller is not installed. Run: python -m pip install pyinstaller", file=sys.stderr)
        return 1

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    return subprocess.call(command, cwd=PROJECT_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
