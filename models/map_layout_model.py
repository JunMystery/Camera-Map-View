"""Map layout model for multi-map workspace management."""

from dataclasses import dataclass


@dataclass
class MapLayout:
    """Represent one independent canvas/map layout."""

    id: str
    name: str
    background_path: str = ""
    grid_size: int = 20
    canvas_width: int = 4000
    canvas_height: int = 3000
    background_scale: float = 1.0
    background_x: float = 0.0
    background_y: float = 0.0
