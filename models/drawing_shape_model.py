"""Drawing shape model for map annotations."""

from dataclasses import dataclass


@dataclass
class DrawingShape:
    """Represent a persisted geometric annotation on the map."""

    id: str
    shape_type: str
    points: list[float]
    color: str = "#ef4444"
    line_thickness: int = 2
    label: str = ""
    image_path: str = ""
