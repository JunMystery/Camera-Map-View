"""Helpers for importing lightweight image assets into project storage."""

import shutil
import uuid
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QImageReader

CAMERA_PHOTO_MAX_EDGE = 1600
CAMERA_PHOTO_JPEG_QUALITY = 75


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


def is_supported_image(source_path: str) -> bool:
    """Return whether Qt can decode the selected image file."""
    source = Path(source_path)
    if not source.exists() or not source.is_file():
        return False
    reader = QImageReader(str(source))
    return reader.canRead()


def import_camera_location_image(
    source_path: str,
    target_dir: str | Path = "assets/camera_photos",
) -> tuple[str, int, int] | None:
    """Compress a camera location photo to a bounded JPG asset."""
    source = Path(source_path)
    if not source.exists() or not source.is_file():
        return None

    reader = QImageReader(str(source))
    reader.setAutoTransform(True)
    image = reader.read()
    if image.isNull():
        return None

    if image.width() > CAMERA_PHOTO_MAX_EDGE or image.height() > CAMERA_PHOTO_MAX_EDGE:
        image = image.scaled(
            CAMERA_PHOTO_MAX_EDGE,
            CAMERA_PHOTO_MAX_EDGE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    target_root = Path(target_dir)
    target_root.mkdir(parents=True, exist_ok=True)
    target = target_root / f"camera_photo_{uuid.uuid4().hex}.jpg"
    if not image.convertToFormat(QImage.Format.Format_RGB888).save(str(target), "JPG", CAMERA_PHOTO_JPEG_QUALITY):
        return None
    return str(target), image.width(), image.height()
