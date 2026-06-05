"""Tests for the camera placement controller."""

from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtWidgets import QApplication, QMenu

from controllers.camera_data_manager import CameraDataManager
from controllers.camera_placement_controller import CameraPlacementController
from models.camera_data_model import Camera
from models.device_catalog import DEVICE_KIND_SERVER, DEVICE_KIND_SWITCH
from models.device_link_model import DeviceLink
from models.drawing_shape_model import DrawingShape
from views.app_camera_actions import AppCameraActions
from views.control_layout_panel import ControlLayoutPanel as CameraPanel, DeviceParentPickerDialog
from views.map_drawing_tools import DrawingMode
from views.map_view_canvas import MapCanvas
from views.ui_theme import GRID_DARK, GRID_LIGHT


def _create_default_layout(manager: CameraDataManager) -> None:
    manager.db.execute(
        "INSERT OR IGNORE INTO map_layouts (id, name, background_path) VALUES (?, ?, ?)",
        ("default", "Default Layout", ""),
    )


def _seed_default_devices(manager: CameraDataManager) -> None:
    _create_default_layout(manager)
    for index in range(1, 6):
        manager.add_camera(Camera(f"cam_{index:02}", f"Camera {index}", f"192.168.1.{100 + index}"))


def test_drop_camera_persists_position_and_moves_item_to_map() -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _seed_default_devices(manager)
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
    controller.load_cameras("default")

    panel.unplaced_button.click()
    assert _camera_count(panel) == 5

    controller.handle_camera_dropped("cam_01", 123.4, 567.8)

    saved = manager.get_camera("cam_01")
    assert saved is not None
    assert _camera_count(panel) == 4
    assert "cam_01" in canvas.camera_items
    assert saved.position_x == 123.4
    assert saved.position_y == 567.8

    app.processEvents()


def _camera_count(panel: CameraPanel) -> int:
    return sum(1 for item in _tree_items(panel) if item.data(0, Qt.ItemDataRole.UserRole + 1) == "camera")


def _tree_items(panel: CameraPanel):
    for group_index in range(panel.tree_widget.topLevelItemCount()):
        yield from _tree_item_branch(panel.tree_widget.topLevelItem(group_index))


def _tree_item_branch(item):
    yield item
    for child_index in range(item.childCount()):
        yield from _tree_item_branch(item.child(child_index))


def _camera_item(panel: CameraPanel, camera_id: str):
    return next(item for item in _tree_items(panel) if item.data(0, Qt.ItemDataRole.UserRole) == camera_id)


class _DropEvent:
    def __init__(self, mime_data) -> None:
        self._mime_data = mime_data
        self.accepted = False
        self.ignored = False
        self.drop_action = None

    def mimeData(self):
        return self._mime_data

    def position(self) -> QPointF:
        return QPointF(0, 0)

    def setDropAction(self, action) -> None:
        self.drop_action = action

    def accept(self) -> None:
        self.accepted = True
        self.ignored = False

    def ignore(self) -> None:
        self.ignored = True


class _WheelEvent:
    def __init__(self, delta: int, pixel_delta: int = 0) -> None:
        self._delta = delta
        self._pixel_delta = pixel_delta
        self.accepted = False

    def angleDelta(self) -> QPoint:
        return QPoint(0, self._delta)

    def pixelDelta(self) -> QPoint:
        return QPoint(0, self._pixel_delta)

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


class _DragWheelEvent(_WheelEvent):
    def type(self):
        return QEvent.Type.Wheel


class _StatusBar:
    def __init__(self) -> None:
        self.messages = []

    def showMessage(self, message: str, timeout: int = 0) -> None:
        self.messages.append((message, timeout))


class _ImportActionHost(AppCameraActions):
    def __init__(self, manager: CameraDataManager, panel: CameraPanel, canvas: MapCanvas) -> None:
        self.current_layout_id = "default"
        self.camera_manager = manager
        self.camera_panel = panel
        self.map_canvas = canvas
        self.status_bar = _StatusBar()
        self.ping_refreshed = 0
        self.dashboard_refreshed = 0

    def refresh_ping_cameras(self) -> None:
        self.ping_refreshed += 1

    def refresh_status_dashboard(self) -> None:
        self.dashboard_refreshed += 1


def test_drawing_created_signal_persists_shape() -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
    controller.load_cameras("default")
    shape = DrawingShape("shape_test", "Line", [0.0, 0.0, 40.0, 40.0])

    canvas.drawing_created.emit(shape)

    saved = manager.get_drawing_shapes()
    assert len(saved) == 1
    assert saved[0].id == shape.id
    assert saved[0].layer_id == manager.first_layer_id("default")
    assert controller.current_layout_id == "default"
    app.processEvents()


def test_canvas_deletes_selected_drawing_shape() -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    panel = CameraPanel()
    canvas = MapCanvas()
    CameraPlacementController(panel, canvas, manager)
    shape = DrawingShape("shape_test", "Line", [0.0, 0.0, 40.0, 40.0])

    item = canvas.add_drawing_shape(shape, emit_created=True)
    assert item is not None
    canvas.set_drawing_mode(DrawingMode.SELECT)
    item.setSelected(True)

    assert canvas.delete_selected_drawings() == 1
    assert manager.get_drawing_shapes() == []
    app.processEvents()


def test_canvas_unbinds_selected_camera_without_deleting_record() -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _seed_default_devices(manager)
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
    controller.load_cameras("default")
    controller.handle_camera_dropped("cam_01", 100.0, 100.0)

    canvas.set_drawing_mode(DrawingMode.SELECT)
    canvas.camera_items["cam_01"].setSelected(True)

    assert canvas.delete_selected_drawings() == 1
    saved = manager.get_camera("cam_01")
    assert saved is not None
    assert "cam_01" not in canvas.camera_items
    assert "cam_01" in {camera.id for camera in manager.get_unplaced_cameras()}
    panel.unplaced_button.click()
    assert _camera_count(panel) == 5
    app.processEvents()


def test_delete_key_unplaces_selected_camera_without_deleting_record() -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _seed_default_devices(manager)
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
    controller.load_cameras("default")
    controller.handle_camera_dropped("cam_01", 100.0, 100.0)
    canvas.set_drawing_mode(DrawingMode.SELECT)
    canvas.camera_items["cam_01"].setSelected(True)

    event = _KeyEvent(Qt.Key.Key_Delete)
    canvas.keyPressEvent(event)

    saved = manager.get_camera("cam_01")
    assert event.accepted is True
    assert saved is not None
    assert "cam_01" not in canvas.camera_items
    assert "cam_01" in {camera.id for camera in manager.get_unplaced_cameras()}
    panel.unplaced_button.click()
    assert _camera_count(panel) == 5
    app.processEvents()


def test_canvas_rotates_selected_camera() -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _seed_default_devices(manager)
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
    controller.load_cameras("default")
    controller.handle_camera_dropped("cam_01", 100.0, 100.0)

    canvas.set_drawing_mode(DrawingMode.SELECT)
    canvas.camera_items["cam_01"].setSelected(True)

    assert canvas.rotate_selected_cameras(15.0) == 1
    saved = manager.get_camera("cam_01")
    assert saved is not None
    assert saved.rotation == 15.0
    app.processEvents()


def test_canvas_resizes_selected_camera_and_persists_scale() -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _seed_default_devices(manager)
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
    controller.load_cameras("default")
    controller.handle_camera_dropped("cam_01", 100.0, 100.0)

    item = canvas.camera_items["cam_01"]
    item.resize_start_distance = 50.0
    item.resize_start_scale = 1.0
    item._apply_resize_from_distance(125.0)

    saved = manager.get_camera("cam_01")
    assert saved is not None
    assert saved.display_scale == 2.5
    assert controller.current_layout_id == "default"
    app.processEvents()


def test_canvas_moves_selected_camera_to_custom_layer() -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _seed_default_devices(manager)
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
    controller.load_cameras("default")
    layer = manager.create_layer("Custom", "default")
    canvas.set_canvas_layers(manager.get_layers("default"), "default")
    controller.handle_camera_dropped("cam_01", 100.0, 100.0)

    item = canvas.camera_items["cam_01"]
    canvas.set_drawing_mode(DrawingMode.SELECT)
    item.setSelected(True)

    assert canvas.move_selected_items_to_layer(layer.id) == 1
    saved = manager.get_camera("cam_01")
    assert saved is not None
    assert saved.layer_id == layer.id
    app.processEvents()


def test_canvas_grid_visibility_toggle() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()

    canvas.set_grid_visible(False)
    assert canvas.grid_items
    assert all(not item.isVisible() for item in canvas.grid_items)

    canvas.set_grid_visible(True)
    assert all(item.isVisible() for item in canvas.grid_items)
    app.processEvents()


def test_canvas_theme_updates_grid_and_camera_items() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    camera_item = canvas.add_camera_item(Camera("cam_test", "Lobby", "10.0.0.10"))

    assert not canvas.light_theme
    assert not camera_item.light_theme
    assert canvas.grid_items[0].pen().color().name() == GRID_DARK

    canvas.set_light_theme(True)

    assert canvas.light_theme
    assert camera_item.light_theme
    assert canvas.grid_items[0].pen().color().name() == GRID_LIGHT
    app.processEvents()


def test_status_dashboard_callback_runs_after_load_and_status_update() -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _seed_default_devices(manager)
    panel = CameraPanel()
    canvas = MapCanvas()
    refresh_count = 0

    def refresh_dashboard() -> None:
        nonlocal refresh_count
        refresh_count += 1

    controller = CameraPlacementController(
        panel,
        canvas,
        manager,
        dashboard_refresh_callback=refresh_dashboard,
    )

    controller.load_cameras("default")
    controller.handle_camera_status_updated("cam_01", True, 1.5)

    assert refresh_count >= 2
    app.processEvents()


def test_canvas_renames_camera_object_and_refreshes_panel() -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _seed_default_devices(manager)
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
    controller.load_cameras("default")
    controller.handle_camera_dropped("cam_01", 100.0, 100.0)

    assert canvas.rename_layer_object("camera", "cam_01", "Renamed Camera")

    saved = manager.get_camera("cam_01")
    assert saved is not None
    assert saved.name == "Renamed Camera"
    assert canvas.camera_items["cam_01"].camera.name == "Renamed Camera"
    assert any("Renamed Camera" in item.text(0) for item in _tree_items(panel))
    app.processEvents()


def test_canvas_renames_drawing_object_without_changing_text_content() -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
    controller.load_cameras("default")
    item = canvas.add_drawing_shape(DrawingShape("text_test", "Text", [1.0, 2.0], label="Visible Text"), emit_created=True)
    assert item is not None
    assert controller.current_layout_id == "default"

    assert canvas.rename_layer_object("drawing", "text_test", "Layer Row Name")

    saved = manager.get_drawing_shapes()[0]
    assert saved.display_name == "Layer Row Name"
    assert item.toPlainText() == "Visible Text"
    assert canvas.get_layer_object_states(canvas.active_layer_id)[0].label == "Layer Row Name"
    app.processEvents()


def test_controller_active_ping_uses_camera_ip(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    panel = CameraPanel()
    canvas = MapCanvas()
    messages = []
    opened = []
    controller = CameraPlacementController(panel, canvas, manager, status_callback=lambda message, timeout: messages.append(message))
    manager.add_camera(Camera("cam_ping", "Ping Cam", "10.0.0.88"))
    controller.load_cameras("default")
    monkeypatch.setattr("controllers.camera_placement_controller.open_active_ping", lambda ip_address: opened.append(ip_address) or True)

    controller.ping_camera("cam_ping")

    assert opened == ["10.0.0.88"]
    assert "10.0.0.88" in messages[-1]
    assert manager.get_ping_history("cam_ping") == []
    app.processEvents()


def test_camera_panel_search_toggle_and_link_tree_grouping() -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    server = Camera("server_a", "Server A", "", device_kind=DEVICE_KIND_SERVER, variant="Rack", ping_enabled=False)
    switch = Camera("switch_a", "Switch A", "10.0.0.20", device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    camera = Camera("cam_b", "Lobby", "10.0.0.11")
    gate = Camera("cam_a", "Gate", "10.0.0.10")
    for device in (server, switch, camera, gate):
        manager.add_camera(device)
    manager.update_camera_position("server_a", 30, 20)
    manager.update_camera_position("switch_a", 20, 20)
    manager.update_camera_position("cam_b", 10, 20)
    manager.add_device_link("cam_b", "switch_a")
    manager.add_device_link("switch_a", "server_a")

    panel.set_cameras(manager.get_all_cameras(), {"server_a", "switch_a", "cam_b"}, manager.get_device_links())

    root = panel.tree_widget.topLevelItem(0)
    assert root.isExpanded() is False
    assert "Server A" in root.text(0)
    assert "Switch A" in root.child(0).text(0)
    assert "Lobby" in root.child(0).child(0).text(0)

    panel.search_input.setText("Lobby")
    root = panel.tree_widget.topLevelItem(0)
    assert _camera_count(panel) == 3
    assert root.isExpanded() is True
    assert root.child(0).isExpanded() is True
    assert panel.tree_widget.currentItem().data(0, Qt.ItemDataRole.UserRole) == "cam_b"
    assert "Server A" in root.text(0)
    assert "Switch A" in root.child(0).text(0)
    assert "Lobby" in root.child(0).child(0).text(0)
    assert root.data(0, Qt.ItemDataRole.UserRole) != "group:unlinked"
    panel.search_input.setText("Switch")
    root = panel.tree_widget.topLevelItem(0)
    assert _camera_count(panel) == 3
    assert root.isExpanded() is True
    assert root.child(0).isExpanded() is True
    assert panel.tree_widget.currentItem().data(0, Qt.ItemDataRole.UserRole) == "switch_a"
    assert "Switch A" in root.child(0).text(0)
    assert "Lobby" in root.child(0).child(0).text(0)
    panel.search_input.setText("10.0.0.20")
    root = panel.tree_widget.topLevelItem(0)
    assert _camera_count(panel) == 3
    assert "Switch A" in root.child(0).text(0)
    assert "Lobby" in root.child(0).child(0).text(0)
    panel.search_input.clear()
    root = panel.tree_widget.topLevelItem(0)
    assert root.isExpanded() is False
    panel.unplaced_button.click()
    assert _camera_count(panel) == 1
    assert "Gate" in panel.tree_widget.topLevelItem(0).child(0).text(0)
    app.processEvents()


def test_camera_panel_search_expands_unlinked_group_and_clear_restores_user_state() -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    placed = Camera("cam_placed", "Placed", "10.0.0.10")
    unlinked = Camera("cam_unlinked", "Search Target", "10.0.0.11")
    panel.set_cameras([placed, unlinked], set())
    panel.unplaced_button.click()

    group = panel.tree_widget.topLevelItem(0)
    assert group.data(0, Qt.ItemDataRole.UserRole) == "group:unlinked"
    assert group.isExpanded() is False

    panel.search_input.setText("target")

    group = panel.tree_widget.topLevelItem(0)
    assert group.isExpanded() is True
    assert panel.tree_widget.currentItem().data(0, Qt.ItemDataRole.UserRole) == "cam_unlinked"

    panel.search_input.clear()

    group = panel.tree_widget.topLevelItem(0)
    assert group.isExpanded() is False
    group.setExpanded(True)
    panel.search_input.setText("target")
    panel.search_input.clear()

    group = panel.tree_widget.topLevelItem(0)
    assert group.isExpanded() is True
    app.processEvents()


def test_canvas_device_can_move_outside_scene_without_bounds_clamp() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.resize_canvas(200, 160)
    camera = Camera("cam_edge", "Edge", "10.0.0.10", position_x=20.0, position_y=20.0)
    item = canvas.add_camera_item(camera)
    item.setSelected(True)

    item.setPos(-45.0, -30.0)
    canvas.scene.clamp_selected_items()

    assert item.pos().x() == -45.0
    assert item.pos().y() == -30.0
    assert camera.position_x == -45.0
    assert camera.position_y == -30.0
    app.processEvents()


def test_camera_tree_quick_link_drop_accepts_only_created_link(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    camera = Camera("cam_a", "Camera A", "10.0.0.10")
    switch = Camera("switch_a", "Switch A", "", device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    panel.set_cameras([camera, switch], {"cam_a", "switch_a"}, [])
    created = []
    panel.set_device_link_request_handler(lambda source, target: created.append((source, target)) or True)
    monkeypatch.setattr(panel.tree_widget, "itemAt", lambda _point: _camera_item(panel, "switch_a"))

    event = _DropEvent(panel.tree_widget._drag_mime_data(_camera_item(panel, "cam_a")))
    panel.tree_widget.dropEvent(event)

    assert created == [("cam_a", "switch_a")]
    assert event.accepted is True
    assert event.drop_action == Qt.DropAction.CopyAction
    app.processEvents()


def test_camera_tree_quick_link_drop_ignores_rejected_handler(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    camera = Camera("cam_a", "Camera A", "10.0.0.10")
    switch = Camera("switch_a", "Switch A", "", device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    panel.set_cameras([camera, switch], {"cam_a", "switch_a"}, [])
    panel.set_device_link_request_handler(lambda _source, _target: False)
    monkeypatch.setattr(panel.tree_widget, "itemAt", lambda _point: _camera_item(panel, "switch_a"))

    event = _DropEvent(panel.tree_widget._drag_mime_data(_camera_item(panel, "cam_a")))
    panel.tree_widget.dropEvent(event)

    assert event.accepted is False
    assert event.ignored is True
    app.processEvents()


def test_camera_tree_quick_link_drop_rejects_duplicate_and_descendant(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    camera = Camera("cam_a", "Camera A", "10.0.0.10")
    switch = Camera("switch_a", "Switch A", "", device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    server = Camera("server_a", "Server A", "", device_kind=DEVICE_KIND_SERVER, variant="Rack", ping_enabled=False)
    links = [
        DeviceLink("link_1", "default", "cam_a", "switch_a"),
        DeviceLink("link_2", "default", "switch_a", "server_a"),
    ]
    panel.set_cameras([camera, switch, server], {"cam_a", "switch_a", "server_a"}, links)
    requested = []
    panel.set_device_link_request_handler(lambda source, target: requested.append((source, target)) or True)

    monkeypatch.setattr(panel.tree_widget, "itemAt", lambda _point: _camera_item(panel, "switch_a"))
    duplicate = _DropEvent(panel.tree_widget._drag_mime_data(_camera_item(panel, "cam_a")))
    panel.tree_widget.dropEvent(duplicate)

    monkeypatch.setattr(panel.tree_widget, "itemAt", lambda _point: _camera_item(panel, "cam_a"))
    descendant = _DropEvent(panel.tree_widget._drag_mime_data(_camera_item(panel, "switch_a")))
    panel.tree_widget.dropEvent(descendant)

    assert requested == []
    assert duplicate.ignored is True
    assert descendant.ignored is True
    app.processEvents()


def test_camera_tree_quick_link_branch_drop_links_branch_root(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    camera = Camera("cam_a", "Camera A", "10.0.0.10")
    switch = Camera("switch_a", "Switch A", "", device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    router = Camera("router_a", "Router A", "", device_kind=DEVICE_KIND_SERVER, variant="Router", ping_enabled=False)
    links = [DeviceLink("link_1", "default", "cam_a", "switch_a")]
    panel.set_cameras([camera, switch, router], {"cam_a", "switch_a", "router_a"}, links)
    created = []
    panel.set_device_link_request_handler(lambda source, target: created.append((source, target)) or True)
    monkeypatch.setattr(panel.tree_widget, "itemAt", lambda _point: _camera_item(panel, "router_a"))

    event = _DropEvent(panel.tree_widget._drag_mime_data(_camera_item(panel, "switch_a")))
    panel.tree_widget.dropEvent(event)

    assert created == [("switch_a", "router_a")]
    assert event.accepted is True
    app.processEvents()


def test_camera_tree_quick_link_multi_selection_links_each_source(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    camera_a = Camera("cam_a", "Camera A", "10.0.0.10")
    camera_b = Camera("cam_b", "Camera B", "10.0.0.11")
    switch = Camera("switch_a", "Switch A", "", device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    panel.set_cameras([camera_a, camera_b, switch], {"cam_a", "cam_b", "switch_a"}, [])
    created = []
    panel.set_device_link_request_handler(lambda source, target: created.append((source, target)) or True)
    monkeypatch.setattr(panel.tree_widget, "itemAt", lambda _point: _camera_item(panel, "switch_a"))

    event = _DropEvent(panel.tree_widget._drag_mime_data([_camera_item(panel, "cam_a"), _camera_item(panel, "cam_b")]))
    panel.tree_widget.dropEvent(event)

    assert created == [("cam_a", "switch_a"), ("cam_b", "switch_a")]
    assert event.accepted is True
    app.processEvents()


def test_camera_tree_quick_link_preserves_other_expanded_groups(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    cam_a = Camera("cam_a", "Camera A", "10.0.0.10")
    switch_a = Camera("switch_a", "Switch A", "", device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    cam_b = Camera("cam_b", "Camera B", "10.0.0.11")
    switch_b = Camera("switch_b", "Switch B", "", device_kind=DEVICE_KIND_SWITCH, variant="Access", ping_enabled=False)
    router = Camera("router_a", "Router A", "", device_kind=DEVICE_KIND_SERVER, variant="Router", ping_enabled=False)
    links = [
        DeviceLink("link_1", "default", "cam_a", "switch_a"),
        DeviceLink("link_2", "default", "cam_b", "switch_b"),
    ]
    devices = [cam_a, switch_a, cam_b, switch_b, router]
    panel.set_cameras(devices, {device.id for device in devices}, links)
    _camera_item(panel, "switch_a").setExpanded(True)
    _camera_item(panel, "switch_b").setExpanded(True)

    def create_link(source: str, target: str) -> bool:
        links.append(DeviceLink("link_3", "default", source, target))
        panel.set_cameras(devices, {device.id for device in devices}, links)
        return True

    panel.set_device_link_request_handler(create_link)
    monkeypatch.setattr(panel.tree_widget, "itemAt", lambda _point: _camera_item(panel, "router_a"))

    event = _DropEvent(panel.tree_widget._drag_mime_data(_camera_item(panel, "switch_a")))
    panel.tree_widget.dropEvent(event)

    assert event.accepted is True
    assert _camera_item(panel, "switch_b").isExpanded() is True
    assert _camera_item(panel, "router_a").isExpanded() is False
    assert _camera_item(panel, "switch_a").isExpanded() is True
    app.processEvents()


def test_camera_tree_blank_drop_ungroups_selected_sources(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    camera_a = Camera("cam_a", "Camera A", "10.0.0.10")
    camera_b = Camera("cam_b", "Camera B", "10.0.0.11")
    switch = Camera("switch_a", "Switch A", "", device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    links = [
        DeviceLink("link_1", "default", "cam_a", "switch_a"),
        DeviceLink("link_2", "default", "cam_b", "switch_a"),
    ]
    panel.set_cameras([camera_a, camera_b, switch], {"cam_a", "cam_b", "switch_a"}, links)
    ungrouped = []
    panel.set_device_unlink_request_handler(lambda source_ids: ungrouped.extend(source_ids) or True)
    monkeypatch.setattr(panel.tree_widget, "itemAt", lambda _point: None)

    event = _DropEvent(panel.tree_widget._drag_mime_data([_camera_item(panel, "cam_a"), _camera_item(panel, "cam_b")]))
    panel.tree_widget.dropEvent(event)

    assert ungrouped == ["cam_a", "cam_b"]
    assert event.accepted is True
    app.processEvents()


def test_camera_controller_ungroup_refreshes_panel_tree() -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
    camera = Camera("cam_a", "Camera A", "10.0.0.10")
    switch = Camera("switch_a", "Switch A", "", device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    manager.add_camera(camera, is_placed=True)
    manager.add_camera(switch, is_placed=True)
    manager.add_device_link("cam_a", "switch_a")
    controller.load_cameras("default")

    assert _camera_item(panel, "cam_a").parent() is _camera_item(panel, "switch_a")

    assert controller.unlink_devices_from_group(["cam_a"]) is True

    assert manager.get_device_links("default") == []
    assert _camera_item(panel, "cam_a").parent() is not _camera_item(panel, "switch_a")
    assert panel.tree_widget.topLevelItem(0).isExpanded() is False
    app.processEvents()


def test_device_parent_picker_lists_unplaced_and_excludes_descendants() -> None:
    app = QApplication.instance() or QApplication([])
    camera = Camera("cam_a", "Camera A", "10.0.0.10")
    switch = Camera("switch_a", "Switch A", "10.0.0.20", device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    router = Camera("router_a", "Router A", "10.0.0.30", device_kind=DEVICE_KIND_SERVER, variant="Rack", ping_enabled=False)
    child = Camera("child_a", "Child A", "10.0.0.40")
    links = [
        DeviceLink("link_1", "default", "child_a", "cam_a"),
        DeviceLink("link_2", "default", "cam_a", "switch_a"),
    ]
    dialog = DeviceParentPickerDialog(
        "cam_a",
        {device.id: device for device in [camera, switch, router, child]},
        links,
        lambda _device_id: "",
    )

    visible_ids = {
        dialog.tree_widget.topLevelItem(index).data(0, Qt.ItemDataRole.UserRole)
        for index in range(dialog.tree_widget.topLevelItemCount())
    }
    assert visible_ids == {"switch_a", "router_a"}

    dialog.search_input.setText("router")
    visible_ids = {
        dialog.tree_widget.topLevelItem(index).data(0, Qt.ItemDataRole.UserRole)
        for index in range(dialog.tree_widget.topLevelItemCount())
    }
    assert visible_ids == {"router_a"}
    app.processEvents()


def test_camera_controller_change_parent_replaces_existing_parent_link() -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    panel = CameraPanel()
    canvas = MapCanvas()
    messages = []
    controller = CameraPlacementController(
        panel,
        canvas,
        manager,
        status_callback=lambda message, _timeout: messages.append(message),
    )
    camera = Camera("cam_a", "Camera A", "10.0.0.10")
    old_parent = Camera("switch_a", "Switch A", "", device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    new_parent = Camera("router_a", "Router A", "", device_kind=DEVICE_KIND_SERVER, variant="Rack", ping_enabled=False)
    for device in (camera, old_parent, new_parent):
        assert manager.add_camera(device, is_placed=True)
    assert manager.add_device_link("cam_a", "switch_a")
    controller.load_cameras("default")

    assert controller.change_device_parent("cam_a", "router_a") is True

    assert {(link.source_device_id, link.target_device_id) for link in manager.get_device_links()} == {
        ("cam_a", "router_a")
    }
    assert {(link.source_device_id, link.target_device_id) for link in canvas.device_links} == {
        ("cam_a", "router_a")
    }
    assert _camera_item(panel, "cam_a").parent() is _camera_item(panel, "router_a")
    assert messages
    app.processEvents()


def test_camera_tree_link_unlink_preserves_only_existing_expanded_groups(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    cam_a = Camera("cam_a", "Camera A", "10.0.0.10")
    switch_a = Camera("switch_a", "Switch A", "", device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    cam_b = Camera("cam_b", "Camera B", "10.0.0.11")
    switch_b = Camera("switch_b", "Switch B", "", device_kind=DEVICE_KIND_SWITCH, variant="Access", ping_enabled=False)
    cam_c = Camera("cam_c", "Camera C", "10.0.0.12")
    switch_c = Camera("switch_c", "Switch C", "", device_kind=DEVICE_KIND_SWITCH, variant="Edge", ping_enabled=False)
    router = Camera("router_a", "Router A", "", device_kind=DEVICE_KIND_SERVER, variant="Router", ping_enabled=False)
    devices = [cam_a, switch_a, cam_b, switch_b, cam_c, switch_c, router]
    placed_ids = {device.id for device in devices}
    links = [
        DeviceLink("link_1", "default", "cam_a", "switch_a"),
        DeviceLink("link_2", "default", "cam_b", "switch_b"),
        DeviceLink("link_3", "default", "cam_c", "switch_c"),
    ]
    panel.set_cameras(devices, placed_ids, links)
    _camera_item(panel, "switch_a").setExpanded(True)
    _camera_item(panel, "switch_b").setExpanded(False)
    _camera_item(panel, "switch_c").setExpanded(False)

    def create_link(source: str, target: str) -> bool:
        links.append(DeviceLink("link_4", "default", source, target))
        panel.set_cameras(devices, placed_ids, links)
        return True

    panel.set_device_link_request_handler(create_link)
    monkeypatch.setattr(panel.tree_widget, "itemAt", lambda _point: _camera_item(panel, "router_a"))

    link_event = _DropEvent(panel.tree_widget._drag_mime_data(_camera_item(panel, "switch_c")))
    panel.tree_widget.dropEvent(link_event)

    assert link_event.accepted is True
    assert _camera_item(panel, "switch_a").isExpanded() is True
    assert _camera_item(panel, "switch_b").isExpanded() is False
    assert _camera_item(panel, "switch_c").isExpanded() is False
    assert _camera_item(panel, "router_a").isExpanded() is False

    def unlink_devices(source_ids: list[str]) -> bool:
        links[:] = [link for link in links if link.source_device_id not in source_ids]
        panel.set_cameras(devices, placed_ids, links)
        return True

    panel.set_device_unlink_request_handler(unlink_devices)
    monkeypatch.setattr(panel.tree_widget, "itemAt", lambda _point: None)

    unlink_event = _DropEvent(panel.tree_widget._drag_mime_data(_camera_item(panel, "cam_c")))
    panel.tree_widget.dropEvent(unlink_event)

    assert unlink_event.accepted is True
    assert _camera_item(panel, "switch_a").isExpanded() is True
    assert _camera_item(panel, "switch_b").isExpanded() is False
    assert panel.tree_widget.topLevelItem(panel.tree_widget.topLevelItemCount() - 1).isExpanded() is False
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


def test_camera_tree_wheel_scrolls_while_dragging(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    scroll_bar = _ScrollBar()
    monkeypatch.setattr(panel.tree_widget, "verticalScrollBar", lambda: scroll_bar)
    panel.tree_widget._drag_in_progress = True

    down_event = _WheelEvent(-120)
    panel.tree_widget.wheelEvent(down_event)

    assert down_event.accepted is True
    assert scroll_bar.value() == 80

    up_event = _WheelEvent(120)
    panel.tree_widget.wheelEvent(up_event)

    assert up_event.accepted is True
    assert scroll_bar.value() == 50
    panel.tree_widget._drag_in_progress = False
    app.processEvents()


def test_import_action_refreshes_placed_canvas_item_after_replace(tmp_path, monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    camera = Camera("csv_placed", "Old Device", "10.0.0.20", position_x=10.0, position_y=20.0)
    assert manager.add_camera(camera, is_placed=True)
    panel = CameraPanel()
    canvas = MapCanvas()
    panel.set_cameras(manager.get_all_cameras(), {"csv_placed"}, [])
    canvas.add_camera_item(manager.get_camera("csv_placed"))
    host = _ImportActionHost(manager, panel, canvas)
    csv_path = tmp_path / "replace.csv"
    csv_path.write_text(
        "id,name,ip_address,port,camera_type,device_kind,variant\n"
        "csv_placed,New Device,10.0.0.21,554,Fixed,Camera,Fixed\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "views.app_camera_actions.QFileDialog.getOpenFileName",
        lambda *_args, **_kwargs: (str(csv_path), ""),
    )

    host.import_cameras_csv()

    assert canvas.camera_items["csv_placed"].camera.name == "New Device"
    assert canvas.camera_items["csv_placed"].camera.ip_address == "10.0.0.21"
    assert panel.cameras["csv_placed"].name == "New Device"
    assert host.ping_refreshed == 1
    assert host.dashboard_refreshed == 1
    app.processEvents()


def test_camera_tree_event_filter_scrolls_wheel_while_dragging(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    scroll_bar = _ScrollBar()
    monkeypatch.setattr(panel.tree_widget, "verticalScrollBar", lambda: scroll_bar)
    panel.tree_widget._drag_in_progress = True

    wheel_event = _DragWheelEvent(-120)
    handled = panel.tree_widget.eventFilter(panel.tree_widget.viewport(), wheel_event)

    assert handled is True
    assert wheel_event.accepted is True
    assert scroll_bar.value() == 80

    pixel_event = _DragWheelEvent(0, pixel_delta=-18)
    handled = panel.tree_widget.eventFilter(panel.tree_widget.viewport(), pixel_event)

    assert handled is True
    assert pixel_event.accepted is True
    assert scroll_bar.value() == 98
    panel.tree_widget._drag_in_progress = False
    app.processEvents()


def test_camera_panel_groups_are_collapsed_by_default() -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    server = Camera("server_a", "Server A", "", device_kind=DEVICE_KIND_SERVER, variant="Rack", ping_enabled=False)
    switch = Camera("switch_a", "Switch A", "", device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    camera = Camera("cam_a", "Camera A", "10.0.0.10")
    links = [
        DeviceLink("link_1", "default", "cam_a", "switch_a"),
        DeviceLink("link_2", "default", "switch_a", "server_a"),
    ]

    panel.set_cameras([server, switch, camera], {"server_a", "switch_a", "cam_a"}, links)

    assert panel.tree_widget.topLevelItem(0).isExpanded() is False
    app.processEvents()


def test_camera_panel_preserves_expanded_group_on_refresh() -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    cameras = [
        Camera("cam_a", "Gate", "10.0.0.10", dvr_origin="DVR-A"),
        Camera("cam_b", "Lobby", "10.0.0.11", dvr_origin="DVR-A"),
    ]

    panel.set_cameras(cameras, set())
    assert panel.placed_button.isChecked()
    assert not panel.unplaced_button.isChecked()
    panel.unplaced_button.click()
    panel.tree_widget.topLevelItem(0).setExpanded(True)

    panel.remove_camera_from_list("cam_a")

    assert panel.tree_widget.topLevelItemCount() == 1
    assert panel.tree_widget.topLevelItem(0).isExpanded() is True
    app.processEvents()

    panel.search_input.setText("Gate")
    assert _camera_count(panel) == 0

    panel.placed_button.click()
    assert _camera_count(panel) == 1
    panel.search_input.setText("")
    assert _camera_count(panel) == 1
    app.processEvents()


def test_camera_panel_emits_focus_only_for_placed_devices() -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    placed = Camera("cam_placed", "Placed", "10.0.0.10")
    unplaced = Camera("cam_unplaced", "Unplaced", "10.0.0.11")
    focused = []
    panel.camera_focus_requested.connect(focused.append)

    panel.set_cameras([placed, unplaced], {"cam_placed"})
    placed_item = next(item for item in _tree_items(panel) if item.data(0, Qt.ItemDataRole.UserRole) == "cam_placed")
    panel.tree_widget.setCurrentItem(placed_item)

    assert focused == ["cam_placed"]

    panel.unplaced_button.click()
    unplaced_item = next(item for item in _tree_items(panel) if item.data(0, Qt.ItemDataRole.UserRole) == "cam_unplaced")
    panel.tree_widget.setCurrentItem(unplaced_item)

    assert focused == ["cam_placed"]
    app.processEvents()


def test_camera_panel_multi_select_emits_placed_devices_for_topology_highlight() -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    router = Camera("router", "Router", "", device_kind=DEVICE_KIND_SERVER, ping_enabled=False)
    switch_a = Camera("switch_a", "Switch A", "", device_kind=DEVICE_KIND_SWITCH, ping_enabled=False)
    switch_b = Camera("switch_b", "Switch B", "", device_kind=DEVICE_KIND_SWITCH, ping_enabled=False)
    cam_a = Camera("cam_a", "Camera A", "10.0.0.10")
    cam_b = Camera("cam_b", "Camera B", "10.0.0.11")
    unplaced = Camera("cam_unplaced", "Unplaced", "10.0.0.12")
    links = [
        DeviceLink("link_a_switch", "default", "cam_a", "switch_a"),
        DeviceLink("link_b_switch", "default", "cam_b", "switch_b"),
        DeviceLink("link_switch_a_router", "default", "switch_a", "router"),
        DeviceLink("link_switch_b_router", "default", "switch_b", "router"),
    ]
    many_focused = []
    single_focused = []
    panel.camera_focus_requested.connect(single_focused.append)
    panel.camera_focus_many_requested.connect(many_focused.append)
    panel.set_cameras([router, switch_a, switch_b, cam_a, cam_b, unplaced], {"router", "switch_a", "switch_b", "cam_a", "cam_b"}, links)
    cam_a_item = _camera_item(panel, "cam_a")
    cam_b_item = _camera_item(panel, "cam_b")

    panel.tree_widget.clearSelection()
    panel.tree_widget.setCurrentItem(cam_a_item)
    cam_a_item.setSelected(True)
    cam_b_item.setSelected(True)
    panel._emit_focused_camera()

    assert many_focused[-1] == ["cam_a", "cam_b"]
    assert single_focused

    panel.unplaced_button.click()
    unplaced_item = _camera_item(panel, "cam_unplaced")
    panel.tree_widget.clearSelection()
    panel.tree_widget.setCurrentItem(unplaced_item)
    unplaced_item.setSelected(True)
    panel._emit_focused_camera()

    assert many_focused[-1] == []
    app.processEvents()


def test_device_panel_filters_status_with_unlinked_group() -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    server = Camera(
        "server_a",
        "Server A",
        "",
        device_kind=DEVICE_KIND_SERVER,
        variant="Rack",
        ping_enabled=False,
    )

    panel.set_cameras([server], set())
    panel.unplaced_button.click()

    assert panel.status_filter_input.currentData() == "all"
    assert panel.tree_widget.topLevelItem(0).data(0, Qt.ItemDataRole.UserRole) == "group:unlinked"
    assert "(1)" in panel.tree_widget.topLevelItem(0).text(0)
    assert "Server" in panel.tree_widget.topLevelItem(0).child(0).text(0)

    panel.status_filter_input.setCurrentIndex(panel.status_filter_input.findData("unknown"))
    assert _camera_count(panel) == 1
    panel.status_filter_input.setCurrentIndex(panel.status_filter_input.findData("online"))
    assert _camera_count(panel) == 0
    app.processEvents()


def test_canvas_device_link_signal_persists_and_overlay_shows_related_chain() -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
    camera = Camera("cam_a", "Camera A", "10.0.0.10", position_x=0.0, position_y=0.0)
    switch = Camera("switch_a", "Switch A", "", position_x=100.0, position_y=0.0, device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    server = Camera("server_a", "Server A", "", device_kind=DEVICE_KIND_SERVER, variant="Rack", ping_enabled=False)
    manager.add_camera(camera, is_placed=True)
    manager.add_camera(switch, is_placed=True)
    manager.add_camera(server, is_placed=True)
    controller.load_cameras("default")
    canvas.set_drawing_mode(DrawingMode.SELECT)

    canvas.device_link_created.emit("cam_a", "switch_a")
    canvas.device_link_created.emit("switch_a", "server_a")
    canvas.camera_items["cam_a"].setSelected(True)

    assert len(manager.get_device_links()) == 2
    assert len(canvas.device_link_items) == 2
    app.processEvents()


def test_canvas_topology_highlight_marks_upstream_and_downstream_without_siblings() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    camera = Camera("cam_a", "Camera A", "10.0.0.10", position_x=0.0, position_y=0.0)
    ap = Camera("ap_a", "AP A", "10.0.0.20", position_x=50.0, position_y=0.0, device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    switch = Camera("switch_a", "Switch A", "10.0.0.30", position_x=100.0, position_y=0.0, device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    router = Camera("router_a", "Router A", "10.0.0.40", position_x=150.0, position_y=0.0, device_kind=DEVICE_KIND_SERVER, variant="Rack", ping_enabled=False)
    sibling = Camera("pc_a", "PC A", "10.0.0.50", position_x=100.0, position_y=50.0)
    for device in (camera, ap, switch, router, sibling):
        canvas.add_camera_item(device)
    links = [
        DeviceLink("link_cam_ap", "default", "cam_a", "ap_a"),
        DeviceLink("link_ap_switch", "default", "ap_a", "switch_a"),
        DeviceLink("link_switch_router", "default", "switch_a", "router_a"),
        DeviceLink("link_pc_switch", "default", "pc_a", "switch_a"),
    ]
    canvas.set_device_links(links)
    canvas.set_drawing_mode(DrawingMode.SELECT)

    canvas.camera_items["cam_a"].setSelected(True)

    assert canvas.camera_items["cam_a"].topology_highlight_role == "selected"
    assert canvas.camera_items["ap_a"].topology_highlight_role == "related"
    assert canvas.camera_items["switch_a"].topology_highlight_role == "related"
    assert canvas.camera_items["router_a"].topology_highlight_role == "related"
    assert canvas.camera_items["pc_a"].topology_highlight_role == ""

    canvas.scene.clearSelection()
    assert canvas.highlight_device_topology("cam_a")

    assert canvas.camera_items["cam_a"].topology_highlight_role == "selected"
    assert canvas.camera_items["ap_a"].topology_highlight_role == "related"
    assert canvas.camera_items["switch_a"].topology_highlight_role == "related"
    assert canvas.camera_items["router_a"].topology_highlight_role == "related"
    assert canvas.camera_items["pc_a"].topology_highlight_role == ""
    assert {item.link.id for item in canvas.device_link_items} == {
        "link_cam_ap",
        "link_ap_switch",
        "link_switch_router",
    }
    assert all(item.link_role == "upstream" for item in canvas.device_link_items)
    assert all(item.pen().color().name() == "#f59e0b" for item in canvas.device_link_items)

    assert canvas.highlight_device_topology("switch_a")

    roles = {item.link.id: item.link_role for item in canvas.device_link_items}
    colors = {item.link.id: item.pen().color().name() for item in canvas.device_link_items}
    assert roles == {
        "link_cam_ap": "downstream",
        "link_ap_switch": "downstream",
        "link_pc_switch": "downstream",
        "link_switch_router": "upstream",
    }
    assert colors["link_switch_router"] == "#f59e0b"
    assert colors["link_cam_ap"] == "#38bdf8"
    assert canvas.camera_items["pc_a"].topology_highlight_role == "related"
    assert canvas.camera_items["switch_a"].topology_highlight_role == "selected"

    canvas.camera_items["pc_a"].setSelected(True)

    assert all(not item.topology_highlight_role for item in canvas.camera_items.values())
    assert canvas.device_link_items == []

    canvas.scene.clearSelection()

    assert all(not item.topology_highlight_role for item in canvas.camera_items.values())
    assert canvas.device_link_items == []
    app.processEvents()


def test_canvas_multi_topology_highlight_unions_selected_devices_and_link_roles() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    camera = Camera("cam_a", "Camera A", "10.0.0.10", position_x=0.0, position_y=0.0)
    ap = Camera("ap_a", "AP A", "10.0.0.20", position_x=50.0, position_y=0.0, device_kind=DEVICE_KIND_SWITCH, ping_enabled=False)
    switch = Camera("switch_a", "Switch A", "10.0.0.30", position_x=100.0, position_y=0.0, device_kind=DEVICE_KIND_SWITCH, ping_enabled=False)
    router = Camera("router_a", "Router A", "10.0.0.40", position_x=150.0, position_y=0.0, device_kind=DEVICE_KIND_SERVER, ping_enabled=False)
    pc = Camera("pc_a", "PC A", "10.0.0.50", position_x=100.0, position_y=50.0)
    unrelated = Camera("pc_b", "PC B", "10.0.0.60", position_x=200.0, position_y=50.0)
    for device in (camera, ap, switch, router, pc, unrelated):
        canvas.add_camera_item(device)
    canvas.set_device_links(
        [
            DeviceLink("link_cam_ap", "default", "cam_a", "ap_a"),
            DeviceLink("link_ap_switch", "default", "ap_a", "switch_a"),
            DeviceLink("link_pc_switch", "default", "pc_a", "switch_a"),
            DeviceLink("link_switch_router", "default", "switch_a", "router_a"),
        ]
    )
    canvas.set_drawing_mode(DrawingMode.SELECT)

    assert canvas.highlight_device_topologies(["cam_a", "pc_a"], center=False)

    assert canvas.camera_items["cam_a"].topology_highlight_role == "selected"
    assert canvas.camera_items["pc_a"].topology_highlight_role == "selected"
    assert canvas.camera_items["ap_a"].topology_highlight_role == "related"
    assert canvas.camera_items["switch_a"].topology_highlight_role == "related"
    assert canvas.camera_items["router_a"].topology_highlight_role == "related"
    assert canvas.camera_items["pc_b"].topology_highlight_role == ""
    assert {
        item.camera.id for item in canvas.scene.selectedItems() if item.data(1) == "camera"
    } == {"cam_a", "pc_a"}
    roles = {item.link.id: item.link_role for item in canvas.device_link_items}
    assert roles == {
        "link_cam_ap": "upstream",
        "link_ap_switch": "upstream",
        "link_pc_switch": "upstream",
        "link_switch_router": "upstream",
    }
    assert len(canvas.device_link_items) == 4

    assert not canvas.highlight_device_topologies(["missing"], center=False)
    assert all(not item.topology_highlight_role for item in canvas.camera_items.values())
    assert canvas.device_link_items == []
    app.processEvents()


def test_canvas_device_link_context_menu_is_disabled(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
    controller.load_cameras("default")
    camera_a = Camera("cam_a", "Camera A", "10.0.0.10")
    camera_b = Camera("cam_b", "Camera B", "10.0.0.11")
    switch = Camera("switch_a", "Switch A", "", device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    manager.add_camera(camera_a, is_placed=True)
    manager.add_camera(camera_b, is_placed=True)
    manager.add_camera(switch, is_placed=True)
    canvas.add_camera_item(camera_a)
    canvas.add_camera_item(camera_b)
    canvas.add_camera_item(switch)
    manager.add_device_link("cam_a", "switch_a")
    manager.add_device_link("cam_b", "switch_a")
    canvas.set_device_links(manager.get_device_links())
    canvas.set_drawing_mode(DrawingMode.SELECT)
    canvas.camera_items["switch_a"].setSelected(True)

    def fail_if_opened(_menu: QMenu, _pos: object) -> object:
        raise AssertionError("canvas link context menu should not open")

    monkeypatch.setattr(QMenu, "exec", fail_if_opened)
    event = _ContextMenuEvent()
    canvas.device_link_items[0].contextMenuEvent(event)

    links = manager.get_device_links()
    assert event.ignored is True
    assert len(links) == 2
    assert {(link.source_device_id, link.target_device_id) for link in links} == {
        ("cam_a", "switch_a"),
        ("cam_b", "switch_a"),
    }
    assert len(canvas.device_link_items) == 2
    assert controller.current_layout_id == "default"
    app.processEvents()


def test_canvas_device_link_context_menu_ignores_link_mode(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    _create_default_layout(manager)
    panel = CameraPanel()
    canvas = MapCanvas()
    CameraPlacementController(panel, canvas, manager)
    camera = Camera("cam_a", "Camera A", "10.0.0.10", position_x=0.0, position_y=0.0)
    switch = Camera("switch_a", "Switch A", "", position_x=100.0, position_y=0.0, device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
    manager.add_camera(camera, is_placed=True)
    manager.add_camera(switch, is_placed=True)
    canvas.add_camera_item(camera)
    canvas.add_camera_item(switch)
    manager.add_device_link("cam_a", "switch_a")
    canvas.set_device_links(manager.get_device_links())
    canvas.set_drawing_mode(DrawingMode.SELECT)
    canvas.camera_items["cam_a"].setSelected(True)
    link_item = canvas.device_link_items[0]
    assert link_item.link_role == "upstream"
    assert link_item.pen().widthF() == 3.0
    assert link_item.pen().color().name() == "#f59e0b"
    assert link_item.shape().boundingRect().height() >= 28.0

    def fail_if_opened(_menu: QMenu, _pos: object) -> object:
        raise AssertionError("unlink menu should not open in Link mode")

    monkeypatch.setattr(QMenu, "exec", fail_if_opened)
    canvas.set_drawing_mode(DrawingMode.LINK)
    event = _ContextMenuEvent()
    link_item.contextMenuEvent(event)

    assert event.ignored
    assert len(manager.get_device_links()) == 1
    app.processEvents()


class _ContextMenuEvent:
    def __init__(self) -> None:
        self.ignored = False

    def screenPos(self) -> QPoint:
        return QPoint(0, 0)

    def ignore(self) -> None:
        self.ignored = True
