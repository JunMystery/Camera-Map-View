"""Tests for the multi-floor demo layout seed script."""

from controllers.camera_data_manager import CameraDataManager
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
from scripts.seed_demo_layout import DEMO_LAYOUT_ID, seed_demo_layout


def test_seed_demo_layout_creates_idempotent_multifloor_sample(tmp_path) -> None:
    db_path = tmp_path / "camera_manager.db"

    assert seed_demo_layout(db_path) == DEMO_LAYOUT_ID
    assert seed_demo_layout(db_path) == DEMO_LAYOUT_ID

    manager = CameraDataManager(db_path)
    try:
        layout = manager.get_layout(DEMO_LAYOUT_ID)
        assert layout is not None
        assert layout.canvas_width == 4200
        assert layout.canvas_height == 3000
        assert layout.grid_size == 50

        devices = manager.get_all_cameras(DEMO_LAYOUT_ID)
        assert len(devices) == 23
        assert len(manager.get_placed_cameras(DEMO_LAYOUT_ID)) == len(devices)
        assert {device.device_kind for device in devices} >= {
            DEVICE_KIND_CAMERA,
            DEVICE_KIND_SERVER,
            DEVICE_KIND_FIREWALL,
            DEVICE_KIND_ROUTER,
            DEVICE_KIND_SWITCH,
            DEVICE_KIND_AP,
            DEVICE_KIND_DVR,
            DEVICE_KIND_PC,
        }
        assert {device.variant for device in devices if device.device_kind == DEVICE_KIND_PC} == {
            "PC",
            "Laptop",
            "Workstation",
        }

        links = manager.get_device_links(DEMO_LAYOUT_ID)
        assert len(links) == 22
        incoming_to_core = manager.get_incoming_device_ids("demo_switch_core", DEMO_LAYOUT_ID)
        assert set(incoming_to_core) == {"demo_sw_f1", "demo_sw_f2", "demo_sw_f3"}
        incoming_to_floor1_switch = manager.get_incoming_device_ids("demo_sw_f1", DEMO_LAYOUT_ID)
        assert len(incoming_to_floor1_switch) >= 3

        drawings = manager.get_drawing_shapes(DEMO_LAYOUT_ID)
        assert len(drawings) >= 10
        assert {shape.shape_type for shape in drawings} >= {"Rectangle", "Text", "Line"}
        assert any(shape.label == "Server Room" for shape in drawings)
    finally:
        manager.db.close()
