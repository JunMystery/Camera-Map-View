"""Persist application-level settings outside layout-specific SQLite data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

APP_SETTINGS_PATH = Path("assets/data/app_settings.json")

DEFAULT_SETTINGS: dict[str, object] = {
    "ping_interval": 30,
    "ping_timeout": 1.0,
    "ping_retries": 1,
    "canvas_width": 4000,
    "canvas_height": 3000,
    "grid_size": 20,
    "background_scale": 1.0,
    "light_theme": False,
}


def load_app_settings(path: str | Path = APP_SETTINGS_PATH) -> dict[str, object]:
    """Load settings from JSON and merge them with defaults."""
    settings = DEFAULT_SETTINGS.copy()
    source = Path(path)
    if not source.exists():
        return settings
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return settings
    if not isinstance(data, dict):
        return settings
    for key, default_value in DEFAULT_SETTINGS.items():
        if key in data:
            settings[key] = _coerce_value(data[key], default_value)
    return settings


def save_app_settings(settings: dict[str, object], path: str | Path = APP_SETTINGS_PATH) -> None:
    """Write known application settings to JSON."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        key: _coerce_value(settings.get(key, default_value), default_value)
        for key, default_value in DEFAULT_SETTINGS.items()
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _coerce_value(value: Any, default_value: object) -> object:
    if isinstance(default_value, bool):
        return bool(value)
    if isinstance(default_value, int):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default_value
    if isinstance(default_value, float):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default_value
    return value
