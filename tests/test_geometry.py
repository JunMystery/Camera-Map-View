"""Tests for geometry helpers and snap behavior."""

from PyQt6.QtCore import QByteArray, QMimeData, QPointF, Qt
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication, QDialogButtonBox, QGraphicsView, QMenu

from models.camera_data_model import Camera
from models.canvas_layer_model import CanvasLayer
from models.device_link_model import DeviceLink
from models.device_catalog import DEVICE_KIND_PC, DEVICE_KIND_SERVER, DEVICE_KIND_SWITCH
from models.drawing_shape_model import DrawingShape
from utils.geometry import snap_to_grid
from utils.image_assets import CAMERA_PHOTO_MAX_EDGE, import_camera_location_image
from config.i18n import set_language
from views.camera_location_image_dialog import CameraLocationImageDialog
from views.camera_view_dialog import CameraPropertiesDialog
from views.device_connections_dialog import DeviceConnectionsDialog
from views.layer_state import BACKGROUND_LAYER, GRID_LAYER
from views.map_drawing_tools import DrawingMode
from views.map_view_canvas import MapCanvas
from views.tool_icons import device_icon, tool_icon


def test_snap_to_grid_rounds_to_nearest_intersection() -> None:
    assert snap_to_grid(23.4, 47.9, 20) == (20.0, 40.0)
    assert snap_to_grid(31.0, 49.0, 20) == (40.0, 40.0)


def test_canvas_snaps_camera_items_when_moved() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.grid_size = 20
    item = canvas.add_camera_item(Camera("cam_test", "Lobby", "10.0.0.10"))

    item.setPos(23.4, 47.9)

    assert item.pos().x() == 20.0
    assert item.pos().y() == 40.0
    assert item.camera.position_x == 20.0
    assert item.camera.position_y == 40.0
    app.processEvents()


def test_canvas_creates_rectangle_shape_from_drawing_points() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.grid_size = 20
    canvas.set_drawing_mode(DrawingMode.RECTANGLE)

    shape = canvas._shape_from_points(canvas.mapToScene(0, 0), canvas.mapToScene(41, 79))

    assert shape is not None
    assert shape.shape_type == "Rectangle"
    assert shape.points == [0.0, 0.0, 40.0, 80.0]
    app.processEvents()


def test_canvas_defaults_to_pan_mode() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()

    assert canvas.drawing_mode == DrawingMode.PAN
    assert canvas.dragMode() == QGraphicsView.DragMode.ScrollHandDrag
    app.processEvents()


def test_pan_mode_disables_item_interaction_until_select() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    camera_item = canvas.add_camera_item(Camera("cam_test", "Lobby", "10.0.0.10"))

    assert not camera_item.flags() & camera_item.GraphicsItemFlag.ItemIsSelectable
    assert not camera_item.flags() & camera_item.GraphicsItemFlag.ItemIsMovable

    canvas.set_drawing_mode(DrawingMode.SELECT)

    assert camera_item.flags() & camera_item.GraphicsItemFlag.ItemIsSelectable
    assert camera_item.flags() & camera_item.GraphicsItemFlag.ItemIsMovable
    app.processEvents()


def test_escape_cancels_camera_resize_and_rotation() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    item = canvas.add_camera_item(Camera("cam_test", "Lobby", "10.0.0.10", rotation=20.0))
    canvas.set_drawing_mode(DrawingMode.SELECT)
    item.setSelected(True)

    item.mousePressEvent(_ItemMouseEvent(Qt.MouseButton.LeftButton, QPointF(46, 0)))
    assert item.is_rotating
    assert item.camera.rotation != 20.0

    canvas.keyPressEvent(_KeyEvent(Qt.Key.Key_Escape))

    assert not item.is_rotating
    assert item.camera.rotation == 20.0

    item.mousePressEvent(_ItemMouseEvent(Qt.MouseButton.LeftButton, QPointF(54, 54), QPointF(100, 100)))
    item._apply_resize_from_distance(200.0)
    assert item.scale() != 1.0

    canvas.keyPressEvent(_KeyEvent(Qt.Key.Key_Escape))

    assert not item.is_resizing
    assert item.scale() == 1.0
    app.processEvents()


def test_missing_background_image_keeps_existing_scene() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    camera = canvas.add_camera_item(Camera("cam_test", "Lobby", "10.0.0.10"))

    assert not canvas.load_background_image("does-not-exist.png")
    assert camera.scene() is canvas.scene
    assert canvas.background_item is None
    app.processEvents()


def test_background_load_and_unload_preserve_map_items(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    camera = canvas.add_camera_item(Camera("cam_test", "Lobby", "10.0.0.10"))
    shape_item = canvas.add_drawing_shape(DrawingShape("shape_test", "Line", [0.0, 0.0, 40.0, 40.0]))
    image_path = tmp_path / "map.png"
    image = QImage(120, 80, QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    assert image.save(str(image_path))

    assert canvas.load_background_image(str(image_path))
    assert canvas.background_item is not None
    assert camera.scene() is canvas.scene
    assert shape_item is not None
    assert shape_item.scene() is canvas.scene

    canvas.unload_background_image()
    assert canvas.background_item is None
    assert camera.scene() is canvas.scene
    assert shape_item.scene() is canvas.scene
    assert canvas.grid_items
    app.processEvents()


def test_canvas_drawing_mouse_events_create_shape() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.grid_size = 20
    canvas.set_drawing_mode(DrawingMode.LINE)
    created = []
    canvas.drawing_created.connect(created.append)

    canvas.mousePressEvent(_MouseEvent(Qt.MouseButton.LeftButton, 0, 0))
    canvas.mouseMoveEvent(_MouseEvent(Qt.MouseButton.LeftButton, 41, 79))
    canvas.mouseReleaseEvent(_MouseEvent(Qt.MouseButton.LeftButton, 41, 79))

    assert len(created) == 1
    assert created[0].shape_type == "Line"
    assert created[0].points == [0.0, 0.0, 40.0, 80.0]
    app.processEvents()


def test_drop_event_decodes_qbytearray_camera_id() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    dropped = []
    canvas.camera_dropped.connect(lambda camera_id, x, y: dropped.append((camera_id, x, y)))

    event = _DropEvent("cam_test", 20, 40)
    canvas.dropEvent(event)

    assert dropped
    assert dropped[0][0] == "cam_test"
    assert event.accepted
    app.processEvents()


def test_camera_dialog_disables_save_for_invalid_input() -> None:
    app = QApplication.instance() or QApplication([])
    dialog = CameraPropertiesDialog(Camera("cam", "Lobby", "10.0.0.10"))
    save_button = dialog.button_box.button(QDialogButtonBox.StandardButton.Save)

    assert save_button is not None
    assert save_button.isEnabled()

    dialog.name_input.setText("")
    assert not save_button.isEnabled()

    dialog.name_input.setText("Lobby")
    dialog.ip_input.setText("999.0.0.10")
    assert not save_button.isEnabled()
    app.processEvents()


def test_canvas_wheel_zoom_accepts_event_in_modes() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()

    for mode in (DrawingMode.PAN, DrawingMode.SELECT, DrawingMode.LINE):
        canvas.set_drawing_mode(mode)
        before = canvas.transform().m11()
        event = _WheelEvent(120)
        canvas.wheelEvent(event)

        assert event.accepted
        assert canvas.transform().m11() > before

    app.processEvents()


def test_canvas_device_links_follow_downstream_and_single_upstream_path() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.set_drawing_mode(DrawingMode.SELECT)
    devices = [
        Camera("router", "Router", "", position_x=300.0, position_y=0.0, device_kind="Router", ping_enabled=False),
        Camera("switch", "Switch", "", position_x=200.0, position_y=0.0, device_kind=DEVICE_KIND_SWITCH, ping_enabled=False),
        Camera("ap", "AP", "", position_x=100.0, position_y=0.0, device_kind="AP", ping_enabled=False),
        Camera("cam", "Camera", "10.0.0.10", position_x=0.0, position_y=0.0),
        Camera("pc", "PC", "", position_x=200.0, position_y=100.0, device_kind=DEVICE_KIND_PC, ping_enabled=False),
    ]
    for device in devices:
        canvas.add_camera_item(device)
    links = [
        DeviceLink("link_cam_ap", "default", "cam", "ap"),
        DeviceLink("link_ap_switch", "default", "ap", "switch"),
        DeviceLink("link_pc_switch", "default", "pc", "switch"),
        DeviceLink("link_switch_router", "default", "switch", "router"),
    ]
    canvas.set_device_links(links)

    canvas.scene.clearSelection()
    canvas.camera_items["cam"].setSelected(True)
    assert {(item.link.source_device_id, item.link.target_device_id) for item in canvas.device_link_items} == {
        ("cam", "ap"),
        ("ap", "switch"),
        ("switch", "router"),
    }

    canvas.scene.clearSelection()
    canvas.camera_items["ap"].setSelected(True)
    assert {(item.link.source_device_id, item.link.target_device_id) for item in canvas.device_link_items} == {
        ("cam", "ap"),
        ("ap", "switch"),
        ("switch", "router"),
    }

    canvas.scene.clearSelection()
    canvas.camera_items["router"].setSelected(True)
    assert {(item.link.source_device_id, item.link.target_device_id) for item in canvas.device_link_items} == {
        ("cam", "ap"),
        ("ap", "switch"),
        ("pc", "switch"),
        ("switch", "router"),
    }
    app.processEvents()


def test_device_dialog_uses_device_name_label_and_preserves_rotation() -> None:
    app = QApplication.instance() or QApplication([])
    dialog = CameraPropertiesDialog(Camera("cam", "Lobby", "10.0.0.10", rotation=123.0))

    assert dialog.name_label.text() == "Tên thiết bị"
    assert not hasattr(dialog, "rotation_slider")
    assert not dialog.fov_input.isHidden()
    assert [dialog.fov_input.itemData(index) for index in range(dialog.fov_input.count())] == [80, 180, 360]
    assert dialog.get_camera().rotation == 123.0
    assert dialog.get_camera().fov_degrees == 80

    dialog.name_input.setText("")
    assert dialog.error_label.text() == "Tên thiết bị không được để trống."
    app.processEvents()


def test_camera_dialog_translates_camera_type_labels_without_changing_value() -> None:
    app = QApplication.instance() or QApplication([])
    set_language("jp")
    dialog = CameraPropertiesDialog(Camera("cam", "Lobby", "10.0.0.10", camera_type="Fixed"))

    assert dialog.type_input.currentText() == "固定"
    assert dialog.get_camera().camera_type == "Fixed"

    set_language("vi")
    app.processEvents()


def test_device_dialog_updates_variant_presets_and_allows_blank_non_camera_ip() -> None:
    app = QApplication.instance() or QApplication([])
    dialog = CameraPropertiesDialog(Camera("device", "", "192.168.1.1"))

    server_index = dialog.kind_input.findData(DEVICE_KIND_SERVER)
    dialog.kind_input.setCurrentIndex(server_index)
    dialog.name_input.setText("Server A")

    assert dialog.ip_input.text() == ""
    assert dialog.ping_input.isChecked() is False
    assert dialog.variant_input.findData("Rack") >= 0
    assert dialog.fov_input.isHidden()
    assert dialog.button_box.button(QDialogButtonBox.StandardButton.Save).isEnabled()
    app.processEvents()


def test_device_dialog_pc_variants_are_available() -> None:
    app = QApplication.instance() or QApplication([])
    dialog = CameraPropertiesDialog(Camera("device", "", "192.168.1.1"))

    pc_index = dialog.kind_input.findData(DEVICE_KIND_PC)
    dialog.kind_input.setCurrentIndex(pc_index)
    dialog.name_input.setText("Laptop A")

    assert pc_index >= 0
    assert [dialog.variant_input.itemData(index) for index in range(dialog.variant_input.count())] == [
        "PC",
        "Laptop",
        "Workstation",
    ]
    assert dialog.ip_input.text() == ""
    assert dialog.button_box.button(QDialogButtonBox.StandardButton.Save).isEnabled()
    app.processEvents()


def test_device_dialog_link_search_preserves_checked_and_shows_incoming() -> None:
    app = QApplication.instance() or QApplication([])
    ap = Camera("ap", "AP 1", "", device_kind="AP", variant="Indoor AP", ping_enabled=False)
    server = Camera("server", "Server A", "", device_kind=DEVICE_KIND_SERVER, variant="Rack", ping_enabled=False)
    camera_a = Camera("cam_a", "Camera A", "10.0.0.10")
    camera_b = Camera("cam_b", "Camera B", "10.0.0.11")
    properties = CameraPropertiesDialog(ap, None, [ap, server, camera_a, camera_b], ["server"], ["cam_a", "cam_b"])
    dialog = DeviceConnectionsDialog(ap, [server, camera_a, camera_b], set(properties.get_linked_device_ids()), {"cam_a", "cam_b"})

    assert not hasattr(properties, "link_list")
    assert not hasattr(properties, "incoming_link_list")
    assert properties.manage_connections_button.text() == "Quản lý kết nối"
    assert dialog.get_linked_device_ids() == ["server"]
    assert dialog.incoming_list.count() == 2

    dialog.search_input.setText("camera a")
    assert dialog.incoming_list.item(0).isHidden() is False
    assert dialog.incoming_list.item(1).isHidden() is True

    dialog.search_input.clear()
    for index in range(dialog.outgoing_list.count()):
        item = dialog.outgoing_list.item(index)
        if item.data(Qt.ItemDataRole.UserRole) == "cam_a":
            item.setCheckState(Qt.CheckState.Checked)

    dialog.search_input.setText("server")
    dialog.search_input.clear()
    assert dialog.get_linked_device_ids() == ["server", "cam_a"]
    app.processEvents()


def test_tool_icons_load_assets_and_fallback() -> None:
    app = QApplication.instance() or QApplication([])

    assert not tool_icon("add").isNull()
    assert not device_icon(DEVICE_KIND_SERVER).isNull()
    assert not device_icon("Unknown Device").isNull()
    app.processEvents()


def test_camera_dialog_preserves_location_image_until_save(tmp_path, monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    old_photo = tmp_path / "old.jpg"
    new_photo = tmp_path / "new.png"
    image = QImage(40, 30, QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    assert image.save(str(old_photo))
    assert image.save(str(new_photo))
    compressed = tmp_path / "compressed.jpg"
    assert image.save(str(compressed))
    monkeypatch.setattr("views.camera_view_dialog.import_camera_location_image", lambda source: (str(compressed), 40, 30))
    dialog = CameraPropertiesDialog(Camera("cam", "Lobby", "10.0.0.10", location_image_path=str(old_photo)))

    dialog.pending_location_source = str(new_photo)
    dialog.location_image_path = str(new_photo)
    updated = dialog.get_camera()

    assert updated.location_image_path.endswith(".jpg")
    assert updated.location_image_path != str(old_photo)
    assert updated.location_image_path == str(compressed)
    app.processEvents()


def test_import_camera_location_image_compresses_to_jpg(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    source = tmp_path / "source.png"
    target_dir = tmp_path / "photos"
    image = QImage(2400, 1200, QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    assert image.save(str(source))

    imported = import_camera_location_image(str(source), target_dir)

    assert imported is not None
    path, width, height = imported
    assert path.endswith(".jpg")
    assert max(width, height) == CAMERA_PHOTO_MAX_EDGE
    assert QImage(path).width() == CAMERA_PHOTO_MAX_EDGE
    app.processEvents()


def test_camera_context_menu_order(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    item = canvas.add_camera_item(Camera("cam_test", "Lobby", "10.0.0.10"))
    captured = []

    def capture_exec(menu: QMenu, _pos: object) -> None:
        captured.extend(action.text() for action in menu.actions())

    monkeypatch.setattr(QMenu, "exec", capture_exec)
    item.contextMenuEvent(_ContextMenuEvent())

    assert captured == ["Ảnh vị trí", "Ping", "Chỉnh sửa thông số"]
    app.processEvents()


def test_location_image_dialog_loads_and_zooms(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "photo.jpg"
    image = QImage(120, 80, QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    assert image.save(str(image_path))
    dialog = CameraLocationImageDialog(str(image_path), "Lobby")

    assert dialog.pixmap_item is not None
    assert dialog.view.dragMode() == QGraphicsView.DragMode.ScrollHandDrag
    before = dialog.zoom_factor
    dialog.zoom_in()
    assert dialog.zoom_factor > before
    dialog.zoom_out()
    wheel_before = dialog.zoom_factor
    dialog.view.wheelEvent(_WheelEvent(120))
    assert dialog.zoom_factor > wheel_before
    dialog.view.wheelEvent(_WheelEvent(-120))
    app.processEvents()


def test_camera_item_rotation_ring_updates_angle() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    item = canvas.add_camera_item(Camera("cam_test", "Lobby", "10.0.0.10"))
    rotations = []
    canvas.camera_rotated.connect(lambda camera_id, angle: rotations.append((camera_id, angle)))

    item.setSelected(True)
    assert item._is_on_rotation_ring(QPointF(46, 0))

    item._apply_rotation_from_point(QPointF(0, 46))

    assert rotations[-1] == ("cam_test", 90.0)
    assert item.camera.rotation == 90.0
    app.processEvents()


def test_camera_item_resize_handle_updates_scale() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    item = canvas.add_camera_item(Camera("cam_test", "Lobby", "10.0.0.10"))

    item.setSelected(True)
    assert item._is_on_resize_handle(QPointF(54, 54))

    item.resize_start_distance = 50.0
    item.resize_start_scale = 1.0
    item._apply_resize_from_distance(100.0)

    assert item.scale() == 2.0
    assert item.camera.display_scale == 2.0

    item._set_camera_scale(0.1)
    assert item.scale() == item.min_scale
    assert item.camera.display_scale == item.min_scale

    item._set_camera_scale(10.0)
    assert item.scale() == item.max_scale
    app.processEvents()


def test_canvas_layer_visibility_lock_and_selection() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    camera_item = canvas.add_camera_item(Camera("cam_test", "Lobby", "10.0.0.10"))
    drawing_item = canvas.add_drawing_shape(DrawingShape("shape_test", "Line", [0.0, 0.0, 40.0, 40.0]))
    assert drawing_item is not None
    layer_id = canvas.active_layer_id

    canvas.set_layer_visible(GRID_LAYER, False)
    canvas.set_layer_visible(layer_id, False)

    assert all(not item.isVisible() for item in canvas.grid_items)
    assert not camera_item.isVisible()
    assert not drawing_item.isVisible()

    canvas.set_drawing_mode(DrawingMode.SELECT)
    canvas.set_layer_visible(layer_id, True)
    canvas.set_layer_locked(layer_id, True)
    assert not camera_item.flags() & camera_item.GraphicsItemFlag.ItemIsMovable
    assert canvas.select_layer_items(layer_id) == 0

    canvas.set_layer_locked(layer_id, False)
    assert canvas.select_layer_items(layer_id) == 2
    assert camera_item.isSelected()
    app.processEvents()


def test_canvas_object_lock_and_z_order_updates_state() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.set_drawing_mode(DrawingMode.SELECT)
    camera_item = canvas.add_camera_item(Camera("cam_test", "Lobby", "10.0.0.10", z_index=0))
    drawing_item = canvas.add_drawing_shape(DrawingShape("shape_test", "Line", [0.0, 0.0, 40.0, 40.0], z_index=1))
    assert drawing_item is not None
    locks = []
    z_changes = []
    canvas.object_locked_changed.connect(lambda object_type, object_id, locked: locks.append((object_type, object_id, locked)))
    canvas.object_z_changed.connect(lambda object_type, object_id, z_index: z_changes.append((object_type, object_id, z_index)))

    assert canvas.set_layer_object_locked("camera", "cam_test", True)
    assert locks[-1] == ("camera", "cam_test", True)
    assert not camera_item.flags() & camera_item.GraphicsItemFlag.ItemIsMovable
    assert canvas.select_layer_object("camera", "cam_test") is False

    assert canvas.move_layer_object("camera", "cam_test", 1)
    assert int(camera_item.data(7) or 0) == 1
    assert int(drawing_item.data(7) or 0) == 0
    assert ("camera", "cam_test", 1) in z_changes
    app.processEvents()


def test_rectangle_and_zone_hit_test_only_uses_border() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    rectangle = canvas.add_drawing_shape(DrawingShape("rect_test", "Rectangle", [0.0, 0.0, 100.0, 100.0]))
    zone = canvas.add_drawing_shape(DrawingShape("zone_test", "Polygon", [0.0, 0.0, 100.0, 0.0, 100.0, 100.0, 0.0, 100.0]))

    assert rectangle is not None
    assert zone is not None
    assert rectangle.shape().contains(QPointF(0.0, 50.0))
    assert not rectangle.shape().contains(QPointF(50.0, 50.0))
    assert zone.shape().contains(QPointF(100.0, 50.0))
    assert not zone.shape().contains(QPointF(50.0, 50.0))
    app.processEvents()


def test_canvas_delete_layer_items_emits_persistence_signal(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    deleted = []
    canvas.drawing_deleted.connect(deleted.append)
    layer_id = canvas.active_layer_id
    text_item = canvas.add_drawing_shape(DrawingShape("text_test", "Text", [1.0, 2.0], label="Hello"))
    image_path = tmp_path / "layer.png"
    image = QImage(32, 32, QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    assert image.save(str(image_path))
    image_item = canvas.add_drawing_shape(DrawingShape("image_test", "Image", [1.0, 2.0, 32.0, 32.0], image_path=str(image_path)))

    assert text_item is not None
    assert image_item is not None
    assert canvas.delete_layer_items(layer_id) == 2
    assert set(deleted) == {"text_test", "image_test"}
    app.processEvents()


def test_canvas_layer_background_delete_and_annotation_reorder(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    image_path = tmp_path / "map.png"
    image = QImage(80, 80, QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    assert image.save(str(image_path))
    assert canvas.load_background_image(str(image_path))

    drawing_item = canvas.add_drawing_shape(DrawingShape("shape_test", "Line", [0.0, 0.0, 40.0, 40.0]))
    text_layer = CanvasLayer("layer_default_2", "default", "Layer 2", 1)
    canvas.set_canvas_layers([*canvas.canvas_layers, text_layer], "default")
    assert canvas.set_active_layer(text_layer.id)
    text_item = canvas.add_drawing_shape(DrawingShape("text_test", "Text", [1.0, 2.0], label="Hello"))

    assert canvas.delete_layer_items(BACKGROUND_LAYER) == 1
    assert canvas.background_item is None
    assert drawing_item is not None
    assert drawing_item.scene() is canvas.scene

    assert text_item is not None
    before = text_item.zValue()
    assert canvas.move_layer(text_layer.id, -1)
    assert text_item.zValue() < before
    app.processEvents()


def test_canvas_draws_new_items_into_active_layer() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    target_layer = CanvasLayer("layer_default_2", "default", "Layer 2", 1)
    canvas.set_canvas_layers([*canvas.canvas_layers, target_layer], "default")
    assert canvas.set_active_layer(target_layer.id)

    item = canvas.add_drawing_shape(DrawingShape("shape_test", "Line", [0.0, 0.0, 40.0, 40.0]))

    assert item is not None
    assert item.data(2) == target_layer.id
    canvas.set_drawing_mode(DrawingMode.SELECT)
    assert canvas.select_layer_items(target_layer.id) == 1
    app.processEvents()


def test_canvas_settings_resize_grid_and_background_scale(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    assert canvas.grid_size == 20
    assert canvas.scene.sceneRect().width() == 4000

    canvas.resize_canvas(1200, 900)
    canvas.redraw_grid(10)
    assert canvas.grid_size == 10
    assert canvas.scene.sceneRect().width() == 1200

    image_path = tmp_path / "map.png"
    image = QImage(100, 80, QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    assert image.save(str(image_path))
    assert canvas.load_background_image(str(image_path))
    canvas.set_background_scale(2.0)

    assert canvas.background_item is not None
    assert canvas.background_item.pixmap().width() == 200
    app.processEvents()


def test_scene_clamps_drawing_items_to_canvas_bounds() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.resize_canvas(100, 100)
    item = canvas.add_drawing_shape(DrawingShape("shape_test", "Rectangle", [0.0, 0.0, 20.0, 20.0]))
    assert item is not None
    canvas.set_drawing_mode(DrawingMode.SELECT)
    item.setSelected(True)

    item.setPos(200, 200)
    canvas.scene.clamp_selected_items()

    assert item.sceneBoundingRect().right() <= 100
    assert item.sceneBoundingRect().bottom() <= 100
    app.processEvents()


class _MouseEvent:
    def __init__(self, button: Qt.MouseButton, x: float, y: float) -> None:
        self._button = button
        self._position = QPointF(x, y)
        self.accepted = False

    def button(self) -> Qt.MouseButton:
        return self._button

    def position(self) -> QPointF:
        return self._position

    def accept(self) -> None:
        self.accepted = True


class _ItemMouseEvent:
    def __init__(self, button: Qt.MouseButton, pos: QPointF, scene_pos: QPointF | None = None) -> None:
        self._button = button
        self._pos = pos
        self._scene_pos = scene_pos or pos
        self.accepted = False

    def button(self) -> Qt.MouseButton:
        return self._button

    def pos(self) -> QPointF:
        return self._pos

    def scenePos(self) -> QPointF:
        return self._scene_pos

    def accept(self) -> None:
        self.accepted = True


class _KeyEvent:
    def __init__(self, key: Qt.Key) -> None:
        self._key = key
        self.accepted = False

    def key(self) -> Qt.Key:
        return self._key

    def isAutoRepeat(self) -> bool:
        return False

    def accept(self) -> None:
        self.accepted = True


class _ContextMenuEvent:
    def screenPos(self) -> QPointF:
        return QPointF(0, 0)


class _WheelEvent:
    def __init__(self, delta_y: int) -> None:
        self._delta_y = delta_y
        self.accepted = False

    def angleDelta(self) -> QPointF:
        return QPointF(0, self._delta_y)

    def accept(self) -> None:
        self.accepted = True


class _DropEvent:
    def __init__(self, camera_id: str, x: float, y: float) -> None:
        self._mime_data = QMimeData()
        self._mime_data.setData("application/x-camera-id", QByteArray(camera_id.encode("utf-8")))
        self._position = QPointF(x, y)
        self.accepted = False

    def mimeData(self) -> QMimeData:
        return self._mime_data

    def position(self) -> QPointF:
        return self._position

    def acceptProposedAction(self) -> None:
        self.accepted = True
