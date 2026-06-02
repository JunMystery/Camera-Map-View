"""Map canvas view for background images, grid display, zoom, pan, and drops."""

from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import QPointF, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPainterPathStroker, QPen, QPixmap
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsLineItem, QGraphicsPixmapItem, QGraphicsView, QMenu

from config.i18n import t
from models.camera_data_model import Camera
from models.canvas_layer_model import CanvasLayer
from models.device_link_model import DeviceLink
from models.drawing_shape_model import DrawingShape
from views.map_canvas_actions import MapCanvasActions
from views.map_canvas_drawing_events import MapCanvasDrawingEvents
from views.map_canvas_surface import MapCanvasSurface
from views.camera_view_item import CameraItem
from views.ui_theme import DANGER
from views.map_drawing_tools import DrawingMode, DrawingTool


class DeviceLinkItem(QGraphicsLineItem):
    """Temporary canvas item for one visible device topology link."""

    def __init__(
        self,
        link: DeviceLink,
        line: tuple[float, float, float, float],
        delete_callback: Callable[[str, str], None],
        mode_getter: Callable[[], DrawingMode],
    ) -> None:
        super().__init__(*line)
        self.link = link
        self.delete_callback = delete_callback
        self.mode_getter = mode_getter
        self.setPen(QPen(QColor("#38bdf8"), 2.2, Qt.PenStyle.DashLine))
        self.setZValue(45)
        self.setData(0, link.id)
        self.setData(1, "device_link")
        self.setData(4, link.source_device_id)
        self.setData(5, link.target_device_id)
        self.setAcceptHoverEvents(True)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.moveTo(self.line().p1())
        path.lineTo(self.line().p2())
        stroker = QPainterPathStroker()
        stroker.setWidth(28.0)
        return stroker.createStroke(path)

    def contextMenuEvent(self, event: Any) -> None:
        if self.mode_getter() != DrawingMode.SELECT:
            event.ignore()
            return
        menu = QMenu()
        remove_action = menu.addAction(t("action.remove_device_link"))
        remove_action.triggered.connect(lambda: self.delete_callback(self.link.source_device_id, self.link.target_device_id))
        menu.exec(event.screenPos())


class MapCanvas(MapCanvasSurface, MapCanvasDrawingEvents, MapCanvasActions, QGraphicsView):
    """Graphics view that displays the site map and placed camera markers."""

    camera_dropped = pyqtSignal(str, float, float)
    camera_edit_requested = pyqtSignal(str)
    camera_location_image_requested = pyqtSignal(str)
    camera_ping_requested = pyqtSignal(str)
    camera_moved = pyqtSignal(str, float, float)
    camera_rotated = pyqtSignal(str, float)
    camera_resized = pyqtSignal(str, float)
    camera_deleted = pyqtSignal(str)
    device_link_created = pyqtSignal(str, str)
    device_link_delete_requested = pyqtSignal(str, str)
    object_layer_changed = pyqtSignal(str, str, str)
    object_renamed = pyqtSignal(str, str, str)
    object_locked_changed = pyqtSignal(str, str, bool)
    object_z_changed = pyqtSignal(str, str, int)
    drawing_created = pyqtSignal(object)
    drawing_updated = pyqtSignal(object)
    drawing_deleted = pyqtSignal(str)
    layers_changed = pyqtSignal()

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
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
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
        self.light_theme = False
        self.drawing_mode = DrawingMode.PAN
        self.drawing_color = DANGER
        self.drawing_start_pos: QPointF | None = None
        self.freehand_points: list[QPointF] = []
        self.preview_item: QGraphicsItem | None = None
        self.pending_device_link_source_id = ""
        self.device_links: list[DeviceLink] = []
        self.device_link_items: list[DeviceLinkItem] = []
        self.drawing_tool = DrawingTool(self.snap_point)
        self.camera_info_visibility = {"name": True, "zone": False, "ip": False, "dvr": False}
        self.current_layout_id = "default"
        self.canvas_layers: list[CanvasLayer] = self._fallback_layers(self.current_layout_id)
        self.layer_default_names = {layer.id: layer.name for layer in self.canvas_layers}
        self.layer_display_names = self.layer_default_names.copy()
        self.layer_visibility = {layer.id: layer.visible for layer in self.canvas_layers}
        self.layer_locked = {layer.id: layer.locked for layer in self.canvas_layers}
        self.annotation_layer_order = [layer.id for layer in self.canvas_layers]
        self.active_layer_id = self._default_layer_id("1")
        self.item_default_flags: dict[QGraphicsItem, QGraphicsItem.GraphicsItemFlag] = {}
        self.pan_item_flags: dict[QGraphicsItem, QGraphicsItem.GraphicsItemFlag] = {}
        self.item_interaction_suspended = False

        self.set_drawing_mode(DrawingMode.PAN)
        self.scene.selectionChanged.connect(self.refresh_device_links)
        self.draw_default_grid()
        QTimer.singleShot(0, self.fit_in_view)

    def add_camera_item(self, camera: Camera) -> CameraItem:
        """Create and add a camera item to the map."""
        self.remove_camera_item(camera.id)

        item = CameraItem(camera)
        item.set_light_theme(self.light_theme)
        item.set_edit_callback(self.camera_edit_requested.emit)
        item.set_location_image_callback(self.camera_location_image_requested.emit)
        item.set_ping_callback(self.camera_ping_requested.emit)
        item.set_move_callback(self.camera_moved.emit)
        item.set_rotation_callback(self.camera_rotated.emit)
        item.set_scale_callback(self.camera_resized.emit)
        item.set_snap_callback(self.snap_point)
        item.set_info_visibility(self.camera_info_visibility)
        item.setData(1, "camera")
        item.setData(6, camera.object_locked)
        item.setData(7, camera.z_index)
        layer_id = camera.layer_id or self.active_layer_id or (self.canvas_layers[0].id if self.canvas_layers else self._default_layer_id("1"))
        camera.layer_id = layer_id
        item.setData(2, layer_id)
        item.setVisible(self.layer_visibility.get(layer_id, True))
        self.scene.addItem(item)
        self.camera_items[camera.id] = item
        self._set_item_locked(item, self._item_effective_locked(item))
        self._sync_item_interaction_flags(item)
        self.apply_layer_z_values()
        self.layers_changed.emit()
        return item

    def set_light_theme(self, enabled: bool) -> None:
        """Refresh canvas and camera colors for the active theme."""
        self.light_theme = enabled
        self.redraw_grid()
        for item in self.camera_items.values():
            item.set_light_theme(enabled)

    def add_drawing_shape(self, shape: DrawingShape, emit_created: bool = False) -> QGraphicsItem | None:
        """Add a persisted drawing shape to the scene."""
        item = self.drawing_tool.item_from_shape(shape)
        if item is None:
            return None

        item.setData(0, shape.id)
        item.setData(1, "drawing")
        layer_id = shape.layer_id or self._target_layer_for_shape(shape)
        shape.layer_id = layer_id
        item.setData(2, layer_id)
        item.setData(3, shape.display_name)
        item.setData(6, shape.object_locked)
        item.setData(7, shape.z_index)
        item.setVisible(self.layer_visibility.get(layer_id, True))
        item.setFlags(
            item.flags()
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        )
        self.scene.addItem(item)
        self._set_item_locked(item, self._item_effective_locked(item))
        self._sync_item_interaction_flags(item)
        self.apply_layer_z_values()
        if emit_created:
            self.drawing_created.emit(shape)
        self.layers_changed.emit()
        return item

    def set_canvas_layers(self, layers: list[CanvasLayer], layout_id: str) -> None:
        """Load persisted layer definitions for the active layout."""
        self.current_layout_id = layout_id
        self.canvas_layers = [] if not layout_id else layers or self._fallback_layers(layout_id)
        self.layer_default_names = {layer.id: layer.name for layer in self.canvas_layers}
        self.layer_display_names = {layer.id: layer.name for layer in self.canvas_layers}
        self.layer_visibility = {layer.id: layer.visible for layer in self.canvas_layers}
        self.layer_locked = {layer.id: layer.locked for layer in self.canvas_layers}
        self.annotation_layer_order = [layer.id for layer in self.canvas_layers]
        if not self.canvas_layers:
            self.active_layer_id = ""
        elif self.active_layer_id not in self.layer_display_names:
            self.active_layer_id = self.canvas_layers[0].id if self.canvas_layers else self._default_layer_id("1")
        self.apply_layer_z_values()
        self._set_item_interaction_suspended(self.drawing_mode == DrawingMode.PAN)
        self.layers_changed.emit()

    def _default_layer_id(self, kind: str) -> str:
        return f"layer_{self.current_layout_id}_{kind}"

    def _fallback_layers(self, layout_id: str) -> list[CanvasLayer]:
        return [CanvasLayer(f"layer_{layout_id}_1", layout_id, "Layer 1", 0)]

    def _target_layer_for_shape(self, shape: DrawingShape) -> str:
        return self.active_layer_id or (self.canvas_layers[0].id if self.canvas_layers else self._default_layer_id("1"))

    def set_drawing_mode(self, mode: DrawingMode | str) -> None:
        """Switch between selection and drawing modes."""
        self.drawing_mode = DrawingMode(mode)
        self.pending_device_link_source_id = ""
        if self.drawing_mode == DrawingMode.PAN:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.scene.clearSelection()
            self._set_item_interaction_suspended(True)
            return
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self._set_item_interaction_suspended(False)
        self.setCursor(Qt.CursorShape.ArrowCursor if self.drawing_mode == DrawingMode.SELECT else Qt.CursorShape.CrossCursor)

    def set_device_links(self, links: list[DeviceLink]) -> None:
        """Replace topology links used for temporary canvas overlays."""
        self.device_links = list(links)
        self.refresh_device_links()

    def refresh_device_links(self) -> None:
        """Render only links related to the currently selected device."""
        self._remove_device_link_items()
        selected_id = self._selected_device_id()
        if not selected_id:
            return
        for link in self._related_device_links(selected_id):
            source = self.camera_items.get(link.source_device_id)
            target = self.camera_items.get(link.target_device_id)
            if source is None or target is None:
                continue
            line = DeviceLinkItem(
                link,
                (source.pos().x(), source.pos().y(), target.pos().x(), target.pos().y()),
                self.device_link_delete_requested.emit,
                lambda: self.drawing_mode,
            )
            self.scene.addItem(line)
            self.device_link_items.append(line)

    def refresh_camera_item(self, camera: Camera) -> None:
        """Refresh an existing camera item from updated model data."""
        item = self.camera_items.get(camera.id)
        if item is None:
            return

        item.camera = camera
        item.setPos(camera.position_x, camera.position_y)
        item.setScale(camera.display_scale)
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
            self.pan_item_flags.pop(item, None)
            self.item_default_flags.pop(item, None)
            self.scene.removeItem(item)
            self.layers_changed.emit()
            self.refresh_device_links()

    def dragEnterEvent(self, event: Any) -> None:
        """Accept device drags."""
        if event.mimeData().hasFormat("application/x-camera-id") or event.mimeData().hasFormat("application/x-device-id"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: Any) -> None:
        """Accept device drag movement over the canvas."""
        if event.mimeData().hasFormat("application/x-camera-id") or event.mimeData().hasFormat("application/x-device-id"):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: Any) -> None:
        """Emit a device placement request when a device is dropped."""
        mime_key = "application/x-device-id" if event.mimeData().hasFormat("application/x-device-id") else "application/x-camera-id"
        if event.mimeData().hasFormat(mime_key):
            camera_id = bytes(event.mimeData().data(mime_key)).decode("utf-8")
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
        delta_y = event.angleDelta().y()
        if delta_y == 0:
            super().wheelEvent(event)
            return

        factor = zoom_in_factor if delta_y > 0 else zoom_out_factor
        current_zoom = self.transform().m11() or self.zoom_factor or 1.0
        new_zoom = current_zoom * factor

        if new_zoom < self.min_zoom:
            factor = self.min_zoom / current_zoom
        elif new_zoom > self.max_zoom:
            factor = self.max_zoom / current_zoom

        if factor > 0:
            self.scale(factor, factor)
            self.zoom_factor = self.transform().m11()
        event.accept()

    def mousePressEvent(self, event: Any) -> None:
        """Start map panning when the middle button is pressed."""
        if self._start_drawing(event):
            return

        is_middle_click = event.button() == Qt.MouseButton.MiddleButton
        is_pan_left_click = event.button() == Qt.MouseButton.LeftButton and self.drawing_mode == DrawingMode.PAN
        is_space_left_click = event.button() == Qt.MouseButton.LeftButton and self.dragMode() == QGraphicsView.DragMode.ScrollHandDrag

        if is_middle_click or is_pan_left_click or is_space_left_click:
            self.is_panning = True
            self.pan_start_pos = event.position()
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Any) -> None:
        """Pan the map while the middle button is held."""
        if self._update_drawing_preview(event):
            return

        if self.is_panning and event.buttons() & (Qt.MouseButton.MiddleButton | Qt.MouseButton.LeftButton):
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
            if self.drawing_mode == DrawingMode.PAN:
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
                self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: Any) -> None:
        """Enable left-button panning while Space is held."""
        if event.key() == Qt.Key.Key_Escape:
            self._cancel_interaction()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: Any) -> None:
        """Disable Space-based panning."""
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            if self.drawing_mode == DrawingMode.PAN:
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
                self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def _set_item_interaction_suspended(self, suspended: bool) -> None:
        self.item_interaction_suspended = suspended
        blocked_flags = (
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
        )
        for item in self.scene.items():
            if item.data(1) not in {"camera", "drawing"}:
                continue
            if suspended:
                self.pan_item_flags.setdefault(item, item.flags())
                item.setSelected(False)
                item.setFlags(item.flags() & ~blocked_flags)
            else:
                original_flags = self.pan_item_flags.pop(item, None)
                if original_flags is not None:
                    item.setFlags(original_flags)
                self._set_item_locked(item, self._item_effective_locked(item))

    def _sync_item_interaction_flags(self, item: QGraphicsItem) -> None:
        if self.item_interaction_suspended:
            blocked_flags = (
                QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
                | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
                | QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
            )
            self.pan_item_flags.setdefault(item, item.flags())
            item.setFlags(item.flags() & ~blocked_flags)

    def _item_effective_locked(self, item: QGraphicsItem) -> bool:
        return bool(item.data(6)) or self.layer_locked.get(str(item.data(2) or ""), False)

    def _cancel_interaction(self) -> None:
        self.is_panning = False
        self.pending_device_link_source_id = ""
        self._remove_preview_item()
        self.drawing_start_pos = None
        self.freehand_points = []
        for item in self.camera_items.values():
            item.cancel_interaction()
        if self.drawing_mode == DrawingMode.PAN:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor if self.drawing_mode == DrawingMode.SELECT else Qt.CursorShape.CrossCursor)

    def _selected_device_id(self) -> str:
        for item in self.scene.selectedItems():
            if item.data(1) == "camera" and isinstance(item, CameraItem):
                return item.camera.id
        return ""

    def _related_device_links(self, root_id: str) -> list[DeviceLink]:
        related: list[DeviceLink] = []
        seen: set[str] = set()
        for link in [*self._downstream_links(root_id), *self._upstream_path_links(root_id)]:
            if link.id in seen:
                continue
            related.append(link)
            seen.add(link.id)
        return related

    def _downstream_links(self, target_id: str) -> list[DeviceLink]:
        visited = {target_id}
        related: list[DeviceLink] = []
        changed = True
        while changed:
            changed = False
            for link in self.device_links:
                if link in related or link.target_device_id not in visited:
                    continue
                related.append(link)
                if link.source_device_id not in visited:
                    visited.add(link.source_device_id)
                    changed = True
        return related

    def _upstream_path_links(self, source_id: str) -> list[DeviceLink]:
        paths = self._upstream_paths(source_id, set())
        if not paths:
            return []
        paths.sort(key=lambda path: (-len(path), [link.target_device_id for link in path], [link.source_device_id for link in path]))
        return paths[0]

    def _upstream_paths(self, source_id: str, visited: set[str]) -> list[list[DeviceLink]]:
        if source_id in visited:
            return [[]]
        outgoing = sorted(
            [link for link in self.device_links if link.source_device_id == source_id],
            key=lambda item: (item.target_device_id, item.source_device_id, item.id),
        )
        if not outgoing:
            return []
        paths: list[list[DeviceLink]] = []
        next_visited = {*visited, source_id}
        for link in outgoing:
            child_paths = self._upstream_paths(link.target_device_id, next_visited)
            if not child_paths:
                paths.append([link])
            else:
                paths.extend([[link, *path] for path in child_paths])
        return paths

    def _remove_device_link_items(self) -> None:
        for item in self.device_link_items:
            if item.scene() is self.scene:
                self.scene.removeItem(item)
        self.device_link_items.clear()
from views.bounded_graphics_scene import BoundedGraphicsScene
