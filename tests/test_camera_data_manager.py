"""Tests for camera CRUD persistence."""

from controllers.camera_data_manager import CameraDataManager
from models.camera_data_model import Camera
from models.camera_db_manager import CameraDbManager
from models.drawing_shape_model import DrawingShape


def test_add_and_fetch_camera() -> None:
    manager = CameraDataManager(":memory:")
    camera = Camera("cam_test", "Lobby", "10.0.0.10")

    assert manager.add_camera(camera)

    saved = manager.get_camera("cam_test")
    assert saved is not None
    assert saved.name == "Lobby"
    assert saved.ip_address == "10.0.0.10"
    assert saved.display_scale == 1.0


def test_reject_duplicate_ip_address() -> None:
    manager = CameraDataManager(":memory:")

    assert manager.add_camera(Camera("cam_a", "A", "10.0.0.10"))
    assert not manager.add_camera(Camera("cam_b", "B", "10.0.0.10"))


def test_reject_invalid_camera_input() -> None:
    manager = CameraDataManager(":memory:")

    assert not manager.add_camera(Camera("cam_test", "", "10.0.0.10"))
    assert not manager.add_camera(Camera("cam_test", "Lobby", "999.0.0.10"))
    assert not manager.add_camera(Camera("cam_test", "Lobby", "10.0.0.10", port=0))


def test_update_camera_position_marks_camera_as_placed() -> None:
    manager = CameraDataManager(":memory:")
    manager.add_camera(Camera("cam_test", "Lobby", "10.0.0.10"))

    assert manager.update_camera_position("cam_test", 12.5, 34.5)

    placed = manager.get_placed_cameras()
    unplaced = manager.get_unplaced_cameras()
    assert [camera.id for camera in placed] == ["cam_test"]
    assert unplaced == []
    assert placed[0].position_x == 12.5
    assert placed[0].position_y == 34.5
    assert placed[0].layer_id == manager.default_layer_id("default", "cameras")


def test_default_layers_and_membership_are_created() -> None:
    manager = CameraDataManager(":memory:")
    manager.add_camera(Camera("cam_test", "Lobby", "10.0.0.10"))
    manager.add_drawing_shape(DrawingShape("shape_test", "Text", [0.0, 0.0], label="Note"))

    layers = manager.get_layers()

    assert [layer.name for layer in layers] == ["Cameras", "Drawings", "Images", "Text"]
    assert manager.get_camera("cam_test").layer_id == manager.default_layer_id("default", "cameras")
    assert manager.get_drawing_shapes()[0].layer_id == manager.default_layer_id("default", "text")


def test_layer_crud_reorder_and_delete_contents() -> None:
    manager = CameraDataManager(":memory:")
    layer = manager.create_layer("Custom")
    camera = Camera("cam_test", "Lobby", "10.0.0.10", layer_id=layer.id)
    shape = DrawingShape("shape_test", "Line", [0.0, 0.0, 1.0, 1.0], layer_id=layer.id)
    manager.add_camera(camera)
    manager.add_drawing_shape(shape)

    assert manager.rename_layer(layer.id, "Renamed")
    assert manager.set_layer_visible(layer.id, False)
    assert manager.set_layer_locked(layer.id, True)
    assert manager.move_layer(layer.id, -1)

    saved = next(item for item in manager.get_layers() if item.id == layer.id)
    assert saved.name == "Renamed"
    assert saved.visible is False
    assert saved.locked is True

    assert manager.delete_layer(layer.id)
    assert manager.get_camera("cam_test") is None
    assert manager.get_drawing_shapes() == []


def test_update_camera_details_and_delete() -> None:
    manager = CameraDataManager(":memory:")
    manager.add_camera(Camera("cam_test", "Lobby", "10.0.0.10"))

    updated = Camera(
        "cam_test",
        "Updated Lobby",
        "10.0.0.11",
        port=8554,
        camera_type="PTZ",
        rotation=90.0,
        status=True,
        notes="Main entrance",
        zone="Lobby",
        dvr_origin="DVR-A",
    )
    assert manager.update_camera_details(updated)

    saved = manager.get_camera("cam_test")
    assert saved is not None
    assert saved.name == "Updated Lobby"
    assert saved.ip_address == "10.0.0.11"
    assert saved.port == 8554
    assert saved.camera_type == "PTZ"
    assert saved.rotation == 90.0
    assert saved.status is True
    assert saved.notes == "Main entrance"
    assert saved.zone == "Lobby"
    assert saved.dvr_origin == "DVR-A"

    assert manager.update_camera_rotation("cam_test", 375.0)
    rotated = manager.get_camera("cam_test")
    assert rotated is not None
    assert rotated.rotation == 15.0

    assert manager.update_camera_scale("cam_test", 2.25)
    scaled = manager.get_camera("cam_test")
    assert scaled is not None
    assert scaled.display_scale == 2.25

    assert manager.delete_camera("cam_test")
    assert manager.get_camera("cam_test") is None


def test_delete_camera_cascades_ping_history() -> None:
    manager = CameraDataManager(":memory:")
    manager.add_camera(Camera("cam_test", "Lobby", "10.0.0.10"))
    manager.update_camera_status("cam_test", True, 1.0)

    assert len(manager.get_ping_history("cam_test")) == 1
    assert manager.delete_camera("cam_test")
    assert manager.get_ping_history("cam_test") == []


def test_add_and_fetch_drawing_shape() -> None:
    manager = CameraDataManager(":memory:")
    shape = DrawingShape("shape_test", "Image", [0.0, 0.0, 40.0, 80.0], image_path="assets/maps/test.png")

    assert manager.add_drawing_shape(shape)

    saved_shapes = manager.get_drawing_shapes()
    assert len(saved_shapes) == 1
    assert saved_shapes[0].id == shape.id
    assert saved_shapes[0].layer_id == manager.default_layer_id("default", "images")
    assert manager.delete_drawing_shape("shape_test")
    assert manager.get_drawing_shapes() == []


def test_database_manager_creates_startup_backup(tmp_path) -> None:
    db_path = tmp_path / "camera_manager.db"
    manager = CameraDbManager(db_path)
    manager.close()

    reopened = CameraDbManager(db_path)
    reopened.close()

    assert db_path.with_suffix(".db.bak").exists()


def test_camera_csv_import_and_export(tmp_path) -> None:
    manager = CameraDataManager(":memory:")
    csv_path = tmp_path / "cameras.csv"
    csv_path.write_text(
        "id,name,ip_address,port,camera_type,zone,dvr_origin,notes\n"
        "csv_01,Gate,10.0.0.20,554,AI,North,DVR-1,Imported\n",
        encoding="utf-8",
    )

    assert manager.import_cameras_csv(csv_path) == 1
    imported = manager.get_camera("csv_01")
    assert imported is not None
    assert imported.dvr_origin == "DVR-1"

    export_path = tmp_path / "export.csv"
    manager.export_cameras_csv(export_path)
    assert "csv_01" in export_path.read_text(encoding="utf-8")


def test_layout_crud_and_data_isolation() -> None:
    manager = CameraDataManager(":memory:")
    layout = manager.create_layout("Second")
    manager.add_camera(Camera("cam_default", "Default", "10.0.0.1"), layout_id="default")
    manager.add_camera(Camera("cam_second", "Second", "10.0.0.1"), layout_id=layout.id)
    manager.add_drawing_shape(DrawingShape("shape_second", "Line", [0, 0, 10, 10]), layout.id)

    assert [camera.id for camera in manager.get_all_cameras("default")] == ["cam_default"]
    assert [camera.id for camera in manager.get_all_cameras(layout.id)] == ["cam_second"]
    assert [shape.id for shape in manager.get_drawing_shapes(layout.id)] == ["shape_second"]

    layout.canvas_width = 5000
    layout.background_scale = 1.5
    assert manager.update_layout(layout)
    saved = manager.get_layout(layout.id)
    assert saved is not None
    assert saved.canvas_width == 5000
    assert saved.background_scale == 1.5

    assert manager.delete_layout(layout.id)
    assert manager.get_all_cameras(layout.id) == []
    assert manager.get_drawing_shapes(layout.id) == []
