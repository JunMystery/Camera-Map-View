"""Map canvas view for background images, grid display, zoom, pan, and drops."""

from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import QPointF, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPainterPathStroker, QPen, QPixmap
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsLineItem, QGraphicsPixmapItem, QGraphicsView

from models.camera_data_model import Camera
from models.canvas_layer_model import CanvasLayer
from models.device_link_model import DeviceLink
from models.drawing_shape_model import DrawingShape
from views.map_canvas_actions import MapCanvasActions
from views.map_canvas_drawing_events import MapCanvasDrawingEvents
from views.map_canvas_surface import MapCanvasSurface
from views.camera_view_item import CameraItem
from views.ui_theme import CANVAS_BG_DARK, CANVAS_BG_LIGHT, DANGER
from views.map_drawing_tools import DrawingMode, DrawingTool


class DeviceLinkItem(QGraphicsLineItem):
    """Temporary canvas item for one visible device topology link."""

    def __init__(
        self,
        link: DeviceLink,
        line: tuple[float, float, float, float],
        delete_callback: Callable[[str, str], None],
        mode_getter: Callable[[], DrawingMode],
        link_role: str = "downstream",
    ) -> None:
        super().__init__(*line)
        self.link = link
        self.delete_callback = delete_callback
        self.mode_getter = mode_getter
        self.link_role = link_role if link_role == "upstream" else "downstream"
        self._dash_offset = 0.0
        self._apply_pen()
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
        event.ignore()

    def set_dash_offset(self, offset: float) -> None:
        """Update the shared dash animation phase."""
        self._dash_offset = offset % 12.0
        self._apply_pen()

    def stop_animation(self) -> None:
        """Compatibility hook for scene cleanup."""
        return

    def _apply_pen(self) -> None:
        color = "#f59e0b" if self.link_role == "upstream" else "#38bdf8"
        width = 3.0 if self.link_role == "upstream" else 2.2
        pen = QPen(QColor(color), width, Qt.PenStyle.CustomDashLine)
        pen.setDashPattern([6.0, 4.0])
        pen.setDashOffset(self._dash_offset)
        self.setPen(pen)


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
    object_visibility_changed = pyqtSignal(str, str, bool)
    object_z_changed = pyqtSignal(str, str, int)
    drawing_created = pyqtSignal(object)
    drawing_updated = pyqtSignal(object)
    drawing_deleted = pyqtSignal(str)
    layers_changed = pyqtSignal()
    history_step_started = pyqtSignal(str)
    history_step_finished = pyqtSignal(str)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.scene = BoundedGraphicsScene(self)
        self.setScene(self.scene)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setAcceptDrops(True)
        self.setRubberBandSelectionMode(Qt.ItemSelectionMode.IntersectsItemShape)

        self.zoom_factor = 1.0
        self.min_zoom = 0.15
        self.max_zoom = 5.0
        self.is_panning = False
        self.pan_start_pos = QPointF()
        self.camera_items: dict[str, CameraItem] = {}
        self.device_catalog: dict[str, Camera] = {}
        self.grid_items: list[QGraphicsItem] = []
        self.background_item: QGraphicsPixmapItem | None = None
        self.canvas_bounds_item: QGraphicsItem | None = None
        self.background_map_visible = True
        self.snap_to_grid_enabled = False
        self.grid_visible = False
        self.grid_size = 20
        self.background_source_pixmap: QPixmap | None = None
        self.background_scale = 1.0
        self.light_theme = False
        self._apply_canvas_background()
        self.drawing_mode = DrawingMode.PAN
        self.drawing_color = DANGER
        self.drawing_fill_color = ""
        self.drawing_start_pos: QPointF | None = None
        self.freehand_points: list[QPointF] = []
        self.preview_item: QGraphicsItem | None = None
        self.pending_device_link_source_id = ""
        self.device_links: list[DeviceLink] = []
        self.device_link_items: list[DeviceLinkItem] = []
        self._links_by_source: dict[str, list[DeviceLink]] = {}
        self._links_by_target: dict[str, list[DeviceLink]] = {}
        self._link_dash_offset = 0.0
        self.link_animation_timer = QTimer(self)
        self.link_animation_timer.timeout.connect(self._advance_link_dash)
        self.drawing_tool = DrawingTool(self.snap_point)
        self.camera_info_visibility = {"name": False, "zone": False, "ip": False}
        self.current_layout_id = "default"
        self.canvas_layers: list[CanvasLayer] = self._fallback_layers(self.current_layout_id)
        self.layer_default_names = {layer.id: layer.name for layer in self.canvas_layers}
        self.layer_display_names = self.layer_default_names.copy()
        self.layer_visibility = {layer.id: layer.visible for layer in self.canvas_layers}
        self.layer_locked = {layer.id: layer.locked for layer in self.canvas_layers}
        self.annotation_layer_order = [layer.id for layer in self.canvas_layers if not layer.is_group]
        self.active_layer_id = self._default_layer_id("1")
        self.item_default_flags: dict[QGraphicsItem, QGraphicsItem.GraphicsItemFlag] = {}
        self.pan_item_flags: dict[QGraphicsItem, QGraphicsItem.GraphicsItemFlag] = {}
        self.item_interaction_suspended = False
        self._interaction_history_active = False
        self._priority_raised_item: QGraphicsItem | None = None
        self._priority_raised_z = 0.0
        self._layers_changed_suspend_count = 0
        self._layers_changed_pending = False
        self.topology_focus_id = ""
        self.topology_highlight_ids: set[str] = set()
        self.topology_upstream_link_ids: set[str] = set()
        self.topology_blink_phase = False
        self._applying_topology_highlight = False
        self.topology_blink_timer = QTimer(self)
        self.topology_blink_timer.timeout.connect(self._advance_topology_blink)
        self.topology_blink_timer.start(450)

        self.set_drawing_mode(DrawingMode.PAN)
        self.scene.selectionChanged.connect(self._handle_selection_changed)
        self.draw_default_grid()
        QTimer.singleShot(0, self.fit_in_view)

    def add_camera_item(self, camera: Camera) -> CameraItem:
        """Create and add a camera item to the map."""
        self.remove_camera_item(camera.id)
        self.device_catalog[camera.id] = camera

        item = CameraItem(camera)
        item.set_light_theme(self.light_theme)
        item.set_edit_callback(self.camera_edit_requested.emit)
        item.set_location_image_callback(self.camera_location_image_requested.emit)
        item.set_ping_callback(self.camera_ping_requested.emit)
        item.set_move_callback(self.camera_moved.emit)
        item.set_rotation_callback(self.camera_rotated.emit)
        item.set_scale_callback(self.camera_resized.emit)
        item.set_snap_callback(self.snap_point)
        item.set_parent_ip_callback(self.parent_ip_for_device)
        item.set_info_visibility(self.camera_info_visibility)
        item.setData(1, "camera")
        item.setData(6, camera.object_locked)
        item.setData(7, camera.z_index)
        item.setData(9, camera.object_visible)
        layer_id = camera.layer_id or self.active_layer_id or (self.canvas_layers[0].id if self.canvas_layers else self._default_layer_id("1"))
        camera.layer_id = layer_id
        item.setData(2, layer_id)
        self.scene.addItem(item)
        self._apply_item_visibility(item)
        self.camera_items[camera.id] = item
        self._set_item_locked(item, self._item_effective_locked(item))
        self._sync_item_interaction_flags(item)
        self.apply_layer_z_values()
        self._emit_layers_changed()
        return item

    def set_light_theme(self, enabled: bool) -> None:
        """Refresh canvas and camera colors for the active theme."""
        self.light_theme = enabled
        self._apply_canvas_background()
        self.redraw_grid()
        for item in self.camera_items.values():
            item.set_light_theme(enabled)

    def add_drawing_shape(self, shape: DrawingShape, emit_created: bool = False) -> QGraphicsItem | None:
        """Add a persisted drawing shape to the scene."""
        if emit_created:
            self._begin_history_step("drawing_create")
        item = self.drawing_tool.item_from_shape(shape)
        if item is None:
            if emit_created:
                self._commit_history_step("drawing_create")
            return None

        item.setData(0, shape.id)
        item.setData(1, "drawing")
        layer_id = shape.layer_id or self._target_layer_for_shape(shape)
        shape.layer_id = layer_id
        item.setData(2, layer_id)
        item.setData(3, shape.display_name)
        item.setData(4, shape.image_path)
        item.setData(6, shape.object_locked)
        item.setData(7, shape.z_index)
        item.setData(8, shape.shape_type)
        item.setData(9, shape.object_visible)
        item.setFlags(
            item.flags()
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        )
        self.scene.addItem(item)
        self._apply_item_visibility(item)
        self._set_item_locked(item, self._item_effective_locked(item))
        self._sync_item_interaction_flags(item)
        self.apply_layer_z_values()
        if emit_created:
            self.drawing_created.emit(shape)
        self._emit_layers_changed()
        if emit_created:
            self._commit_history_step("drawing_create")
        return item

    def set_canvas_layers(self, layers: list[CanvasLayer], layout_id: str) -> None:
        """Load persisted layer definitions for the active layout."""
        self.current_layout_id = layout_id
        self.canvas_layers = [] if not layout_id else layers or self._fallback_layers(layout_id)
        self.layer_default_names = {layer.id: layer.name for layer in self.canvas_layers}
        self.layer_display_names = {layer.id: layer.name for layer in self.canvas_layers}
        self.layer_visibility = {layer.id: layer.visible for layer in self.canvas_layers}
        self.layer_locked = {layer.id: layer.locked for layer in self.canvas_layers}
        self.annotation_layer_order = [layer.id for layer in self.canvas_layers if not layer.is_group]
        if not self.canvas_layers:
            self.active_layer_id = ""
        elif self.active_layer_id not in self.annotation_layer_order:
            self.active_layer_id = self.annotation_layer_order[0] if self.annotation_layer_order else ""
        self.apply_layer_z_values()
        self._set_item_interaction_suspended(self.drawing_mode == DrawingMode.PAN)
        self._emit_layers_changed()

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
        if self.drawing_mode != DrawingMode.SELECT:
            self.clear_topology_highlight()
        if self.drawing_mode == DrawingMode.PAN:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.scene.clearSelection()
            self._set_item_interaction_suspended(True)
            return
        self.setDragMode(self._drag_mode_for_current_mode())
        self._set_item_interaction_suspended(False)
        self.setCursor(Qt.CursorShape.ArrowCursor if self.drawing_mode == DrawingMode.SELECT else Qt.CursorShape.CrossCursor)

    def set_device_links(self, links: list[DeviceLink]) -> None:
        """Replace topology links used for temporary canvas overlays."""
        self.device_links = list(links)
        self._rebuild_device_link_index()
        for item in self.camera_items.values():
            item.update_tooltip()
            item.update()
        self.refresh_device_links()

    def set_device_catalog(self, cameras: list[Camera]) -> None:
        """Replace lookup data for all devices in the active layout."""
        self.device_catalog = {camera.id: camera for camera in cameras}
        for item in self.camera_items.values():
            if item.camera.id in self.device_catalog:
                item.camera = self.device_catalog[item.camera.id]
            item.update_tooltip()
            item.update()

    def parent_ip_for_device(self, device_id: str) -> str:
        """Return direct parent IP addresses for one device from current canvas links."""
        parent_ids = sorted(
            {link.target_device_id for link in self.device_links if link.source_device_id == device_id},
            key=lambda item: (
                self.device_catalog[item].name if item in self.device_catalog else item,
                self.device_catalog[item].ip_address if item in self.device_catalog else "",
                item,
            ),
        )
        ips = [
            self.device_catalog[parent_id].ip_address
            for parent_id in parent_ids
            if parent_id in self.device_catalog and self.device_catalog[parent_id].ip_address
        ]
        return ", ".join(dict.fromkeys(ips))

    def refresh_device_links(self) -> None:
        """Render topology links related to the single selected device."""
        self._remove_device_link_items()
        selected_id = self._selected_device_id()
        if not selected_id:
            self._sync_link_animation_timer()
            return
        downstream_links = self._downstream_links(selected_id)
        upstream_links = self._upstream_path_links(selected_id)
        related_links = [*downstream_links, *upstream_links]
        seen: set[str] = set()
        upstream_ids = {link.id for link in upstream_links}
        for link in related_links:
            if link.id in seen:
                continue
            seen.add(link.id)
            source = self.camera_items.get(link.source_device_id)
            target = self.camera_items.get(link.target_device_id)
            if source is None or target is None:
                continue
            line = DeviceLinkItem(
                link,
                (source.pos().x(), source.pos().y(), target.pos().x(), target.pos().y()),
                self._request_delete_device_link,
                lambda: self.drawing_mode,
                "upstream" if link.id in upstream_ids else "downstream",
            )
            self.scene.addItem(line)
            self.device_link_items.append(line)
        self._sync_link_animation_timer()

    def highlight_device_topology(self, device_id: str, center: bool = True) -> bool:
        """Select one device and highlight its upstream path plus downstream subtree."""
        item = self.camera_items.get(device_id)
        if item is None or self._item_effective_locked(item) or not item.isVisible():
            self.clear_topology_highlight()
            return False

        return self._set_topology_focus(device_id, center=center, select_item=True)

    def _set_topology_focus(self, device_id: str, center: bool = False, select_item: bool = False) -> bool:
        item = self.camera_items.get(device_id)
        if item is None or self._item_effective_locked(item) or not item.isVisible():
            self.clear_topology_highlight()
            return False

        downstream_links = self._downstream_links(device_id)
        upstream_links = self._upstream_path_links(device_id)
        highlight_ids = {device_id}
        for link in [*downstream_links, *upstream_links]:
            highlight_ids.update({link.source_device_id, link.target_device_id})

        self._applying_topology_highlight = True
        try:
            if select_item:
                self.scene.clearSelection()
                item.setSelected(True)
            if center:
                self.centerOn(item)
            self.topology_focus_id = device_id
            self.topology_highlight_ids = highlight_ids
            self.topology_upstream_link_ids = {link.id for link in upstream_links}
            self._apply_topology_highlight_roles()
            self.refresh_device_links()
        finally:
            self._applying_topology_highlight = False
        return True

    def clear_topology_highlight(self) -> None:
        """Clear transient topology highlight state without changing persisted data."""
        if not self.topology_focus_id and not self.topology_highlight_ids:
            return
        self.topology_focus_id = ""
        self.topology_highlight_ids = set()
        self.topology_upstream_link_ids = set()
        for item in self.camera_items.values():
            item.set_topology_highlight("")

    def _handle_selection_changed(self) -> None:
        if self._applying_topology_highlight:
            return
        selected_id = self._selected_device_id()
        if selected_id:
            self._set_topology_focus(selected_id, center=False, select_item=False)
            return
        if self.topology_focus_id:
            self.clear_topology_highlight()
        self.refresh_device_links()

    def _advance_topology_blink(self) -> None:
        if not self.topology_highlight_ids:
            return
        self.topology_blink_phase = not self.topology_blink_phase
        self._apply_topology_highlight_roles()

    def _apply_topology_highlight_roles(self) -> None:
        for camera_id, item in self.camera_items.items():
            if camera_id == self.topology_focus_id:
                item.set_topology_highlight("selected", self.topology_blink_phase)
            elif camera_id in self.topology_highlight_ids:
                item.set_topology_highlight("related", self.topology_blink_phase)
            else:
                item.set_topology_highlight("")

    def refresh_camera_item(self, camera: Camera) -> None:
        """Refresh an existing camera item from updated model data."""
        item = self.camera_items.get(camera.id)
        if item is None:
            return

        item.camera = camera
        self.device_catalog[camera.id] = camera
        item.set_parent_ip_callback(self.parent_ip_for_device)
        item.setData(9, camera.object_visible)
        item.setPos(camera.position_x, camera.position_y)
        item.setScale(camera.display_scale)
        self._apply_item_visibility(item)
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
            self._emit_layers_changed()
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

            self._begin_history_step("camera_drop")
            self.camera_dropped.emit(camera_id, scene_pos.x(), scene_pos.y())
            self._commit_history_step("camera_drop")
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def fit_in_view(self) -> None:
        """Fit the current scene into the view while preserving aspect ratio."""
        rect = self.scene.sceneRect()
        if not rect.isNull():
            self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
            self.zoom_factor = self.transform().m11()

    def export_snapshot(self, path: str) -> bool:
        """Render the whole visible scene to an image file without UI chrome or selection handles."""
        rect = self.scene.sceneRect()
        if rect.isNull() or rect.width() <= 0 or rect.height() <= 0:
            return False
        if rect.width() * rect.height() > 80_000_000:
            return False

        image = QImage(int(rect.width()), int(rect.height()), QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        selected_items = [item for item in self.scene.selectedItems()]
        bounds_visible = bool(self.canvas_bounds_item is not None and self.canvas_bounds_item.isVisible())

        self.scene.clearSelection()
        if self.canvas_bounds_item is not None:
            self.canvas_bounds_item.setVisible(False)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.scene.render(painter)
        painter.end()
        if self.canvas_bounds_item is not None:
            self.canvas_bounds_item.setVisible(bounds_visible)

        for item in selected_items:
            if item.scene() is self.scene and item.isVisible():
                item.setSelected(True)
        self.refresh_device_links()

        image_format = "JPG" if path.lower().endswith((".jpg", ".jpeg")) else "PNG"
        return image.save(path, image_format, 92)

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

        self._raise_priority_item_for_press(event)
        self._maybe_begin_select_interaction_history(event)
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
                self.setDragMode(self._drag_mode_for_current_mode())
                self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        super().mouseReleaseEvent(event)
        self._restore_priority_raised_item()
        self._commit_select_interaction_history()

    def keyPressEvent(self, event: Any) -> None:
        """Enable left-button panning while Space is held."""
        if event.key() == Qt.Key.Key_Escape:
            self._cancel_interaction()
            self._commit_select_interaction_history()
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
                self.setDragMode(self._drag_mode_for_current_mode())
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
        layer_id = str(item.data(2) or "")
        group_id = next((layer.group_id for layer in self.canvas_layers if layer.id == layer_id), "")
        return bool(item.data(6)) or self.layer_locked.get(layer_id, False) or self.layer_locked.get(group_id, False)

    def _item_object_visible(self, item: QGraphicsItem) -> bool:
        value = item.data(9)
        return True if value is None else bool(value)

    def _apply_item_visibility(self, item: QGraphicsItem) -> None:
        layer_id = str(item.data(2) or "")
        visible = self.layer_visibility.get(layer_id, True) and self._group_visible_for_layer(layer_id) and self._item_object_visible(item)
        if item is self.background_item:
            visible = visible and self.background_map_visible
        item.setVisible(visible)

    def _group_visible_for_layer(self, layer_id: str) -> bool:
        group_id = next((layer.group_id for layer in self.canvas_layers if layer.id == layer_id), "")
        return self.layer_visibility.get(group_id, True) if group_id else True

    def _cancel_interaction(self) -> None:
        self.is_panning = False
        self.pending_device_link_source_id = ""
        self._remove_preview_item()
        self.drawing_start_pos = None
        self.freehand_points = []
        for item in self.camera_items.values():
            item.cancel_interaction()
        for item in self.scene.items():
            if item.data(1) == "drawing" and hasattr(item, "cancel_interaction"):
                item.cancel_interaction()
        if self.drawing_mode == DrawingMode.PAN:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setDragMode(self._drag_mode_for_current_mode())
            self.setCursor(Qt.CursorShape.ArrowCursor if self.drawing_mode == DrawingMode.SELECT else Qt.CursorShape.CrossCursor)

    def _selected_device_id(self) -> str:
        selected = [item.camera.id for item in self.scene.selectedItems() if item.data(1) == "camera" and isinstance(item, CameraItem)]
        return selected[0] if len(selected) == 1 else ""

    def _drag_mode_for_current_mode(self) -> QGraphicsView.DragMode:
        if self.drawing_mode == DrawingMode.SELECT:
            return QGraphicsView.DragMode.RubberBandDrag
        return QGraphicsView.DragMode.NoDrag

    def _apply_canvas_background(self) -> None:
        """Apply a view-only canvas background that is not part of scene exports."""
        color = CANVAS_BG_LIGHT if self.light_theme else CANVAS_BG_DARK
        self.setBackgroundBrush(QBrush(QColor(color)))

    def _begin_history_step(self, label: str) -> None:
        self.history_step_started.emit(label)

    def _commit_history_step(self, label: str) -> None:
        self.history_step_finished.emit(label)

    def _maybe_begin_select_interaction_history(self, event: Any) -> None:
        if self.drawing_mode != DrawingMode.SELECT or event.button() != Qt.MouseButton.LeftButton:
            return
        item = self.itemAt(event.position().toPoint())
        if item is None or item.data(1) not in {"camera", "drawing"}:
            return
        self._interaction_history_active = True
        self._begin_history_step("canvas_interaction")

    def _commit_select_interaction_history(self) -> None:
        if not self._interaction_history_active:
            return
        self._persist_selected_drawing_positions()
        self._interaction_history_active = False
        self._commit_history_step("canvas_interaction")

    def _raise_priority_item_for_press(self, event: Any) -> None:
        if self.drawing_mode != DrawingMode.SELECT or event.button() != Qt.MouseButton.LeftButton:
            return
        if self._clicked_selected_transform_handle(event):
            return
        top_item = self.top_selectable_item_at(event.position().toPoint())
        default_item = self.itemAt(event.position().toPoint())
        if top_item is None or top_item is default_item:
            return
        self._priority_raised_item = top_item
        self._priority_raised_z = float(top_item.zValue())
        highest_z = max((float(item.zValue()) for item in self.scene.items()), default=self._priority_raised_z)
        top_item.setZValue(highest_z + 10000.0)

    def _restore_priority_raised_item(self) -> None:
        if self._priority_raised_item is None:
            return
        if self._priority_raised_item.scene() is self.scene:
            self._priority_raised_item.setZValue(self._priority_raised_z)
        self._priority_raised_item = None
        self._priority_raised_z = 0.0

    def _clicked_selected_transform_handle(self, event: Any) -> bool:
        scene_pos = self.mapToScene(event.position().toPoint())
        for item in self.scene.selectedItems():
            if not hasattr(item, "_handle_at"):
                continue
            local_pos = item.mapFromScene(scene_pos)
            handle_at = getattr(item, "_handle_at", None)
            rotation_rect = getattr(item, "_rotation_handle_rect", None)
            if callable(handle_at) and handle_at(local_pos):
                return True
            if callable(rotation_rect) and rotation_rect().contains(local_pos):
                return True
        return False

    def _request_delete_device_link(self, source_device_id: str, target_device_id: str) -> None:
        self._begin_history_step("device_link_delete")
        self.device_link_delete_requested.emit(source_device_id, target_device_id)
        self._commit_history_step("device_link_delete")

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
        queue = [target_id]
        seen_links: set[str] = set()
        while queue:
            current_target = queue.pop(0)
            for link in self._links_by_target.get(current_target, []):
                if link.id in seen_links:
                    continue
                seen_links.add(link.id)
                related.append(link)
                if link.source_device_id not in visited:
                    visited.add(link.source_device_id)
                    queue.append(link.source_device_id)
        return related

    def _upstream_path_links(self, source_id: str) -> list[DeviceLink]:
        return self._best_upstream_path(source_id, set(), {})

    def _best_upstream_path(
        self,
        source_id: str,
        visited: set[str],
        memo: dict[str, list[DeviceLink]],
    ) -> list[DeviceLink]:
        if source_id in visited:
            return []
        if source_id in memo:
            return list(memo[source_id])
        outgoing = sorted(
            self._links_by_source.get(source_id, []),
            key=lambda item: (item.target_device_id, item.source_device_id, item.id),
        )
        if not outgoing:
            memo[source_id] = []
            return []
        next_visited = {*visited, source_id}
        best: list[DeviceLink] = []
        for link in outgoing:
            candidate = [link, *self._best_upstream_path(link.target_device_id, next_visited, memo)]
            if len(candidate) > len(best) or (
                len(candidate) == len(best)
                and [item.target_device_id for item in candidate] < [item.target_device_id for item in best]
            ):
                best = candidate
        memo[source_id] = list(best)
        return best

    def _remove_device_link_items(self) -> None:
        for item in self.device_link_items:
            item.stop_animation()
            if item.scene() is self.scene:
                self.scene.removeItem(item)
        self.device_link_items.clear()
        self._sync_link_animation_timer()

    def _emit_layers_changed(self) -> None:
        """Emit the expensive layer refresh signal, or defer it during bulk work."""
        if self._layers_changed_suspend_count > 0:
            self._layers_changed_pending = True
            return
        self.layers_changed.emit()

    def suspend_layer_refresh(self) -> None:
        """Suspend LayersPanel rebuilds while loading many scene items."""
        self._layers_changed_suspend_count += 1

    def resume_layer_refresh(self) -> None:
        """Resume LayersPanel rebuilds and flush one pending update."""
        self._layers_changed_suspend_count = max(0, self._layers_changed_suspend_count - 1)
        if self._layers_changed_suspend_count == 0 and self._layers_changed_pending:
            self._layers_changed_pending = False
            self.layers_changed.emit()

    def notify_geometry_changed(self) -> None:
        """Refresh lightweight overlays after item movement without rebuilding layers."""
        self._update_device_link_item_positions()

    def _rebuild_device_link_index(self) -> None:
        self._links_by_source = {}
        self._links_by_target = {}
        for link in self.device_links:
            self._links_by_source.setdefault(link.source_device_id, []).append(link)
            self._links_by_target.setdefault(link.target_device_id, []).append(link)

    def _advance_link_dash(self) -> None:
        self._link_dash_offset = (self._link_dash_offset + 1.0) % 12.0
        for item in self.device_link_items:
            item.set_dash_offset(self._link_dash_offset)

    def _update_device_link_item_positions(self) -> None:
        for link_item in self.device_link_items:
            source = self.camera_items.get(link_item.link.source_device_id)
            target = self.camera_items.get(link_item.link.target_device_id)
            if source is None or target is None:
                continue
            link_item.setLine(source.pos().x(), source.pos().y(), target.pos().x(), target.pos().y())

    def _sync_link_animation_timer(self) -> None:
        if self.device_link_items and not self.link_animation_timer.isActive():
            self.link_animation_timer.start(90)
        elif not self.device_link_items and self.link_animation_timer.isActive():
            self.link_animation_timer.stop()
from views.bounded_graphics_scene import BoundedGraphicsScene
