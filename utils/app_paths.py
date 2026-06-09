"""Resolve application-relative paths consistently in source and frozen builds."""

import sys
from pathlib import Path


def app_base_dir() -> Path:
    """Return the directory that owns application assets."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def resolve_app_path(path: str | Path) -> Path:
    """Resolve a relative path against the application base directory."""
    value = Path(path)
    return value if value.is_absolute() else app_base_dir() / value
