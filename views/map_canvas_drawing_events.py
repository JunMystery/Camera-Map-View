"""Drawing event helpers for the map canvas widget."""

from typing import Any

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtWidgets import QGraphicsItem

from models.drawing_shape_model import DrawingShape
from views.camera_view_item import CameraItem
from views.map_drawing_tools import DrawingMode


class MapCanvasDrawingEvents:
    """Handle drawing-mode mouse events and shape layer mapping."""

    def _start_drawing(self, event: Any) -> bool:
        if self.drawing_mode == DrawingMode.LINK and event.button() == Qt.MouseButton.LeftButton:
            return self._handle_device_link_click(event)
        if self.drawing_mode in {DrawingMode.PAN, DrawingMode.SELECT} or event.button() != Qt.MouseButton.LeftButton:
            return False
        self.drawing_start_pos = self.mapToScene(event.position().toPoint())
        self.freehand_points = [self.drawing_start_pos]
        event.accept()
        return True

    def _update_drawing_preview(self, event: Any) -> bool:
        if self.drawing_mode == DrawingMode.LINK:
            return False
        if self.drawing_start_pos is None or self.drawing_mode in {DrawingMode.PAN, DrawingMode.SELECT}:
            return False
        current_pos = self.mapToScene(event.position().toPoint())
        if self.drawing_mode == DrawingMode.FREEHAND:
            self.freehand_points.append(current_pos)
        self._remove_preview_item()
        self.preview_item = self._create_preview_item(self.drawing_start_pos, current_pos)
        if self.preview_item is not None:
            self.preview_item.setZValue(5)
            self.scene.addItem(self.preview_item)
        event.accept()
        return True

    def _finish_drawing(self, event: Any) -> bool:
        if self.drawing_mode == DrawingMode.LINK:
            return False
        if self.drawing_start_pos is None or self.drawing_mode in {DrawingMode.PAN, DrawingMode.SELECT}:
            return False
        end_pos = self.mapToScene(event.position().toPoint())
        start_pos = self.drawing_start_pos
        self.drawing_start_pos = None
        self._remove_preview_item()
        if self.drawing_mode == DrawingMode.FREEHAND:
            self.freehand_points.append(end_pos)
            shape = self.drawing_tool.freehand_shape(self.freehand_points, self.drawing_color)
            self.freehand_points = []
        else:
            shape = self._shape_from_points(start_pos, end_pos)
        if shape is not None:
            self.add_drawing_shape(shape, emit_created=True)
        event.accept()
        return True

    def _remove_preview_item(self) -> None:
        if self.preview_item is not None:
            self.scene.removeItem(self.preview_item)
            self.preview_item = None

    def _create_preview_item(self, start_pos: QPointF, end_pos: QPointF) -> QGraphicsItem | None:
        if self.drawing_mode == DrawingMode.FREEHAND:
            shape = self.drawing_tool.freehand_shape(self.freehand_points, self.drawing_color)
            return self.drawing_tool.item_from_shape(shape)
        shape = self._shape_from_points(start_pos, end_pos)
        return self.drawing_tool.item_from_shape(shape) if shape is not None else None

    def _shape_from_points(self, start_pos: QPointF, end_pos: QPointF) -> DrawingShape | None:
        return self.drawing_tool.shape_from_points(
            self.drawing_mode,
            start_pos,
            end_pos,
            self.drawing_color,
            getattr(self, "drawing_fill_color", ""),
        )

    def _handle_device_link_click(self, event: Any) -> bool:
        item = self.itemAt(event.position().toPoint())
        if not isinstance(item, CameraItem):
            return False
        device_id = item.camera.id
        if not self.pending_device_link_source_id:
            self.pending_device_link_source_id = device_id
            self.scene.clearSelection()
            item.setSelected(True)
            event.accept()
            return True
        if self.pending_device_link_source_id != device_id:
            self._begin_history_step("device_link_create")
            self.device_link_created.emit(self.pending_device_link_source_id, device_id)
            self._commit_history_step("device_link_create")
        self.pending_device_link_source_id = ""
        self.scene.clearSelection()
        item.setSelected(True)
        event.accept()
        return True
