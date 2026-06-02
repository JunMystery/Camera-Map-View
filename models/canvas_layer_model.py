"""Persistent canvas layer metadata for Photoshop-like layer management."""

from dataclasses import dataclass


DEFAULT_LAYER_NAMES = {
    "cameras": "Cameras",
    "drawings": "Drawings",
    "images": "Images",
    "text": "Text",
}


@dataclass
class CanvasLayer:
    """Represent a user-manageable layer inside one map layout."""

    id: str
    layout_id: str
    name: str
    position: int
    visible: bool = True
    locked: bool = False
