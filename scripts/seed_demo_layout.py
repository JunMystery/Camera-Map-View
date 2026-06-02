"""Seed an idempotent multi-floor demo layout for Camera Map View."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from controllers.camera_data_manager import CameraDataManager
from models.camera_data_model import Camera
from models.device_catalog import (
    DEVICE_KIND_AP,
    DEVICE_KIND_CAMERA,
    DEVICE_KIND_DVR,
    DEVICE_KIND_FIREWALL,
    DEVICE_KIND_PC,
    DEVICE_KIND_ROUTER,
    DEVICE_KIND_SERVER,
    DEVICE_KIND_SWITCH,
)
from models.drawing_shape_model import DrawingShape
from models.map_layout_model import MapLayout

DEMO_LAYOUT_ID = "layout_demo_multifloor"
DEMO_LAYOUT_NAME = "Demo - Tòa nhà nhiều tầng"
DEFAULT_DB_PATH = Path("assets/data/camera_manager.db")


def seed_demo_layout(db_path: str | Path = DEFAULT_DB_PATH) -> str:
    """Create or refresh the demo layout and return its layout id."""
    manager = CameraDataManager(db_path)
    try:
        _reset_layout(manager)
        layer_ids = _create_layers(manager)
        for device in _demo_devices(layer_ids):
            manager.add_camera(device, is_placed=True, layout_id=DEMO_LAYOUT_ID)
        for source_id, target_id in _demo_links():
            manager.add_device_link(source_id, target_id, DEMO_LAYOUT_ID)
        for shape in _demo_drawings(layer_ids):
            manager.add_drawing_shape(shape, DEMO_LAYOUT_ID)
    finally:
        manager.db.close()
    return DEMO_LAYOUT_ID


def _reset_layout(manager: CameraDataManager) -> None:
    if manager.get_layout(DEMO_LAYOUT_ID) is not None:
        manager.delete_layout(DEMO_LAYOUT_ID)
    layout = MapLayout(
        id=DEMO_LAYOUT_ID,
        name=DEMO_LAYOUT_NAME,
        grid_size=50,
        canvas_width=4200,
        canvas_height=3000,
    )
    manager.db.execute(
        """
        INSERT INTO map_layouts (id, name, background_path, grid_size, canvas_width, canvas_height, background_scale)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            layout.id,
            layout.name,
            layout.background_path,
            layout.grid_size,
            layout.canvas_width,
            layout.canvas_height,
            layout.background_scale,
        ),
    )
    manager.ensure_default_layers(DEMO_LAYOUT_ID)


def _create_layers(manager: CameraDataManager) -> dict[str, str]:
    base_layer = manager.get_layers(DEMO_LAYOUT_ID)[0]
    manager.rename_layer(base_layer.id, "Infrastructure")
    layer_ids = {"infra": base_layer.id}
    for key, name in (("floor1", "Floor 1"), ("floor2", "Floor 2"), ("floor3", "Floor 3"), ("notes", "Notes")):
        layer_ids[key] = manager.create_layer(name, DEMO_LAYOUT_ID).id
    return layer_ids


def _demo_devices(layer_ids: dict[str, str]) -> list[Camera]:
    return [
        _device("demo_server_main", "Main Server", "", DEVICE_KIND_SERVER, "Rack", 3450, 390, layer_ids["infra"], "Server Room"),
        _device("demo_nvr_main", "NVR Storage", "", DEVICE_KIND_DVR, "NVR", 3450, 610, layer_ids["infra"], "Server Room"),
        _device("demo_firewall_edge", "Edge Firewall", "", DEVICE_KIND_FIREWALL, "NGFW", 3000, 500, layer_ids["infra"], "Server Room"),
        _device("demo_router_wan", "WAN Router", "", DEVICE_KIND_ROUTER, "Edge Router", 2700, 500, layer_ids["infra"], "Server Room"),
        _device("demo_switch_core", "Core Switch", "", DEVICE_KIND_SWITCH, "Core", 2350, 500, layer_ids["infra"], "Server Room"),
        _device("demo_sw_f1", "Floor 1 PoE Switch", "", DEVICE_KIND_SWITCH, "PoE", 1350, 760, layer_ids["floor1"], "Floor 1"),
        _device("demo_sw_f2", "Floor 2 Access Switch", "", DEVICE_KIND_SWITCH, "Access", 1350, 1660, layer_ids["floor2"], "Floor 2"),
        _device("demo_sw_f3", "Floor 3 Access Switch", "", DEVICE_KIND_SWITCH, "Access", 1350, 2560, layer_ids["floor3"], "Floor 3"),
        _device("demo_ap_f1", "Floor 1 Lobby AP", "", DEVICE_KIND_AP, "Ceiling AP", 2000, 760, layer_ids["floor1"], "Lobby"),
        _device("demo_ap_f2", "Floor 2 Office AP", "", DEVICE_KIND_AP, "Ceiling AP", 2000, 1660, layer_ids["floor2"], "Office"),
        _device("demo_ap_f3", "Floor 3 Meeting AP", "", DEVICE_KIND_AP, "Ceiling AP", 2000, 2560, layer_ids["floor3"], "Meeting"),
        _device("demo_cam_f1_entrance", "F1 Entrance Cam", "10.10.1.11", DEVICE_KIND_CAMERA, "Fixed", 420, 760, layer_ids["floor1"], "Entrance", 0),
        _device("demo_cam_f1_lobby", "F1 Lobby Cam", "10.10.1.12", DEVICE_KIND_CAMERA, "Dome", 750, 520, layer_ids["floor1"], "Lobby", 45),
        _device("demo_cam_f1_lift", "F1 Lift Cam", "10.10.1.13", DEVICE_KIND_CAMERA, "Fixed", 1030, 980, layer_ids["floor1"], "Lift", 90),
        _device("demo_cam_f2_corridor", "F2 Corridor Cam", "10.10.2.11", DEVICE_KIND_CAMERA, "Dome", 420, 1660, layer_ids["floor2"], "Corridor", 0),
        _device("demo_cam_f2_office", "F2 Office Cam", "10.10.2.12", DEVICE_KIND_CAMERA, "Fixed", 770, 1440, layer_ids["floor2"], "Office", 35),
        _device("demo_cam_f2_lift", "F2 Lift Cam", "10.10.2.13", DEVICE_KIND_CAMERA, "Fixed", 1030, 1880, layer_ids["floor2"], "Lift", 90),
        _device("demo_cam_f3_corridor", "F3 Corridor Cam", "10.10.3.11", DEVICE_KIND_CAMERA, "Dome", 420, 2560, layer_ids["floor3"], "Corridor", 0),
        _device("demo_cam_f3_meeting", "F3 Meeting Cam", "10.10.3.12", DEVICE_KIND_CAMERA, "360", 770, 2340, layer_ids["floor3"], "Meeting", 0),
        _device("demo_cam_f3_lift", "F3 Lift Cam", "10.10.3.13", DEVICE_KIND_CAMERA, "Fixed", 1030, 2780, layer_ids["floor3"], "Lift", 90),
        _device("demo_pc_reception", "Reception PC", "", DEVICE_KIND_PC, "PC", 2520, 760, layer_ids["floor1"], "Reception"),
        _device("demo_laptop_sales", "Sales Laptop", "", DEVICE_KIND_PC, "Laptop", 2520, 1660, layer_ids["floor2"], "Office"),
        _device("demo_workstation_design", "Design Workstation", "", DEVICE_KIND_PC, "Workstation", 2520, 2560, layer_ids["floor3"], "Meeting"),
    ]


def _device(
    device_id: str,
    name: str,
    ip_address: str,
    kind: str,
    variant: str,
    x: float,
    y: float,
    layer_id: str,
    zone: str,
    rotation: float = 0.0,
) -> Camera:
    ping_enabled = bool(ip_address)
    return Camera(
        id=device_id,
        name=name,
        ip_address=ip_address,
        camera_type=variant,
        position_x=x,
        position_y=y,
        rotation=rotation,
        status=ping_enabled,
        notes=f"Demo {kind} - {zone}",
        zone=zone,
        dvr_origin="Demo NVR" if kind == DEVICE_KIND_CAMERA else "",
        layer_id=layer_id,
        device_kind=kind,
        variant=variant,
        ping_enabled=ping_enabled,
    )


def _demo_links() -> list[tuple[str, str]]:
    return [
        ("demo_cam_f1_entrance", "demo_sw_f1"),
        ("demo_cam_f1_lobby", "demo_ap_f1"),
        ("demo_cam_f1_lift", "demo_sw_f1"),
        ("demo_pc_reception", "demo_sw_f1"),
        ("demo_ap_f1", "demo_sw_f1"),
        ("demo_cam_f2_corridor", "demo_sw_f2"),
        ("demo_cam_f2_office", "demo_ap_f2"),
        ("demo_cam_f2_lift", "demo_sw_f2"),
        ("demo_laptop_sales", "demo_ap_f2"),
        ("demo_ap_f2", "demo_sw_f2"),
        ("demo_cam_f3_corridor", "demo_sw_f3"),
        ("demo_cam_f3_meeting", "demo_ap_f3"),
        ("demo_cam_f3_lift", "demo_sw_f3"),
        ("demo_workstation_design", "demo_sw_f3"),
        ("demo_ap_f3", "demo_sw_f3"),
        ("demo_sw_f1", "demo_switch_core"),
        ("demo_sw_f2", "demo_switch_core"),
        ("demo_sw_f3", "demo_switch_core"),
        ("demo_switch_core", "demo_firewall_edge"),
        ("demo_firewall_edge", "demo_router_wan"),
        ("demo_router_wan", "demo_server_main"),
        ("demo_switch_core", "demo_nvr_main"),
    ]


def _demo_drawings(layer_ids: dict[str, str]) -> list[DrawingShape]:
    return [
        _rect("demo_zone_floor1", [250, 250, 3150, 1120], "#2563eb", layer_ids["floor1"], "Floor 1 boundary"),
        _rect("demo_zone_floor2", [250, 1150, 3150, 2020], "#16a34a", layer_ids["floor2"], "Floor 2 boundary"),
        _rect("demo_zone_floor3", [250, 2050, 3150, 2920], "#9333ea", layer_ids["floor3"], "Floor 3 boundary"),
        _rect("demo_zone_server_room", [3300, 250, 4050, 850], "#dc2626", layer_ids["infra"], "Server Room"),
        _text("demo_label_floor1", "Floor 1 - Entrance / Lobby", 300, 290, layer_ids["notes"]),
        _text("demo_label_floor2", "Floor 2 - Office", 300, 1190, layer_ids["notes"]),
        _text("demo_label_floor3", "Floor 3 - Meeting / Design", 300, 2090, layer_ids["notes"]),
        _text("demo_label_server_room", "Server Room", 3350, 290, layer_ids["notes"]),
        _text("demo_label_topology", "Select any device to show related topology links", 2250, 180, layer_ids["notes"]),
        DrawingShape("demo_line_backbone", "Line", [1450, 760, 2350, 500], "#0f172a", 4, layer_id=layer_ids["infra"], display_name="Backbone hint"),
        DrawingShape("demo_line_backbone_f2", "Line", [1450, 1660, 2350, 500], "#0f172a", 4, layer_id=layer_ids["infra"], display_name="Backbone hint F2"),
        DrawingShape("demo_line_backbone_f3", "Line", [1450, 2560, 2350, 500], "#0f172a", 4, layer_id=layer_ids["infra"], display_name="Backbone hint F3"),
    ]


def _rect(shape_id: str, points: list[float], color: str, layer_id: str, name: str) -> DrawingShape:
    return DrawingShape(shape_id, "Rectangle", points, color=color, line_thickness=3, layer_id=layer_id, display_name=name)


def _text(shape_id: str, label: str, x: float, y: float, layer_id: str) -> DrawingShape:
    return DrawingShape(shape_id, "Text", [x, y], color="#111827", line_thickness=28, label=label, layer_id=layer_id, display_name=label)


def main() -> None:
    """Parse CLI arguments and seed the demo layout."""
    parser = argparse.ArgumentParser(description="Seed the multi-floor demo layout.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH), help="SQLite database path.")
    args = parser.parse_args()
    layout_id = seed_demo_layout(args.db_path)
    print(f"Seeded demo layout: {layout_id}")


if __name__ == "__main__":
    main()
