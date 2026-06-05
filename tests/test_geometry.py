"""Tests for geometry helpers and snap behavior."""

from PyQt6.QtCore import QByteArray, QEvent, QMimeData, QPointF, Qt
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication, QAbstractItemView, QDialogButtonBox, QGraphicsView, QMenu

from controllers.camera_data_manager import CameraDataManager
from models.camera_data_model import Camera
from models.canvas_layer_model import CanvasLayer
from models.device_link_model import DeviceLink
from models.device_catalog import DEVICE_KIND_PC, DEVICE_KIND_SERVER, DEVICE_KIND_SWITCH
from models.drawing_shape_model import DrawingShape
from utils.geometry import snap_to_grid
from utils.image_assets import CAMERA_PHOTO_MAX_EDGE, import_camera_location_image, import_image_asset
from config.i18n import set_language
from views.camera_location_image_dialog import CameraLocationImageDialog
from views.camera_view_item import CameraItem
from views.camera_view_dialog import CameraPropertiesDialog
from views.device_connections_dialog import DeviceConnectionsDialog
from views.layer_state import BACKGROUND_LAYER, GRID_LAYER
from views.layers_panel import ROLE_ID, ROLE_LAYER_ID, ROLE_OBJECT_TYPE, ROLE_TYPE, LayersPanel
from views.map_drawing_tools import (
    DrawingMode,
    TransformableImageItem,
    TransformablePolygonItem,
    TransformableRectItem,
    TransformableTextItem,
)
from views.map_view_canvas import MapCanvas
from views.tool_icons import device_icon, tool_icon
from views.ui_theme import CANVAS_BG_DARK, CANVAS_BG_LIGHT


def test_snap_to_grid_rounds_to_nearest_intersection() -> None:
    assert snap_to_grid(23.4, 47.9, 20) == (20.0, 40.0)
    assert snap_to_grid(31.0, 49.0, 20) == (40.0, 40.0)


def test_canvas_does_not_snap_camera_items_by_default() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.grid_size = 20
    item = canvas.add_camera_item(Camera("cam_test", "Lobby", "10.0.0.10"))

    item.setPos(23.4, 47.9)

    assert item.pos().x() == 23.4
    assert item.pos().y() == 47.9
    assert item.camera.position_x == 23.4
    assert item.camera.position_y == 47.9
    app.processEvents()


def test_canvas_snaps_camera_items_when_ctrl_is_held(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.grid_size = 20
    item = canvas.add_camera_item(Camera("cam_test", "Lobby", "10.0.0.10"))
    monkeypatch.setattr("views.map_canvas_actions.QApplication.keyboardModifiers", lambda: Qt.KeyboardModifier.ControlModifier)

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
    assert shape.points == [0.0, 0.0, 41.0, 79.0, 0.0]
    app.processEvents()


def test_canvas_defaults_to_pan_mode() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()

    assert canvas.drawing_mode == DrawingMode.PAN
    assert canvas.dragMode() == QGraphicsView.DragMode.ScrollHandDrag
    app.processEvents()


def test_canvas_snaps_drawing_points_only_when_ctrl_is_held(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.grid_size = 20
    canvas.set_drawing_mode(DrawingMode.RECTANGLE)
    monkeypatch.setattr("views.map_canvas_actions.QApplication.keyboardModifiers", lambda: Qt.KeyboardModifier.ControlModifier)

    shape = canvas._shape_from_points(canvas.mapToScene(0, 0), canvas.mapToScene(41, 79))

    assert shape is not None
    assert shape.points == [0.0, 0.0, 40.0, 80.0, 0.0]
    app.processEvents()


def test_freehand_uses_real_points_unless_ctrl_is_held(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.grid_size = 20

    shape = canvas.drawing_tool.freehand_shape([QPointF(1.0, 1.0), QPointF(21.0, 19.0)], "#ef4444")
    assert shape is not None
    assert shape.points == [1.0, 1.0, 21.0, 19.0]

    monkeypatch.setattr("views.map_canvas_actions.QApplication.keyboardModifiers", lambda: Qt.KeyboardModifier.ControlModifier)
    snapped = canvas.drawing_tool.freehand_shape([QPointF(1.0, 1.0), QPointF(21.0, 19.0)], "#ef4444")
    assert snapped is not None
    assert snapped.points == [0.0, 0.0, 20.0, 20.0]
    app.processEvents()


def test_canvas_creates_basic_shape_modes() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    modes = [
        (DrawingMode.ROUNDED_RECTANGLE, "RoundedRectangle"),
        (DrawingMode.ELLIPSE, "Ellipse"),
        (DrawingMode.TRIANGLE, "Triangle"),
    ]

    for mode, shape_type in modes:
        canvas.set_drawing_mode(mode)
        shape = canvas._shape_from_points(QPointF(0, 0), QPointF(40, 30))
        assert shape is not None
        assert shape.shape_type == shape_type

    app.processEvents()


def test_select_mode_uses_rubber_band_drag() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()

    canvas.set_drawing_mode(DrawingMode.SELECT)

    assert canvas.dragMode() == QGraphicsView.DragMode.RubberBandDrag
    assert canvas.rubberBandSelectionMode() == Qt.ItemSelectionMode.IntersectsItemShape
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

    item.mousePressEvent(_ItemMouseEvent(Qt.MouseButton.LeftButton, QPointF(50, 50), QPointF(100, 100)))
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
    assert canvas.scene.sceneRect().width() == 4000
    assert canvas.scene.sceneRect().height() == 3000
    assert camera.scene() is canvas.scene
    assert shape_item is not None
    assert shape_item.scene() is canvas.scene

    canvas.unload_background_image()
    assert canvas.background_item is None
    assert camera.scene() is canvas.scene
    assert shape_item.scene() is canvas.scene
    assert canvas.grid_items
    assert canvas.scene.sceneRect().width() == 4000
    assert canvas.scene.sceneRect().height() == 3000
    app.processEvents()


def test_background_position_expands_canvas_without_locking_to_image(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.resize_canvas(1200, 900)
    canvas.background_x = 200.0
    canvas.background_y = 150.0
    image_path = tmp_path / "offset_map.png"
    image = QImage(100, 80, QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    assert image.save(str(image_path))

    assert canvas.load_background_image(str(image_path), 1200, 900)

    assert canvas.background_item is not None
    assert canvas.background_item.pos() == QPointF(200.0, 150.0)
    assert canvas.scene.sceneRect().width() == 1200
    assert canvas.scene.sceneRect().height() == 900

    canvas.set_background_position(1300.0, 950.0)

    assert canvas.scene.sceneRect().width() == 1400
    assert canvas.scene.sceneRect().height() == 1030
    app.processEvents()


def test_move_background_mode_drags_and_escape_rolls_back(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.resize_canvas(300, 200)
    image_path = tmp_path / "move_map.png"
    image = QImage(100, 80, QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    assert image.save(str(image_path))
    assert canvas.load_background_image(str(image_path), 300, 200)
    changed = []
    canvas.background_position_changed.connect(lambda x, y: changed.append((x, y)))

    canvas.set_drawing_mode(DrawingMode.MOVE_BACKGROUND)
    start_view = canvas.mapFromScene(QPointF(10, 10))
    end_view = canvas.mapFromScene(QPointF(40, 50))
    canvas.mousePressEvent(_MouseEvent(Qt.MouseButton.LeftButton, start_view.x(), start_view.y()))
    canvas.mouseMoveEvent(_MouseEvent(Qt.MouseButton.LeftButton, end_view.x(), end_view.y()))
    canvas.mouseReleaseEvent(_MouseEvent(Qt.MouseButton.LeftButton, end_view.x(), end_view.y()))

    assert changed
    assert canvas.background_item is not None
    assert canvas.background_item.pos().x() > 0
    assert canvas.background_item.pos().y() > 0

    moved_x = canvas.background_x
    moved_y = canvas.background_y
    start_view = canvas.mapFromScene(QPointF(moved_x + 10, moved_y + 10))
    end_view = canvas.mapFromScene(QPointF(moved_x + 80, moved_y + 90))
    canvas.mousePressEvent(_MouseEvent(Qt.MouseButton.LeftButton, start_view.x(), start_view.y()))
    canvas.mouseMoveEvent(_MouseEvent(Qt.MouseButton.LeftButton, end_view.x(), end_view.y()))
    canvas.keyPressEvent(_KeyEvent(Qt.Key.Key_Escape))

    assert canvas.background_x == moved_x
    assert canvas.background_y == moved_y
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
    assert created[0].points == [0.0, 0.0, 41.0, 79.0]
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

    dialog.ip_input.setText("")
    assert save_button.isEnabled()
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

    assert canvas.device_link_items == []

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
    canvas.camera_items["switch"].setSelected(True)
    assert {(item.link.source_device_id, item.link.target_device_id) for item in canvas.device_link_items} == {
        ("cam", "ap"),
        ("ap", "switch"),
        ("pc", "switch"),
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

    canvas.scene.clearSelection()
    canvas.camera_items["cam"].setSelected(True)
    canvas.camera_items["pc"].setSelected(True)
    assert canvas.device_link_items == []
    app.processEvents()


def test_camera_item_parent_ip_stays_tooltip_only() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    cam = Camera("cam", "Camera", "10.0.0.10")
    ap = Camera("ap", "AP", "10.0.0.2", device_kind="AP", ping_enabled=False)
    switch = Camera("switch", "Switch", "10.0.0.1", device_kind=DEVICE_KIND_SWITCH, ping_enabled=False)
    for device in (cam, ap, switch):
        canvas.add_camera_item(device)
    canvas.set_device_links(
        [
            DeviceLink("link_cam_ap", "default", "cam", "ap"),
            DeviceLink("link_ap_switch", "default", "ap", "switch"),
        ]
    )

    item = canvas.camera_items["cam"]
    item.set_info_visibility({"name": False, "zone": False, "ip": False, "dvr": True})

    assert item._visible_info_lines() == []
    assert "10.0.0.2" in item.toolTip()
    assert "10.0.0.1" not in item._visible_info_lines()
    app.processEvents()


def test_camera_fov_fill_alpha_and_color_are_red() -> None:
    item = CameraItem(Camera("cam_test", "Lobby", "10.0.0.10"))

    default_fill = item._fov_fill_color(False)
    selected_fill = item._fov_fill_color(True)
    default_pen = item._fov_pen_color(False)
    selected_pen = item._fov_pen_color(True)

    assert default_fill.alpha() < selected_fill.alpha()
    assert default_pen.alpha() < selected_pen.alpha()
    for color in (default_fill, selected_fill):
        assert color.red() > color.green()
        assert color.red() > color.blue()
        assert color.green() == color.blue()


def test_camera_fov_is_not_in_hit_shape_and_non_camera_resize_only() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.set_drawing_mode(DrawingMode.SELECT)
    camera_item = canvas.add_camera_item(Camera("cam_test", "Lobby", "10.0.0.10"))
    server_item = canvas.add_camera_item(
        Camera("server_test", "Server", "", device_kind=DEVICE_KIND_SERVER, ping_enabled=False)
    )

    camera_item.setSelected(True)
    assert not camera_item.shape().contains(QPointF(120.0, 0.0))

    server_item.setSelected(True)
    server_item.mousePressEvent(_ItemMouseEvent(Qt.MouseButton.LeftButton, QPointF(46, 0)))
    assert not server_item.is_rotating
    server_item.mousePressEvent(_ItemMouseEvent(Qt.MouseButton.LeftButton, QPointF(34, 28), QPointF(100, 100)))
    assert server_item.is_resizing
    app.processEvents()


def test_device_dialog_uses_device_name_label_and_preserves_rotation() -> None:
    app = QApplication.instance() or QApplication([])
    dialog = CameraPropertiesDialog(Camera("cam", "Lobby", "10.0.0.10", rotation=123.0))

    assert dialog.name_label.text() == "Tên thiết bị"
    assert not hasattr(dialog, "rotation_slider")
    assert not hasattr(dialog, "dvr_input")
    assert not hasattr(dialog, "status_input")
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


def test_device_dialog_blank_ip_disables_ping_and_camera_stays_blank() -> None:
    app = QApplication.instance() or QApplication([])
    dialog = CameraPropertiesDialog(Camera("device", "Camera A", "", ping_enabled=False))

    assert dialog.ip_input.text() == ""
    assert dialog.ping_input.isChecked() is False
    assert dialog.button_box.button(QDialogButtonBox.StandardButton.Save).isEnabled()

    dialog.ip_input.setText("10.0.0.10")
    dialog.ping_input.setChecked(True)
    dialog.ip_input.setText("")

    assert dialog.ping_input.isChecked() is False
    assert dialog.get_camera().status is False
    app.processEvents()


def test_device_dialog_link_search_preserves_checked_and_shows_incoming() -> None:
    app = QApplication.instance() or QApplication([])
    ap = Camera("ap", "AP 1", "", device_kind="AP", variant="Indoor AP", ping_enabled=False)
    server = Camera("server", "Server A", "", device_kind=DEVICE_KIND_SERVER, variant="Rack", ping_enabled=False)
    camera_a = Camera("cam_a", "Camera A", "10.0.0.10")
    camera_b = Camera("cam_b", "Camera B", "10.0.0.11")
    properties = CameraPropertiesDialog(ap, None, [ap, server, camera_a, camera_b], ["server"], ["cam_a", "cam_b"])
    dialog = DeviceConnectionsDialog(
        ap,
        [server, camera_a, camera_b],
        set(properties.get_linked_device_ids()),
        {"cam_a", "cam_b"},
        lambda device_id: "10.10.10.1" if device_id == "cam_a" else "",
    )

    assert not hasattr(properties, "link_list")
    assert not hasattr(properties, "incoming_link_list")
    assert properties.manage_connections_button.text() == "Quản lý kết nối"
    assert dialog.get_linked_device_ids() == ["server"]
    assert dialog.incoming_list.count() == 2

    dialog.search_input.setText("camera a")
    assert dialog.incoming_list.item(0).isHidden() is False
    assert dialog.incoming_list.item(1).isHidden() is True

    dialog.search_input.setText("10.10.10.1")
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

    for index in range(dialog.incoming_list.count()):
        item = dialog.incoming_list.item(index)
        if item.data(Qt.ItemDataRole.UserRole) == "cam_b":
            item.setCheckState(Qt.CheckState.Unchecked)
    assert dialog.get_removed_incoming_device_ids() == ["cam_b"]
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
    image = QImage(2400, 2000, QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    assert image.save(str(source))

    imported = import_camera_location_image(str(source), target_dir)

    assert imported is not None
    path, width, height = imported
    assert path.endswith(".jpg")
    assert height == CAMERA_PHOTO_MAX_EDGE
    assert width == 1728
    assert QImage(path).height() == CAMERA_PHOTO_MAX_EDGE
    app.processEvents()


def test_import_image_asset_accepts_jpg_and_caps_height(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    source = tmp_path / "source.jpg"
    target_dir = tmp_path / "assets"
    image = QImage(2400, 2000, QImage.Format.Format_RGB32)
    image.fill(0xFFFFFFFF)
    assert image.save(str(source), "JPG")

    imported = import_image_asset(str(source), target_dir)

    assert imported is not None
    path, width, height = imported
    assert path.endswith(".jpg")
    assert width == 1728
    assert height == 1440
    assert QImage(path).height() == 1440
    app.processEvents()


def test_import_image_asset_keeps_smaller_image_size(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    source = tmp_path / "source.bmp"
    target_dir = tmp_path / "assets"
    image = QImage(2400, 1200, QImage.Format.Format_RGB32)
    image.fill(0xFFFFFFFF)
    assert image.save(str(source), "BMP")

    imported = import_image_asset(str(source), target_dir)

    assert imported is not None
    path, width, height = imported
    assert path.endswith(".bmp")
    assert (width, height) == (2400, 1200)
    assert QImage(path).height() == 1200
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

    assert captured == ["Ảnh vị trí", "Ping", "Chỉnh sửa thông số", "", "Gỡ khỏi canvas"]
    app.processEvents()


def test_camera_context_remove_action_uses_remove_callback(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    item = CameraItem(Camera("cam_test", "Lobby", "10.0.0.10"))
    removed = []
    item.set_remove_callback(removed.append)

    def trigger_remove(menu: QMenu, _pos: object) -> None:
        for action in menu.actions():
            if action.text() == "Gỡ khỏi canvas":
                action.trigger()
                return

    monkeypatch.setattr(QMenu, "exec", trigger_remove)
    item.contextMenuEvent(_ContextMenuEvent())

    assert removed == ["cam_test"]
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
    assert item._is_on_resize_handle(QPointF(50, 50))
    assert item._is_on_resize_handle(QPointF(63, 63))
    assert not item._is_on_resize_handle(QPointF(34, 28))

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


def test_camera_item_bounds_cover_selected_fov_and_handles_without_fov_hitbox() -> None:
    app = QApplication.instance() or QApplication([])
    item = CameraItem(Camera("cam_test", "Lobby", "10.0.0.10"))

    bounds = item.boundingRect()

    assert bounds.contains(QPointF(-153.0, 0.0))
    assert bounds.contains(QPointF(153.0, 0.0))
    assert bounds.contains(QPointF(0.0, -153.0))
    assert bounds.contains(QPointF(0.0, 153.0))
    assert bounds.contains(item._resize_handle_hit_rect().bottomRight())
    assert bounds.contains(QPointF(51.0, 0.0))
    assert bounds.contains(QPointF(32.0, -28.0))
    assert bounds.contains(QPointF(58.0, 60.0))

    item.setSelected(True)
    assert not item.shape().contains(QPointF(120.0, 0.0))
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


def test_canvas_grid_toggle_keeps_edit_area_boundary_visible() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()

    assert canvas.canvas_bounds_item is not None
    assert canvas.backgroundBrush().color().name() == CANVAS_BG_DARK
    canvas.set_grid_visible(False)

    assert all(not item.isVisible() for item in canvas.grid_items)
    assert canvas.canvas_bounds_item is not None
    assert canvas.canvas_bounds_item.isVisible()
    dark_pen = canvas.canvas_bounds_item.pen().color().name()
    canvas.set_light_theme(True)
    light_pen = canvas.canvas_bounds_item.pen().color().name()
    assert canvas.backgroundBrush().color().name() == CANVAS_BG_LIGHT
    assert dark_pen != light_pen
    app.processEvents()


def test_canvas_insert_image_fits_large_image_inside_canvas(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.resize_canvas(100, 100)
    image_path = tmp_path / "large.png"
    image = QImage(200, 50, QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    assert image.save(str(image_path))

    shape = canvas.add_image_annotation(str(image_path), 200, 50)

    assert shape.points[2] == 100.0
    assert shape.points[3] == 25.0
    assert shape.points[0] >= 0
    assert shape.points[0] + shape.points[2] <= 100
    app.processEvents()


def test_text_and_image_shapes_persist_rotation_points(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    image_path = tmp_path / "item.png"
    image = QImage(40, 20, QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    assert image.save(str(image_path))

    text_item = canvas.add_drawing_shape(DrawingShape("text_rot", "Text", [1.0, 2.0, 33.0], label="Hello"))
    image_item = canvas.add_drawing_shape(
        DrawingShape("image_rot", "Image", [3.0, 4.0, 40.0, 20.0, 45.0], image_path=str(image_path))
    )

    assert isinstance(text_item, TransformableTextItem)
    assert isinstance(image_item, TransformableImageItem)
    assert text_item.rotation() == 33.0
    assert image_item.rotation() == 45.0
    assert canvas._drawing_shape_from_item(text_item).points == [1.0, 2.0, 33.0]
    assert canvas._drawing_shape_from_item(image_item).points == [3.0, 4.0, 40.0, 20.0, 45.0]
    app.processEvents()


def test_shape_items_resize_and_persist_rotation_points() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    rect_item = canvas.add_drawing_shape(DrawingShape("rect_rot", "RoundedRectangle", [0.0, 0.0, 80.0, 40.0, 25.0]))
    zone_item = canvas.add_drawing_shape(
        DrawingShape("zone_resize", "Polygon", [0.0, 0.0, 80.0, 0.0, 80.0, 40.0, 0.0, 40.0])
    )

    assert isinstance(rect_item, TransformableRectItem)
    assert isinstance(zone_item, TransformablePolygonItem)
    assert rect_item.rotation() == 25.0
    rect_item._set_content_rect(rect_item.rect().adjusted(0.0, 0.0, 20.0, 20.0))
    zone_item.resize_start_rect = zone_item._content_rect()
    zone_item.resize_start_polygon = zone_item.polygon()
    zone_item._set_content_rect(zone_item._content_rect().adjusted(0.0, 0.0, 20.0, 20.0))

    rect_shape = canvas._drawing_shape_from_item(rect_item)
    zone_shape = canvas._drawing_shape_from_item(zone_item)

    assert rect_shape.shape_type == "RoundedRectangle"
    assert rect_shape.points == [0.0, 0.0, 100.0, 60.0, 25.0]
    assert zone_shape.shape_type == "Polygon"
    assert max(zone_shape.points) == 100.0
    app.processEvents()


def test_closed_shapes_render_and_persist_fill_color() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.set_drawing_fill_color("#00ff00")
    canvas.set_drawing_mode(DrawingMode.RECTANGLE)

    shape = canvas._shape_from_points(QPointF(0, 0), QPointF(40, 30))
    assert shape is not None
    assert shape.fill_color == "#00ff00"
    item = canvas.add_drawing_shape(shape)
    assert item is not None
    assert item.brush().color().name() == "#00ff00"
    assert canvas._drawing_shape_from_item(item).fill_color == "#00ff00"

    canvas.clear_drawing_fill_color()
    no_fill = canvas.drawing_tool.item_from_shape(DrawingShape("legacy", "Ellipse", [0, 0, 20, 20]))
    assert no_fill is not None
    assert no_fill.brush().style() == Qt.BrushStyle.NoBrush
    app.processEvents()


def test_canvas_selection_priority_uses_layer_and_object_z_order() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    lower_layer = canvas.canvas_layers[0]
    upper_layer = CanvasLayer("layer_default_2", "default", "Layer 2", 1)
    canvas.set_canvas_layers([lower_layer, upper_layer], "default")
    lower = canvas.add_drawing_shape(
        DrawingShape("lower", "Rectangle", [0.0, 0.0, 50.0, 50.0], layer_id=lower_layer.id, z_index=99)
    )
    lower_sibling = canvas.add_drawing_shape(
        DrawingShape("lower_sibling", "Rectangle", [0.0, 0.0, 50.0, 50.0], layer_id=lower_layer.id, z_index=0)
    )
    upper = canvas.add_drawing_shape(
        DrawingShape("upper", "Rectangle", [0.0, 0.0, 50.0, 50.0], layer_id=upper_layer.id, z_index=0)
    )
    assert lower is not None
    assert lower_sibling is not None
    assert upper is not None
    canvas.set_drawing_mode(DrawingMode.SELECT)

    selected = canvas.top_selectable_item_at(canvas.mapFromScene(QPointF(1.0, 10.0)))

    assert selected is upper
    assert canvas.move_layer_object("drawing", "lower_sibling", 1)
    assert int(lower_sibling.data(7) or 0) == 1
    assert int(lower.data(7) or 0) == 0
    app.processEvents()


def test_layers_panel_object_up_down_keeps_current_object() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    manager = CameraDataManager(":memory:")
    panel = LayersPanel(canvas, manager, lambda: "default")
    layer_id = canvas.active_layer_id
    canvas.add_drawing_shape(DrawingShape("obj_a", "Line", [0.0, 0.0, 10.0, 10.0], z_index=0))
    canvas.add_drawing_shape(DrawingShape("obj_b", "Line", [0.0, 10.0, 10.0, 20.0], z_index=1))
    canvas.add_drawing_shape(DrawingShape("obj_c", "Line", [0.0, 20.0, 10.0, 30.0], z_index=2))
    panel.refresh()
    item = panel._find_object_tree_item("drawing", "obj_a")
    assert item is not None
    panel.tree.setCurrentItem(item)
    item.setSelected(True)
    before_layer_order = list(canvas.annotation_layer_order)

    panel._move_selected_index(1)
    panel._move_selected_index(1)

    assert int(canvas._find_layer_object_item("drawing", "obj_a").data(7) or 0) == 2
    assert canvas.annotation_layer_order == before_layer_order
    assert panel.tree.currentItem() is not None
    assert panel.tree.currentItem().data(0, ROLE_TYPE) == "object"
    assert panel.tree.currentItem().data(0, ROLE_ID) == "obj_a"
    assert str(panel.tree.currentItem().data(0, ROLE_LAYER_ID)) == layer_id

    panel._move_selected_index(-1)
    panel._move_selected_index(1)

    assert panel.tree.currentItem() is not None
    assert panel.tree.currentItem().data(0, ROLE_TYPE) == "object"
    assert panel.tree.currentItem().data(0, ROLE_ID) == "obj_a"
    assert canvas.annotation_layer_order == before_layer_order
    app.processEvents()


def test_layers_panel_grouped_object_up_down_keeps_current_object() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    manager = CameraDataManager(":memory:")
    group = CanvasLayer("group_default_1", "default", "Group 1", 0, is_group=True)
    layer = CanvasLayer("layer_default_2", "default", "Layer 2", 1, group_id=group.id)
    canvas.set_canvas_layers([group, layer], "default")
    canvas.set_active_layer(layer.id)
    panel = LayersPanel(canvas, manager, lambda: "default")
    canvas.add_drawing_shape(DrawingShape("obj_a", "Line", [0.0, 0.0, 10.0, 10.0], layer_id=layer.id, z_index=0))
    canvas.add_drawing_shape(DrawingShape("obj_b", "Line", [0.0, 10.0, 10.0, 20.0], layer_id=layer.id, z_index=1))
    canvas.add_drawing_shape(DrawingShape("obj_c", "Line", [0.0, 20.0, 10.0, 30.0], layer_id=layer.id, z_index=2))
    panel.refresh()
    item = panel._find_object_tree_item("drawing", "obj_a")
    assert item is not None
    panel.tree.setCurrentItem(item)
    item.setSelected(True)

    panel._move_selected_index(1)
    panel._move_selected_index(1)

    assert int(canvas._find_layer_object_item("drawing", "obj_a").data(7) or 0) == 2
    assert panel.tree.currentItem() is not None
    assert panel.tree.currentItem().data(0, ROLE_TYPE) == "object"
    assert panel.tree.currentItem().data(0, ROLE_ID) == "obj_a"
    app.processEvents()


def test_layers_panel_multi_select_selects_all_objects_on_canvas() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    manager = CameraDataManager(":memory:")
    panel = LayersPanel(canvas, manager, lambda: "default")
    canvas.add_drawing_shape(DrawingShape("obj_a", "Line", [0.0, 0.0, 10.0, 10.0], z_index=0))
    canvas.add_drawing_shape(DrawingShape("obj_b", "Line", [0.0, 10.0, 10.0, 20.0], z_index=1))
    panel.refresh()
    item_a = panel._find_object_tree_item("drawing", "obj_a")
    item_b = panel._find_object_tree_item("drawing", "obj_b")
    assert item_a is not None
    assert item_b is not None

    item_a.setSelected(True)
    item_b.setSelected(True)
    panel._handle_selection()

    selected_ids = {str(item.data(0)) for item in canvas.scene.selectedItems() if item.data(1) == "drawing"}
    assert selected_ids == {"obj_a", "obj_b"}
    app.processEvents()


def test_layers_panel_delete_unplaces_camera_and_deletes_drawing_object() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    manager = CameraDataManager(":memory:")
    panel = LayersPanel(canvas, manager, lambda: "default")
    deleted_cameras = []
    deleted_drawings = []
    canvas.camera_deleted.connect(deleted_cameras.append)
    canvas.drawing_deleted.connect(deleted_drawings.append)
    canvas.set_drawing_mode(DrawingMode.SELECT)
    canvas.add_camera_item(Camera("cam_layer", "Layer Camera", "10.0.0.10"))
    canvas.add_drawing_shape(DrawingShape("obj_layer", "Line", [0.0, 0.0, 10.0, 10.0]))
    panel.refresh()
    camera_item = panel._find_object_tree_item("camera", "cam_layer")
    drawing_item = panel._find_object_tree_item("drawing", "obj_layer")
    assert camera_item is not None
    assert drawing_item is not None

    panel.tree.setCurrentItem(camera_item)
    camera_item.setSelected(True)
    drawing_item.setSelected(True)
    panel._delete_selected()

    assert deleted_cameras == ["cam_layer"]
    assert deleted_drawings == ["obj_layer"]
    assert "cam_layer" not in canvas.camera_items
    assert canvas._find_layer_object_item("drawing", "obj_layer") is None
    app.processEvents()


def test_layers_tree_drop_reorders_object_to_exact_index(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    manager = CameraDataManager(":memory:")
    panel = LayersPanel(canvas, manager, lambda: "default")
    canvas.add_drawing_shape(DrawingShape("obj_a", "Line", [0.0, 0.0, 10.0, 10.0], z_index=0))
    canvas.add_drawing_shape(DrawingShape("obj_b", "Line", [0.0, 10.0, 10.0, 20.0], z_index=1))
    canvas.add_drawing_shape(DrawingShape("obj_c", "Line", [0.0, 20.0, 10.0, 30.0], z_index=2))
    panel.refresh()
    source = panel._find_object_tree_item("drawing", "obj_a")
    target = panel._find_object_tree_item("drawing", "obj_c")
    assert source is not None
    assert target is not None
    panel.tree.setCurrentItem(source)
    monkeypatch.setattr(panel.tree, "itemAt", lambda _point: target)
    monkeypatch.setattr(
        panel.tree,
        "dropIndicatorPosition",
        lambda: QAbstractItemView.DropIndicatorPosition.BelowItem,
    )

    event = _LayerDropEvent()
    panel.tree.dropEvent(event)

    assert event.accepted
    assert event.drop_action == Qt.DropAction.CopyAction
    assert int(canvas._find_layer_object_item("drawing", "obj_a").data(7) or 0) == 1
    assert int(canvas._find_layer_object_item("drawing", "obj_b").data(7) or 0) == 0
    assert int(canvas._find_layer_object_item("drawing", "obj_c").data(7) or 0) == 2

    panel.refresh()
    source = panel._find_object_tree_item("drawing", "obj_a")
    target = panel._find_object_tree_item("drawing", "obj_c")
    assert source is not None
    assert target is not None
    panel.tree.setCurrentItem(source)
    monkeypatch.setattr(panel.tree, "itemAt", lambda _point: target)
    monkeypatch.setattr(
        panel.tree,
        "dropIndicatorPosition",
        lambda: QAbstractItemView.DropIndicatorPosition.AboveItem,
    )

    event = _LayerDropEvent()
    panel.tree.dropEvent(event)

    assert event.accepted
    assert event.drop_action == Qt.DropAction.CopyAction
    assert int(canvas._find_layer_object_item("drawing", "obj_a").data(7) or 0) == 2
    assert int(canvas._find_layer_object_item("drawing", "obj_c").data(7) or 0) == 1
    app.processEvents()


def test_layers_tree_drop_moves_to_layer_and_ignores_invalid_targets(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    manager = CameraDataManager(":memory:")
    source_layer = canvas.canvas_layers[0]
    group = CanvasLayer("group_default_1", "default", "Group 1", 1, is_group=True)
    target_layer = CanvasLayer("layer_default_2", "default", "Layer 2", 2)
    canvas.set_canvas_layers([source_layer, group, target_layer], "default")
    canvas.add_drawing_shape(DrawingShape("obj_a", "Line", [0.0, 0.0, 10.0, 10.0], layer_id=source_layer.id))
    panel = LayersPanel(canvas, manager, lambda: "default")
    panel.refresh()
    source = panel._find_object_tree_item("drawing", "obj_a")
    assert source is not None
    panel.tree.setCurrentItem(source)
    target = next(
        item
        for item in _layer_tree_items(panel)
        if item.data(0, ROLE_TYPE) == "layer" and item.data(0, ROLE_LAYER_ID) == target_layer.id
    )
    monkeypatch.setattr(panel.tree, "itemAt", lambda _point: target)

    event = _LayerDropEvent()
    panel.tree.dropEvent(event)

    assert event.accepted
    assert event.drop_action == Qt.DropAction.CopyAction
    assert canvas._find_layer_object_item("drawing", "obj_a").data(2) == target_layer.id

    panel.refresh()
    source = panel._find_object_tree_item("drawing", "obj_a")
    assert source is not None
    panel.tree.setCurrentItem(source)
    group_target = next(item for item in _layer_tree_items(panel) if item.data(0, ROLE_TYPE) == "group")
    monkeypatch.setattr(panel.tree, "itemAt", lambda _point: group_target)

    ignored = _LayerDropEvent()
    panel.tree.dropEvent(ignored)

    assert ignored.ignored
    assert canvas._find_layer_object_item("drawing", "obj_a").data(2) == target_layer.id
    app.processEvents()


def test_layers_tree_drop_object_onto_itself_is_ignored(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    manager = CameraDataManager(":memory:")
    panel = LayersPanel(canvas, manager, lambda: "default")
    canvas.add_drawing_shape(DrawingShape("obj_a", "Line", [0.0, 0.0, 10.0, 10.0], z_index=0))
    panel.refresh()
    source = panel._find_object_tree_item("drawing", "obj_a")
    assert source is not None
    panel.tree.setCurrentItem(source)
    monkeypatch.setattr(panel.tree, "itemAt", lambda _point: source)

    event = _LayerDropEvent()
    panel.tree.dropEvent(event)

    assert event.ignored
    assert int(canvas._find_layer_object_item("drawing", "obj_a").data(7) or 0) == 0
    app.processEvents()


class _ScrollBar:
    def __init__(self) -> None:
        self._value = 50

    def singleStep(self) -> int:
        return 10

    def value(self) -> int:
        return self._value

    def setValue(self, value: int) -> None:
        self._value = value


def test_layers_tree_wheel_scrolls_while_dragging(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    manager = CameraDataManager(":memory:")
    panel = LayersPanel(canvas, manager, lambda: "default")
    scroll_bar = _ScrollBar()
    monkeypatch.setattr(panel.tree, "verticalScrollBar", lambda: scroll_bar)
    panel.tree._drag_in_progress = True

    down_event = _WheelEvent(-120)
    panel.tree.wheelEvent(down_event)

    assert down_event.accepted is True
    assert scroll_bar.value() == 60

    up_event = _WheelEvent(120)
    panel.tree.wheelEvent(up_event)

    assert up_event.accepted is True
    assert scroll_bar.value() == 50
    panel.tree._drag_in_progress = False
    app.processEvents()


def test_layers_tree_event_filter_scrolls_wheel_while_dragging(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    manager = CameraDataManager(":memory:")
    panel = LayersPanel(canvas, manager, lambda: "default")
    scroll_bar = _ScrollBar()
    monkeypatch.setattr(panel.tree, "verticalScrollBar", lambda: scroll_bar)
    panel.tree._drag_in_progress = True

    event = _DragWheelEvent(-120)
    handled = panel.tree.eventFilter(panel.tree.viewport(), event)

    assert handled is True
    assert event.accepted is True
    assert scroll_bar.value() == 60
    panel.tree._drag_in_progress = False
    app.processEvents()


def _layer_tree_items(panel: LayersPanel):
    for index in range(panel.tree.topLevelItemCount()):
        yield from _layer_tree_branch(panel.tree.topLevelItem(index))


def _layer_tree_branch(item):
    yield item
    for child_index in range(item.childCount()):
        yield from _layer_tree_branch(item.child(child_index))


def test_canvas_object_visibility_hides_single_object_and_blocks_selection(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.resize_canvas(80, 60)
    visible_item = canvas.add_drawing_shape(DrawingShape("visible", "Line", [0.0, 0.0, 80.0, 60.0], color="#ffffff"))
    hidden_item = canvas.add_drawing_shape(
        DrawingShape("hidden", "Rectangle", [0.0, 0.0, 80.0, 60.0], fill_color="#ff0000")
    )
    assert visible_item is not None
    assert hidden_item is not None

    assert canvas.set_layer_object_visible("drawing", "hidden", False)

    assert not hidden_item.isVisible()
    assert visible_item.isVisible()
    assert canvas.layer_visibility[canvas.active_layer_id] is True
    assert canvas.select_layer_object("drawing", "hidden") is False
    states = {state.object_id: state.visible for state in canvas.get_layer_object_states(canvas.active_layer_id)}
    assert states["hidden"] is False
    target = tmp_path / "object_visibility_snapshot.png"
    assert canvas.export_snapshot(str(target))
    exported = QImage(str(target))
    assert exported.pixelColor(10, 10).name() != "#ff0000"
    app.processEvents()


def test_escape_cancels_text_and_image_transform(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.set_drawing_mode(DrawingMode.SELECT)
    image_path = tmp_path / "item.png"
    image = QImage(40, 20, QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    assert image.save(str(image_path))
    text_item = canvas.add_drawing_shape(DrawingShape("text_rot", "Text", [1.0, 2.0, 10.0], label="Hello"))
    image_item = canvas.add_drawing_shape(
        DrawingShape("image_size", "Image", [3.0, 4.0, 40.0, 20.0, 0.0], image_path=str(image_path))
    )
    assert isinstance(text_item, TransformableTextItem)
    assert isinstance(image_item, TransformableImageItem)

    text_item.is_rotating = True
    text_item.rotation_start_value = 10.0
    text_item.setRotation(80.0)
    image_item.is_resizing = True
    image_item.resize_start_size = (40.0, 20.0)
    image_item._set_display_size(80.0, 40.0)

    canvas.keyPressEvent(_KeyEvent(Qt.Key.Key_Escape))

    assert text_item.rotation() == 10.0
    assert not text_item.is_rotating
    assert image_item.pixmap().width() == 40
    assert image_item.pixmap().height() == 20
    assert not image_item.is_resizing
    app.processEvents()


def test_rotated_image_resize_uses_stable_start_local_space(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.set_drawing_mode(DrawingMode.SELECT)
    image_path = tmp_path / "rotated_image.png"
    image = QImage(40, 20, QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    assert image.save(str(image_path))
    image_item = canvas.add_drawing_shape(
        DrawingShape("image_rot_resize", "Image", [10.0, 10.0, 40.0, 20.0, 45.0], image_path=str(image_path))
    )
    assert isinstance(image_item, TransformableImageItem)
    image_item.setSelected(True)
    start_handle = image_item._resize_handle_rect("e").center()
    start_scene = image_item.mapToScene(start_handle)
    end_scene = image_item.mapToScene(QPointF(start_handle.x() + 30.0, start_handle.y()))

    image_item.mousePressEvent(_ItemMouseEvent(Qt.MouseButton.LeftButton, start_handle, start_scene))
    image_item.mouseMoveEvent(_ItemMouseEvent(Qt.MouseButton.LeftButton, QPointF(start_handle.x() + 30.0, start_handle.y()), end_scene))
    image_item.mouseReleaseEvent(_ItemMouseEvent(Qt.MouseButton.LeftButton, QPointF(start_handle.x() + 30.0, start_handle.y()), end_scene))
    shape = canvas._drawing_shape_from_item(image_item)

    assert image_item.rotation() == 45.0
    assert shape is not None
    assert shape.points[2] > 40.0
    assert shape.points[4] == 45.0
    app.processEvents()


def test_canvas_snapshot_exports_scene_without_hidden_layer_or_selection(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.resize_canvas(120, 80)
    visible_item = canvas.add_drawing_shape(DrawingShape("visible", "Line", [0.0, 0.0, 120.0, 80.0], color="#ffffff"))
    hidden_layer = CanvasLayer("layer_default_2", "default", "Layer 2", 1)
    canvas.set_canvas_layers([*canvas.canvas_layers, hidden_layer], "default")
    hidden_image_path = tmp_path / "hidden.png"
    hidden_image = QImage(120, 80, QImage.Format.Format_ARGB32)
    hidden_image.fill(0xFFFF0000)
    assert hidden_image.save(str(hidden_image_path))
    hidden_item = canvas.add_drawing_shape(
        DrawingShape("hidden", "Image", [0.0, 0.0, 120.0, 80.0], image_path=str(hidden_image_path), layer_id=hidden_layer.id)
    )
    assert visible_item is not None
    assert hidden_item is not None
    canvas.set_drawing_mode(DrawingMode.SELECT)
    visible_item.setSelected(True)
    canvas.set_layer_visible(hidden_layer.id, False)
    target = tmp_path / "snapshot.png"

    assert canvas.export_snapshot(str(target))
    exported = QImage(str(target))

    assert exported.width() == 120
    assert exported.height() == 80
    assert exported.pixelColor(10, 10).name() != "#ff0000"
    assert visible_item.isSelected()
    app.processEvents()


def test_canvas_snapshot_excludes_ui_background_and_restores_bounds(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.resize_canvas(24, 16)
    canvas.set_grid_visible(False)
    assert canvas.canvas_bounds_item is not None
    assert canvas.canvas_bounds_item.isVisible()
    target = tmp_path / "transparent_snapshot.png"

    assert canvas.export_snapshot(str(target))
    exported = QImage(str(target))

    assert exported.pixelColor(4, 4).alpha() == 0
    assert canvas.backgroundBrush().color().name() == CANVAS_BG_DARK
    assert canvas.canvas_bounds_item is not None
    assert canvas.canvas_bounds_item.isVisible()
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
    assert canvas.grid_size == 10
    assert canvas.scene.sceneRect().width() == 1200
    assert canvas.scene.sceneRect().height() == 900
    canvas.set_background_position(100.0, 50.0)
    canvas.set_background_scale(2.0)

    assert canvas.background_item is not None
    assert canvas.background_item.pos() == QPointF(100.0, 50.0)
    assert canvas.background_item.pixmap().width() == 200
    assert canvas.scene.sceneRect().width() == 1200
    assert canvas.scene.sceneRect().height() == 900
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


class _LayerDropEvent:
    def __init__(self) -> None:
        self.accepted = False
        self.ignored = False
        self.drop_action = None

    def position(self) -> QPointF:
        return QPointF(0, 0)

    def accept(self) -> None:
        self.accepted = True

    def ignore(self) -> None:
        self.ignored = True

    def setDropAction(self, action) -> None:
        self.drop_action = action


class _DragWheelEvent(_WheelEvent):
    def type(self):
        return QEvent.Type.Wheel
