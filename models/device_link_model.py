"""Device link model for upstream topology connections."""

from dataclasses import dataclass


@dataclass
class DeviceLink:
    """Represent a directed device connection on one layout."""

    id: str
    layout_id: str
    source_device_id: str
    target_device_id: str
