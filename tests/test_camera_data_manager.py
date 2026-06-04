"""Tests for camera CRUD persistence."""

from controllers.camera_data_manager import CameraDataManager
from models.camera_data_model import Camera
from models.camera_db_manager import CameraDbManager
from models.device_catalog import DEVICE_KIND_SERVER, DEVICE_KIND_SWITCH
from models.drawing_shape_model import DrawingShape
from services.map_package_service import export_map_package, import_map_package
from zipfile import ZipFile


def _create_default_layout(manager: CameraDataManager) -> None:
    manager.db.execute(
        "INSERT OR IGNORE INTO map_layouts (id, name, background_path) VALUES (?, ?, ?)",
        ("default", "Default Layout", ""),
    )


def test_add_and_fetch_camera() -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    camera = Camera(
        "cam_test",
        "Lobby",
        "10.0.0.10",
        location_image_path="assets/camera_photos/photo.jpg",
        fov_degrees=180,
        object_locked=True,
        z_index=7,
        object_visible=False,
        badge_text="lb1",
    )

    assert manager.add_camera(camera)

    saved = manager.get_camera("cam_test")
    assert saved is not None
    assert saved.name == "Lobby"
    assert saved.ip_address == "10.0.0.10"
    assert saved.display_scale == 1.0
    assert saved.location_image_path == "assets/camera_photos/photo.jpg"
    assert saved.fov_degrees == 180
    assert saved.object_locked is True
    assert saved.z_index == 7
    assert saved.object_visible is False
    assert saved.badge_text == "LB1"


def test_new_database_starts_without_default_layout() -> None:
    manager = CameraDataManager(":memory:")

    assert manager.get_layouts() == []
    assert manager.get_layout("default") is None
    assert not manager.add_camera(Camera("cam_test", "Lobby", "10.0.0.10"))


def test_reject_duplicate_ip_address() -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)

    assert manager.add_camera(Camera("cam_a", "A", "10.0.0.10"))
    assert not manager.add_camera(Camera("cam_b", "B", "10.0.0.10"))


def test_reject_invalid_camera_input() -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)

    assert not manager.add_camera(Camera("cam_test", "", "10.0.0.10"))
    assert not manager.add_camera(Camera("cam_test", "Lobby", "999.0.0.10"))
    assert not manager.add_camera(Camera("cam_test", "Lobby", "10.0.0.10", port=0))


def test_network_device_allows_blank_ip_and_links_are_layout_scoped() -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    server = Camera("server_a", "Server A", "", device_kind=DEVICE_KIND_SERVER, variant="Rack", ping_enabled=False)
    switch = Camera("switch_a", "Switch A", "", device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)

    assert manager.add_camera(server)
    assert manager.add_camera(switch)
    assert manager.add_device_link("switch_a", "server_a")

    assert [camera.id for camera in manager.get_all_cameras()] == ["server_a", "switch_a"]
    assert manager.get_all_cameras_for_ping() == []
    assert manager.get_linked_device_ids("switch_a") == ["server_a"]
    assert len(manager.get_device_links()) == 1
    assert not manager.add_device_link("server_a", "switch_a")


def test_parent_ip_for_device_uses_direct_parent_links(tmp_path) -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    camera = Camera("cam_a", "Camera A", "10.0.0.10")
    ap = Camera("ap_a", "AP A", "10.0.0.2", device_kind="AP", variant="Indoor AP", ping_enabled=False)
    switch = Camera("switch_a", "Switch A", "10.0.0.1", device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    parent_b = Camera("parent_b", "Parent B", "10.0.0.3", device_kind=DEVICE_KIND_SWITCH, variant="Access", ping_enabled=False)
    no_ip_parent = Camera("parent_empty", "Parent Empty", "", device_kind=DEVICE_KIND_SERVER, variant="Rack", ping_enabled=False)
    for device in (camera, ap, switch, parent_b, no_ip_parent):
        assert manager.add_camera(device)
    assert manager.add_device_link("cam_a", "ap_a")
    assert manager.add_device_link("ap_a", "switch_a")

    assert manager.parent_ip_for_device("cam_a") == "10.0.0.2"
    assert manager.parent_ip_for_device("ap_a") == "10.0.0.1"

    assert manager.add_device_link("cam_a", "parent_b")
    assert manager.add_device_link("cam_a", "parent_empty")
    assert manager.parent_ip_for_device("cam_a") == "10.0.0.2, 10.0.0.3"

    export_path = tmp_path / "parent_ip.csv"
    manager.export_cameras_csv(export_path)
    exported = export_path.read_text(encoding="utf-8")
    assert "parent_ip" in exported
    assert "10.0.0.2, 10.0.0.3" in exported


def test_update_camera_position_marks_camera_as_placed() -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    manager.add_camera(Camera("cam_test", "Lobby", "10.0.0.10"))

    assert manager.update_camera_position("cam_test", 12.5, 34.5)

    placed = manager.get_placed_cameras()
    unplaced = manager.get_unplaced_cameras()
    assert [camera.id for camera in placed] == ["cam_test"]
    assert unplaced == []
    assert placed[0].position_x == 12.5
    assert placed[0].position_y == 34.5
    assert placed[0].layer_id == manager.first_layer_id("default")


def test_base_layer_and_membership_are_created() -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    manager.add_camera(Camera("cam_test", "Lobby", "10.0.0.10"))
    manager.add_drawing_shape(DrawingShape("shape_test", "Text", [0.0, 0.0], label="Note"))

    layers = manager.get_layers()

    assert [layer.name for layer in layers] == ["Layer 1"]
    assert manager.get_camera("cam_test").layer_id == layers[0].id
    assert manager.get_drawing_shapes()[0].layer_id == layers[0].id


def test_legacy_default_layers_migrate_to_single_user_layer() -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    for position, kind in enumerate(("cameras", "drawings", "images", "text")):
        manager.db.execute(
            "INSERT INTO canvas_layers (id, layout_id, name, position) VALUES (?, ?, ?, ?)",
            (manager.default_layer_id("default", kind), "default", kind.title(), position),
        )
    manager.add_camera(Camera("cam_legacy", "Legacy", "10.0.0.40", layer_id=manager.default_layer_id("default", "cameras")))
    manager.add_drawing_shape(
        DrawingShape("shape_legacy", "Text", [0.0, 0.0], label="Old", layer_id=manager.default_layer_id("default", "text"))
    )

    layers = manager.get_layers()

    assert [layer.name for layer in layers] == ["Layer 1"]
    assert manager.get_camera("cam_legacy").layer_id == layers[0].id
    assert manager.get_drawing_shapes()[0].layer_id == layers[0].id


def test_layer_crud_reorder_and_delete_contents() -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    manager.get_layers()
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


def test_layer_group_is_one_level_and_persistent() -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    manager.get_layers()
    group = manager.create_layer_group("Network")
    layer = manager.create_layer("Devices")

    assert group.is_group
    assert manager.set_layer_group(layer.id, group.id)

    saved = {item.id: item for item in manager.get_layers()}
    assert saved[layer.id].group_id == group.id
    assert not manager.set_layer_group(group.id, group.id)

    assert manager.delete_layer(group.id)
    assert next(item for item in manager.get_layers() if item.id == layer.id).group_id == ""


def test_update_camera_details_and_delete() -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
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
        location_image_path="assets/camera_photos/updated.jpg",
        fov_degrees=360,
        object_locked=True,
        z_index=3,
        badge_text="S1",
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
    assert saved.location_image_path == "assets/camera_photos/updated.jpg"
    assert saved.fov_degrees == 360
    assert saved.object_locked is True
    assert saved.z_index == 3
    assert saved.badge_text == "S1"

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
    _create_default_layout(manager)
    manager.add_camera(Camera("cam_test", "Lobby", "10.0.0.10"))
    manager.update_camera_status("cam_test", True, 1.0)

    assert len(manager.get_ping_history("cam_test")) == 1
    assert manager.delete_camera("cam_test")
    assert manager.get_ping_history("cam_test") == []


def test_add_and_fetch_drawing_shape() -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    shape = DrawingShape(
        "shape_test",
        "Image",
        [0.0, 0.0, 40.0, 80.0],
        image_path="assets/maps/test.png",
        display_name="Site photo",
        object_locked=True,
        z_index=4,
        fill_color="#00ff00",
        object_visible=False,
    )

    assert manager.add_drawing_shape(shape)

    saved_shapes = manager.get_drawing_shapes()
    assert len(saved_shapes) == 1
    assert saved_shapes[0].id == shape.id
    assert saved_shapes[0].layer_id == manager.first_layer_id("default")
    assert saved_shapes[0].display_name == "Site photo"
    assert saved_shapes[0].object_locked is True
    assert saved_shapes[0].z_index == 4
    assert saved_shapes[0].fill_color == "#00ff00"
    assert saved_shapes[0].object_visible is False
    assert manager.update_drawing_shape_display_name("shape_test", "Renamed photo")
    assert manager.get_drawing_shapes()[0].display_name == "Renamed photo"
    assert manager.update_drawing_shape_object_visible("shape_test", True)
    assert manager.get_drawing_shapes()[0].object_visible is True
    assert manager.delete_drawing_shape("shape_test")
    assert manager.get_drawing_shapes() == []


def test_update_drawing_shape_persists_text_style() -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    shape = DrawingShape("shape_text", "Text", [10.0, 20.0], color="#111111", line_thickness=18, label="Old")
    manager.add_drawing_shape(shape)

    updated = DrawingShape(
        "shape_text",
        "Text",
        [30.0, 40.0],
        color="#00ff00",
        line_thickness=24,
        label="New",
        display_name="Layer text",
        fill_color="#ff00ff",
    )

    assert manager.update_drawing_shape(updated)
    saved = manager.get_drawing_shapes()[0]
    assert saved.label == "New"
    assert saved.color == "#00ff00"
    assert saved.line_thickness == 24
    assert saved.points == [30.0, 40.0]
    assert saved.display_name == "Layer text"
    assert saved.fill_color == "#ff00ff"


def test_database_manager_creates_startup_backup(tmp_path) -> None:
    db_path = tmp_path / "camera_manager.db"
    manager = CameraDbManager(db_path)
    manager.close()

    reopened = CameraDbManager(db_path)
    reopened.close()

    assert db_path.with_suffix(".db.bak").exists()


def test_camera_csv_import_and_export(tmp_path) -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    csv_path = tmp_path / "cameras.csv"
    csv_path.write_text(
        "id,name,ip_address,port,camera_type,zone,parent_ip,notes\n"
        "csv_01,Gate,10.0.0.20,554,AI,North,10.0.0.1,Imported\n",
        encoding="utf-8",
    )

    assert manager.import_cameras_csv(csv_path) == 1
    imported = manager.get_camera("csv_01")
    assert imported is not None
    assert imported.dvr_origin == ""

    export_path = tmp_path / "export.csv"
    manager.export_cameras_csv(export_path)
    exported = export_path.read_text(encoding="utf-8")
    assert "csv_01" in exported
    assert "parent_ip" in exported
    assert "dvr_origin" not in exported


def test_camera_csv_import_replaces_existing_and_preserves_canvas_state(tmp_path) -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    manager.get_layers()
    layer = manager.create_layer("Placed")
    existing = Camera(
        "csv_01",
        "Old",
        "10.0.0.20",
        rotation=45.0,
        display_scale=2.0,
        layer_id=layer.id,
        z_index=5,
        object_locked=True,
        object_visible=False,
        badge_text="A1",
    )
    assert manager.add_camera(existing, is_placed=True)
    assert manager.update_camera_position_in_layout("csv_01", 12.0, 34.0, "default")
    assert manager.update_camera_scale_in_layout("csv_01", 2.0, "default")
    assert manager.update_camera_rotation_in_layout("csv_01", 45.0, "default")
    assert manager.update_camera_layer("csv_01", layer.id, "default")
    csv_path = tmp_path / "replace.csv"
    csv_path.write_text(
        "id,name,ip_address,port,camera_type,device_kind,variant,ping_enabled,zone,parent_ip,notes\n"
        "csv_01,New Name,10.0.0.21,8554,Dome,Camera,Dome,0,North,10.0.0.1,Updated\n",
        encoding="utf-8",
    )

    assert manager.import_cameras_csv(csv_path) == 1

    saved = manager.get_camera("csv_01")
    assert saved is not None
    assert saved.name == "New Name"
    assert saved.ip_address == "10.0.0.21"
    assert saved.port == 8554
    assert saved.camera_type == "Dome"
    assert saved.variant == "Dome"
    assert saved.ping_enabled is False
    assert saved.zone == "North"
    assert saved.dvr_origin == ""
    assert saved.notes == "Updated"
    assert saved.position_x == 12.0
    assert saved.position_y == 34.0
    assert saved.rotation == 45.0
    assert saved.display_scale == 2.0
    assert saved.layer_id == layer.id
    assert saved.z_index == 5
    assert saved.object_locked is True
    assert saved.object_visible is False
    assert saved.badge_text == "A1"
    assert [camera.id for camera in manager.get_placed_cameras()] == ["csv_01"]


def test_camera_csv_import_replaces_name_with_normalized_headers(tmp_path) -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    assert manager.add_camera(Camera("csv_01", "Old Name", "10.0.0.20"))
    csv_path = tmp_path / "replace_name.csv"
    csv_path.write_text(
        " ID , Name , IP_Address , Port , Camera_Type , Device_Kind , Variant \n"
        "csv_01,Renamed From CSV,10.0.0.21,554,Fixed,Camera,Fixed\n",
        encoding="utf-8",
    )

    assert manager.import_cameras_csv(csv_path) == 1

    saved = manager.get_camera("csv_01")
    assert saved is not None
    assert saved.name == "Renamed From CSV"
    assert saved.ip_address == "10.0.0.21"


def test_camera_csv_import_generates_missing_id_and_skips_empty_or_bad_rows(tmp_path) -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    csv_path = tmp_path / "generated_ids.csv"
    csv_path.write_text(
        "id,name,ip_address,port,camera_type,device_kind,variant,zone,parent_ip,notes\n"
        ",Generated,10.0.0.30,554,Fixed,Camera,Fixed,,,\n"
        ",,,,,,,,,\n"
        "bad_port,Bad Port,10.0.0.31,not-a-port,Fixed,Camera,Fixed,,,\n",
        encoding="utf-8",
    )

    assert manager.import_cameras_csv(csv_path) == 1

    cameras = manager.get_all_cameras()
    assert len(cameras) == 1
    assert cameras[0].id.startswith("dev_")
    assert cameras[0].name == "Generated"
    assert cameras[0].ip_address == "10.0.0.30"


def test_camera_csv_import_rejects_ip_conflict_and_other_layout_id(tmp_path) -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    other = manager.create_layout("Other")
    assert manager.add_camera(Camera("existing", "Existing", "10.0.0.40"))
    assert manager.add_camera(Camera("same_id", "Default", "10.0.0.41"))
    conflict_path = tmp_path / "conflict.csv"
    conflict_path.write_text(
        "id,name,ip_address,port,camera_type,device_kind,variant\n"
        "new_id,Conflict,10.0.0.40,554,Fixed,Camera,Fixed\n",
        encoding="utf-8",
    )

    assert manager.import_cameras_csv(conflict_path) == 0
    assert manager.get_camera("new_id") is None

    other_path = tmp_path / "other_layout.csv"
    other_path.write_text(
        "id,name,ip_address,port,camera_type,device_kind,variant\n"
        "same_id,Should Not Replace,10.0.0.50,554,Fixed,Camera,Fixed\n",
        encoding="utf-8",
    )

    assert manager.import_cameras_csv(other_path, other.id) == 0
    saved = manager.get_camera("same_id")
    assert saved is not None
    assert saved.name == "Default"
    assert saved.ip_address == "10.0.0.41"


def test_layout_crud_and_data_isolation() -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
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


def test_default_layout_can_be_deleted() -> None:
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)

    assert manager.delete_layout("default")
    assert manager.get_layouts() == []


def test_map_package_export_and_import_current_layout(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    layout = manager.get_layout("default")
    assert layout is not None
    background = tmp_path / "map.png"
    background.write_bytes(b"map")
    image = tmp_path / "note.png"
    image.write_bytes(b"png")
    photo = tmp_path / "camera_photo.jpg"
    photo.write_bytes(b"jpg")
    layout.background_path = str(background)
    layout.canvas_width = 1200
    manager.update_layout(layout)
    manager.add_camera(Camera("cam_pkg", "Package Cam", "10.0.0.30", location_image_path=str(photo)), is_placed=True)
    manager.add_camera(Camera("server_pkg", "Package Server", "", device_kind=DEVICE_KIND_SERVER, variant="Rack", ping_enabled=False), is_placed=True)
    manager.add_device_link("cam_pkg", "server_pkg")
    shape = DrawingShape("shape_pkg", "Image", [1.0, 2.0, 30.0, 40.0], image_path=str(image), display_name="Packaged image")
    manager.add_drawing_shape(shape)
    cameras = []
    for camera in manager.get_all_cameras():
        row = camera.to_dict()
        row["is_placed"] = camera.id in {item.id for item in manager.get_placed_cameras()}
        cameras.append(row)
    package = tmp_path / "map.cmvmap"

    assert export_map_package(
        package,
        layout,
        {"grid_size": 20},
        {"name": True},
        cameras,
        manager.get_layers(),
        manager.get_drawing_shapes(),
        manager.get_device_links(),
    )

    with ZipFile(package) as archive:
        assert "manifest.json" in archive.namelist()
        assert any(name.startswith("assets/background_") for name in archive.namelist())
        assert any(name.startswith("assets/drawing_shape_pkg_") for name in archive.namelist())
        assert any(name.startswith("assets/camera_cam_pkg_") for name in archive.namelist())

    imported_id = import_map_package(package, manager)

    assert imported_id and imported_id != "default"
    imported_layout = manager.get_layout(imported_id)
    assert imported_layout is not None
    assert imported_layout.canvas_width == 1200
    assert imported_layout.background_path
    imported_cameras = manager.get_placed_cameras(imported_id)
    assert len(imported_cameras) == 2
    assert any(camera.location_image_path for camera in imported_cameras)
    assert manager.get_device_links(imported_id)
    imported_shapes = manager.get_drawing_shapes(imported_id)
    assert imported_shapes
    assert imported_shapes[0].display_name == "Packaged image"
