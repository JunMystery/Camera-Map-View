"""Tests for geometry helpers and snap behavior."""

from PyQt6.QtCore import QByteArray, QMimeData, QPointF, Qt
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication, QDialogButtonBox

from models.camera_data_model import Camera
from models.drawing_shape_model import DrawingShape
from utils.geometry import snap_to_grid
from config.i18n import set_language
from views.camera_view_dialog import CameraPropertiesDialog
from views.layer_state import BACKGROUND_LAYER, CAMERAS_LAYER, DRAWINGS_LAYER, GRID_LAYER, IMAGES_LAYER, TEXT_LAYER
from views.map_drawing_tools import DrawingMode
from views.map_view_canvas import MapCanvas


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


def test_camera_dialog_translates_camera_type_labels_without_changing_value() -> None:
    app = QApplication.instance() or QApplication([])
    set_language("jp")
    dialog = CameraPropertiesDialog(Camera("cam", "Lobby", "10.0.0.10", camera_type="Fixed"))

    assert dialog.type_input.currentText() == "固定"
    assert dialog.get_camera().camera_type == "Fixed"

    set_language("vi")
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


def test_canvas_layer_visibility_lock_and_selection() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    camera_item = canvas.add_camera_item(Camera("cam_test", "Lobby", "10.0.0.10"))
    drawing_item = canvas.add_drawing_shape(DrawingShape("shape_test", "Line", [0.0, 0.0, 40.0, 40.0]))
    assert drawing_item is not None

    canvas.set_layer_visible(GRID_LAYER, False)
    canvas.set_layer_visible(CAMERAS_LAYER, False)
    canvas.set_layer_visible(DRAWINGS_LAYER, False)

    assert all(not item.isVisible() for item in canvas.grid_items)
    assert not camera_item.isVisible()
    assert not drawing_item.isVisible()

    canvas.set_layer_visible(CAMERAS_LAYER, True)
    canvas.set_layer_locked(CAMERAS_LAYER, True)
    assert not camera_item.flags() & camera_item.GraphicsItemFlag.ItemIsMovable
    assert canvas.select_layer_items(CAMERAS_LAYER) == 0

    canvas.set_layer_locked(CAMERAS_LAYER, False)
    assert canvas.select_layer_items(CAMERAS_LAYER) == 1
    assert camera_item.isSelected()
    app.processEvents()


def test_canvas_delete_layer_items_emits_persistence_signal(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    deleted = []
    canvas.drawing_deleted.connect(deleted.append)
    assert canvas.set_active_layer(TEXT_LAYER)
    text_item = canvas.add_drawing_shape(DrawingShape("text_test", "Text", [1.0, 2.0], label="Hello"))
    image_path = tmp_path / "layer.png"
    image = QImage(32, 32, QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    assert image.save(str(image_path))
    assert canvas.set_active_layer(IMAGES_LAYER)
    image_item = canvas.add_drawing_shape(DrawingShape("image_test", "Image", [1.0, 2.0, 32.0, 32.0], image_path=str(image_path)))

    assert text_item is not None
    assert image_item is not None
    assert canvas.delete_layer_items(TEXT_LAYER) == 1
    assert deleted == ["text_test"]

    assert canvas.delete_layer_items(IMAGES_LAYER) == 1
    assert deleted == ["text_test", "image_test"]
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
    assert canvas.set_active_layer(TEXT_LAYER)
    text_item = canvas.add_drawing_shape(DrawingShape("text_test", "Text", [1.0, 2.0], label="Hello"))

    assert canvas.delete_layer_items(BACKGROUND_LAYER) == 1
    assert canvas.background_item is None
    assert drawing_item is not None
    assert drawing_item.scene() is canvas.scene

    assert text_item is not None
    before = text_item.zValue()
    assert canvas.move_layer(TEXT_LAYER, -1)
    assert text_item.zValue() < before
    app.processEvents()


def test_canvas_draws_new_items_into_active_layer() -> None:
    app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    assert canvas.set_active_layer(TEXT_LAYER)

    item = canvas.add_drawing_shape(DrawingShape("shape_test", "Line", [0.0, 0.0, 40.0, 40.0]))

    assert item is not None
    assert item.data(2) == TEXT_LAYER
    assert canvas.select_layer_items(TEXT_LAYER) == 1
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
