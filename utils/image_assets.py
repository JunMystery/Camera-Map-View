"""Helpers for importing lightweight PNG assets onto the map canvas."""

import shutil
import uuid
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage


def import_png_asset(source_path: str, target_dir: str | Path = "assets/maps") -> tuple[str, int, int] | None:
    """Copy a PNG into assets/maps and downscale large images."""
    source = Path(source_path)
    if source.suffix.lower() != ".png" or not source.exists():
        return None

    target_root = Path(target_dir)
    target_root.mkdir(parents=True, exist_ok=True)
    target = target_root / f"inserted_{uuid.uuid4().hex}.png"

    image = QImage(str(source))
    if image.isNull():
        return None

    max_edge = 1200
    if image.width() > max_edge or image.height() > max_edge:
        image = image.scaled(max_edge, max_edge, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        image.save(str(target), "PNG", 85)
    else:
        shutil.copy2(source, target)

    return str(target), image.width(), image.height()
