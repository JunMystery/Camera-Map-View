"""Persistent canvas layer metadata for Photoshop-like layer management."""

from dataclasses import dataclass


@dataclass
class CanvasLayer:
    """Represent a user-manageable layer inside one map layout."""

    id: str
    layout_id: str
    name: str
    position: int
    visible: bool = True
    locked: bool = False
    group_id: str = ""
    is_group: bool = False
