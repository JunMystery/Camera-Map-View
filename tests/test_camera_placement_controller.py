"""Tests for the camera placement controller."""

from PyQt6.QtWidgets import QApplication

from controllers.camera_data_manager import CameraDataManager
from controllers.camera_placement_controller import CameraPlacementController
from models.camera_data_model import Camera
from models.drawing_shape_model import DrawingShape
from views.camera_view_panel import CameraPanel
from views.map_drawing_tools import DrawingMode
from views.map_view_canvas import MapCanvas
from views.ui_theme import GRID_DARK, GRID_LIGHT


def test_drop_camera_persists_position_and_moves_item_to_map() -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
    controller.load_cameras()

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
    count = 0
    for group_index in range(panel.tree_widget.topLevelItemCount()):
        count += panel.tree_widget.topLevelItem(group_index).childCount()
    return count


def test_drawing_created_signal_persists_shape() -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
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
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
    controller.load_cameras()
    controller.handle_camera_dropped("cam_01", 100.0, 100.0)

    canvas.set_drawing_mode(DrawingMode.SELECT)
    canvas.camera_items["cam_01"].setSelected(True)

    assert canvas.delete_selected_drawings() == 1
    saved = manager.get_camera("cam_01")
    assert saved is not None
    assert "cam_01" not in canvas.camera_items
    assert "cam_01" in {camera.id for camera in manager.get_unplaced_cameras()}
    assert _camera_count(panel) == 5
    app.processEvents()


def test_canvas_rotates_selected_camera() -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(":memory:")
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
    controller.load_cameras()
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
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
    controller.load_cameras()
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
    panel = CameraPanel()
    canvas = MapCanvas()
    controller = CameraPlacementController(panel, canvas, manager)
    controller.load_cameras()
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

    controller.load_cameras()
    controller.handle_camera_status_updated("cam_01", True, 1.5)

    assert refresh_count >= 2
    app.processEvents()


def test_camera_panel_search_toggle_and_dvr_grouping() -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    manager = CameraDataManager(":memory:")
    manager.add_camera(Camera("cam_a", "Gate", "10.0.0.10", dvr_origin="DVR-A"))
    manager.add_camera(Camera("cam_b", "Lobby", "10.0.0.11", dvr_origin="DVR-B"))
    manager.update_camera_position("cam_b", 10, 20)

    panel.set_cameras(manager.get_all_cameras(), {"cam_b"})

    assert panel.tree_widget.topLevelItemCount() == 1
    assert panel.tree_widget.topLevelItem(0).isExpanded() is False


def test_camera_panel_preserves_expanded_group_on_refresh() -> None:
    app = QApplication.instance() or QApplication([])
    panel = CameraPanel()
    cameras = [
        Camera("cam_a", "Gate", "10.0.0.10", dvr_origin="DVR-A"),
        Camera("cam_b", "Lobby", "10.0.0.11", dvr_origin="DVR-A"),
    ]

    panel.set_cameras(cameras, set())
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
