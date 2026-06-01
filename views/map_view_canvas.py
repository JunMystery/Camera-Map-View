"""Map canvas view for background images, grid display, zoom, pan, and drops."""

from typing import Any

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPixmapItem, QGraphicsView

from models.camera_data_model import Camera
from models.drawing_shape_model import DrawingShape
from views.map_canvas_actions import MapCanvasActions
from views.map_canvas_drawing_events import MapCanvasDrawingEvents
from views.map_canvas_surface import MapCanvasSurface
from views.camera_view_item import CameraItem
from views.layer_state import (
    ALL_LAYERS,
    ANNOTATION_LAYERS,
    CAMERAS_LAYER,
    DRAWINGS_LAYER,
)
from views.map_drawing_tools import DrawingMode, DrawingTool


class MapCanvas(MapCanvasSurface, MapCanvasDrawingEvents, MapCanvasActions, QGraphicsView):
    """Graphics view that displays the site map and placed camera markers."""

    camera_dropped = pyqtSignal(str, float, float)
    camera_edit_requested = pyqtSignal(str)
    camera_moved = pyqtSignal(str, float, float)
    camera_rotated = pyqtSignal(str, float)
    drawing_created = pyqtSignal(object)
    drawing_deleted = pyqtSignal(str)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.scene = BoundedGraphicsScene(self)
        self.setScene(self.scene)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setAcceptDrops(True)

        self.zoom_factor = 1.0
        self.min_zoom = 0.15
        self.max_zoom = 5.0
        self.is_panning = False
        self.pan_start_pos = QPointF()
        self.camera_items: dict[str, CameraItem] = {}
        self.grid_items: list[QGraphicsItem] = []
        self.background_item: QGraphicsPixmapItem | None = None
        self.snap_to_grid_enabled = True
        self.grid_visible = True
        self.grid_size = 20
        self.background_source_pixmap: QPixmap | None = None
        self.background_scale = 1.0
        self.drawing_mode = DrawingMode.SELECT
        self.drawing_color = "#ef4444"
        self.drawing_start_pos: QPointF | None = None
        self.freehand_points: list[QPointF] = []
        self.preview_item: QGraphicsItem | None = None
        self.drawing_tool = DrawingTool(self.snap_point)
        self.camera_info_visibility = {"name": True, "zone": False, "ip": False, "dvr": False}
        self.layer_default_names = {layer_id: layer_id.title() for layer_id in ALL_LAYERS}
        self.layer_display_names = self.layer_default_names.copy()
        self.layer_visibility = {layer_id: True for layer_id in ALL_LAYERS}
        self.layer_locked = {layer_id: False for layer_id in ALL_LAYERS}
        self.annotation_layer_order = list(ANNOTATION_LAYERS)
        self.active_layer_id = DRAWINGS_LAYER
        self.item_default_flags: dict[QGraphicsItem, QGraphicsItem.GraphicsItemFlag] = {}

        self.draw_default_grid()

    def add_camera_item(self, camera: Camera) -> CameraItem:
        """Create and add a camera item to the map."""
        self.remove_camera_item(camera.id)

        item = CameraItem(camera)
        item.set_edit_callback(self.camera_edit_requested.emit)
        item.set_move_callback(self.camera_moved.emit)
        item.set_rotation_callback(self.camera_rotated.emit)
        item.set_snap_callback(self.snap_point)
        item.set_info_visibility(self.camera_info_visibility)
        item.setData(1, "camera")
        item.setData(2, CAMERAS_LAYER)
        item.setVisible(self.layer_visibility[CAMERAS_LAYER])
        self.scene.addItem(item)
        self.camera_items[camera.id] = item
        self._set_item_locked(item, self.layer_locked[CAMERAS_LAYER])
        self.apply_layer_z_values()
        return item

    def add_drawing_shape(self, shape: DrawingShape, emit_created: bool = False) -> QGraphicsItem | None:
        """Add a persisted drawing shape to the scene."""
        item = self.drawing_tool.item_from_shape(shape)
        if item is None:
            return None

        item.setData(0, shape.id)
        item.setData(1, "drawing")
        item.setData(2, self.active_layer_id)
        item.setVisible(self.layer_visibility[item.data(2)])
        item.setFlags(
            item.flags()
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        )
        self.scene.addItem(item)
        self._set_item_locked(item, self.layer_locked[item.data(2)])
        self.apply_layer_z_values()
        if emit_created:
            self.drawing_created.emit(shape)
        return item

    def set_drawing_mode(self, mode: DrawingMode | str) -> None:
        """Switch between selection and drawing modes."""
        self.drawing_mode = DrawingMode(mode)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setCursor(Qt.CursorShape.CrossCursor if self.drawing_mode != DrawingMode.SELECT else Qt.CursorShape.ArrowCursor)

    def refresh_camera_item(self, camera: Camera) -> None:
        """Refresh an existing camera item from updated model data."""
        item = self.camera_items.get(camera.id)
        if item is None:
            return

        item.camera = camera
        item.setPos(camera.position_x, camera.position_y)
        item.update_tooltip()
        item.update()

    def update_camera_status(self, camera_id: str, is_online: bool) -> None:
        """Refresh the status indicator for a placed camera."""
        item = self.camera_items.get(camera_id)
        if item is not None:
            item.update_status(is_online)

    def retranslate_camera_items(self) -> None:
        """Refresh camera item tooltips for the active language."""
        for item in self.camera_items.values():
            item.update_tooltip()

    def remove_camera_item(self, camera_id: str) -> None:
        """Remove a camera item from the map."""
        if camera_id in self.camera_items:
            item = self.camera_items.pop(camera_id)
            self.scene.removeItem(item)

    def dragEnterEvent(self, event: Any) -> None:
        """Accept camera drags."""
        if event.mimeData().hasFormat("application/x-camera-id"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: Any) -> None:
        """Accept camera drag movement over the canvas."""
        if event.mimeData().hasFormat("application/x-camera-id"):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: Any) -> None:
        """Emit a camera placement request when a camera is dropped."""
        if event.mimeData().hasFormat("application/x-camera-id"):
            camera_id = bytes(event.mimeData().data("application/x-camera-id")).decode("utf-8")
            viewport_pos = event.position().toPoint()
            scene_pos = self.mapToScene(viewport_pos)

            self.camera_dropped.emit(camera_id, scene_pos.x(), scene_pos.y())
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def fit_in_view(self) -> None:
        """Fit the current scene into the view while preserving aspect ratio."""
        rect = self.scene.sceneRect()
        if not rect.isNull():
            self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
            self.zoom_factor = self.transform().m11()

    def wheelEvent(self, event: Any) -> None:
        """Zoom toward the mouse cursor."""
        zoom_in_factor = 1.25
        zoom_out_factor = 0.8
        old_scene_pos = self.mapToScene(event.position().toPoint())

        if event.angleDelta().y() > 0:
            new_zoom = self.zoom_factor * zoom_in_factor
            factor = zoom_in_factor
        else:
            new_zoom = self.zoom_factor * zoom_out_factor
            factor = zoom_out_factor

        if self.min_zoom <= new_zoom <= self.max_zoom:
            self.scale(factor, factor)
            self.zoom_factor = self.transform().m11()

            new_scene_pos = self.mapToScene(event.position().toPoint())
            delta = new_scene_pos - old_scene_pos
            self.translate(delta.x(), delta.y())

    def mousePressEvent(self, event: Any) -> None:
        """Start map panning when the middle button is pressed."""
        if self._start_drawing(event):
            return

        is_middle_click = event.button() == Qt.MouseButton.MiddleButton
        is_space_left_click = (
            event.button() == Qt.MouseButton.LeftButton
            and self.dragMode() == QGraphicsView.DragMode.ScrollHandDrag
        )

        if is_middle_click or is_space_left_click:
            self.is_panning = True
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            if is_middle_click:
                self.pan_start_pos = event.position()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Any) -> None:
        """Pan the map while the middle button is held."""
        if self._update_drawing_preview(event):
            return

        if self.is_panning and event.buttons() & Qt.MouseButton.MiddleButton:
            delta = event.position() - self.pan_start_pos
            self.pan_start_pos = event.position()

            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(h_bar.value() - int(delta.x()))
            v_bar.setValue(v_bar.value() - int(delta.y()))
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        """Stop map panning."""
        if self._finish_drawing(event):
            return

        if self.is_panning:
            self.is_panning = False
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: Any) -> None:
        """Enable left-button panning while Space is held."""
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: Any) -> None:
        """Disable Space-based panning."""
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().keyReleaseEvent(event)
from views.bounded_graphics_scene import BoundedGraphicsScene
