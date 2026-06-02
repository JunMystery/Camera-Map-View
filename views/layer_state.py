"""Layer identifiers and lightweight state records for the map canvas."""

from dataclasses import dataclass


BACKGROUND_LAYER = "background"
GRID_LAYER = "grid"


@dataclass
class LayerState:
    """Represent one visible layer row in the layer manager panel."""

    layer_id: str
    display_name: str
    visible: bool
    locked: bool
    item_count: int
    active: bool = False


@dataclass
class LayerObjectState:
    """Represent one canvas object nested under a layer row."""

    object_id: str
    layer_id: str
    label: str
    object_type: str
    visible: bool
    locked: bool
    z_index: int = 0
