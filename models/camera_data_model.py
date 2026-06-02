"""Camera data model and serialization helpers."""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass
class Camera:
    """Represent a camera and its placement metadata on the map."""

    id: str
    name: str
    ip_address: str
    port: int = 554
    camera_type: str = "Fixed"
    position_x: float = 0.0
    position_y: float = 0.0
    rotation: float = 0.0
    display_scale: float = 1.0
    status: bool = False
    last_check: datetime | None = None
    notes: str = ""
    zone: str = ""
    dvr_origin: str = ""
    layer_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert the camera to a serializable dictionary."""
        data = asdict(self)
        if self.last_check:
            data["last_check"] = self.last_check.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Camera":
        """Create a camera model from a dictionary."""
        data_copy = data.copy()
        last_check = data_copy.get("last_check")
        if last_check and isinstance(last_check, str):
            data_copy["last_check"] = datetime.fromisoformat(last_check)
        return cls(**data_copy)
