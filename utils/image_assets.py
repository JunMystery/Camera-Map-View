"""Helpers for importing lightweight image assets into project storage."""

import shutil
import uuid
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QImageReader

from utils.app_paths import resolve_app_path

IMAGE_MAX_HEIGHT = 1440
CAMERA_PHOTO_MAX_EDGE = IMAGE_MAX_HEIGHT
CAMERA_PHOTO_JPEG_QUALITY = 75
IMAGE_ASSET_QUALITY = 85
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def load_supported_image(source_path: str) -> QImage | None:
    """Load an image with Qt auto-transform handling."""
    source = resolve_app_path(source_path)
    if not source.exists() or not source.is_file():
        return None
    reader = QImageReader(str(source))
    reader.setAutoTransform(True)
    image = reader.read()
    return None if image.isNull() else image


def resize_to_max_height(image: QImage, max_height: int = IMAGE_MAX_HEIGHT) -> QImage:
    """Return a copy scaled down to max height while preserving aspect ratio."""
    if image.height() <= max_height:
        return image
    return image.scaledToHeight(max_height, Qt.TransformationMode.SmoothTransformation)


def import_image_asset(
    source_path: str,
    target_dir: str | Path = "assets/maps",
    prefix: str = "inserted",
) -> tuple[str, int, int] | None:
    """Copy or downscale a supported image into an asset directory."""
    source = resolve_app_path(source_path)
    image = load_supported_image(source_path)
    if image is None:
        return None
    target_root = resolve_app_path(target_dir)
    target_root.mkdir(parents=True, exist_ok=True)
    source_suffix = source.suffix.lower()
    suffix = source_suffix if source_suffix in SUPPORTED_IMAGE_EXTENSIONS else ".png"
    target = target_root / f"{prefix}_{uuid.uuid4().hex}{suffix}"

    resized = resize_to_max_height(image)
    if resized.size() == image.size() and source_suffix in SUPPORTED_IMAGE_EXTENSIONS:
        shutil.copy2(source, target)
        return str(target), image.width(), image.height()

    if _save_image(resized, target, suffix):
        return str(target), resized.width(), resized.height()
    fallback = target.with_suffix(".png")
    if _save_image(resized, fallback, ".png"):
        return str(fallback), resized.width(), resized.height()
    return None


def import_background_map_image(source_path: str, target_dir: str | Path = "assets/maps") -> tuple[str, int, int] | None:
    """Import a background map image with the shared height cap."""
    return import_image_asset(source_path, target_dir, "background")


def import_png_asset(source_path: str, target_dir: str | Path = "assets/maps") -> tuple[str, int, int] | None:
    """Backward-compatible alias for image annotation imports."""
    return import_image_asset(source_path, target_dir, "inserted")


def _save_image(image: QImage, target: Path, suffix: str) -> bool:
    image_format = "JPG" if suffix in {".jpg", ".jpeg"} else suffix.lstrip(".").upper()
    quality = IMAGE_ASSET_QUALITY if image_format in {"JPG", "JPEG", "WEBP"} else -1
    return image.save(str(target), image_format, quality)


def is_supported_image(source_path: str) -> bool:
    """Return whether Qt can decode the selected image file."""
    source = resolve_app_path(source_path)
    if not source.exists() or not source.is_file():
        return False
    reader = QImageReader(str(source))
    return reader.canRead()


def import_camera_location_image(
    source_path: str,
    target_dir: str | Path = "assets/camera_photos",
) -> tuple[str, int, int] | None:
    """Compress a camera location photo to a bounded JPG asset."""
    image = load_supported_image(source_path)
    if image is None:
        return None

    image = resize_to_max_height(image, CAMERA_PHOTO_MAX_EDGE)

    target_root = resolve_app_path(target_dir)
    target_root.mkdir(parents=True, exist_ok=True)
    target = target_root / f"camera_photo_{uuid.uuid4().hex}.jpg"
    if not image.convertToFormat(QImage.Format.Format_RGB888).save(str(target), "JPG", CAMERA_PHOTO_JPEG_QUALITY):
        return None
    return str(target), image.width(), image.height()
