"""Tests for the camera placement controller."""

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QApplication, QMenu

from controllers.camera_data_manager import CameraDataManager
from controllers.camera_placement_controller import CameraPlacementController
from models.camera_data_model import Camera
from models.device_catalog import DEVICE_KIND_SERVER, DEVICE_KIND_SWITCH
from models.drawing_shape_model import DrawingShape
from views.control_layout_panel import ControlLayoutPanel as CameraPanel
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
    switch = Camera("switch_a", "Switch A", "", device_kind=DEVICE_KIND_SWITCH, variant="Core", ping_enabled=False)
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
    assert "Server A" in root.text(0)
    assert "Switch A" in root.child(0).text(0)
    assert "Lobby" in root.child(0).child(0).text(0)

    panel.search_input.setText("Lobby")
    assert _camera_count(panel) == 1
    panel.search_input.clear()
    panel.unplaced_button.click()
    assert _camera_count(panel) == 1
    assert "Gate" in panel.tree_widget.topLevelItem(0).child(0).text(0)
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


def test_canvas_device_link_context_menu_removes_one_link(monkeypatch) -> None:
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

    def choose_remove(menu: QMenu, _pos: object) -> object:
        menu.actions()[0].trigger()
        return menu.actions()[0]

    monkeypatch.setattr(QMenu, "exec", choose_remove)
    canvas.device_link_items[0].contextMenuEvent(_ContextMenuEvent())

    links = manager.get_device_links()
    assert len(links) == 1
    assert {(link.source_device_id, link.target_device_id) for link in links} in [
        {("cam_a", "switch_a")},
        {("cam_b", "switch_a")},
    ]
    assert len(canvas.device_link_items) == 1
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
    assert link_item.pen().widthF() == 2.2
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
