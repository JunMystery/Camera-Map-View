"""Reusable action methods for the map canvas widget."""

from typing import Any

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsTextItem,
)

from models.device_catalog import DEVICE_KIND_CAMERA
from models.drawing_shape_model import DrawingShape
from utils.geometry import snap_to_grid
from views.camera_view_item import CameraItem
from views.layer_state import (
    BACKGROUND_LAYER,
    GRID_LAYER,
    LayerObjectState,
    LayerState,
)


class MapCanvasActions:
    """Provide toolbar-facing map actions without owning Qt event handling."""

    drawing_color: str
    drawing_fill_color: str
    grid_visible: bool
    grid_items: list[Any]
    camera_items: dict[str, CameraItem]
    camera_info_visibility: dict[str, bool]
    snap_to_grid_enabled: bool
    grid_size: int
    layer_display_names: dict[str, str]
    layer_default_names: dict[str, str]
    layer_visibility: dict[str, bool]
    layer_locked: dict[str, bool]
    annotation_layer_order: list[str]
    active_layer_id: str
    item_default_flags: dict[Any, Any]

    def is_snap_modifier_active(self) -> bool:
        """Return whether the current canvas operation should snap to grid."""
        return bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier)

    def snap_point(self, x: float, y: float, force: bool = False) -> tuple[float, float]:
        """Snap coordinates when snap-to-grid is enabled."""
        if not force and not self.is_snap_modifier_active():
            return x, y
        return snap_to_grid(x, y, self.grid_size)

    def set_drawing_color(self, color: str) -> None:
        """Set the active drawing color."""
        self.drawing_color = color

    def set_drawing_fill_color(self, color: str) -> None:
        """Set the active fill color for closed shapes."""
        self.drawing_fill_color = color if QColor(color).isValid() else ""

    def clear_drawing_fill_color(self) -> None:
        """Disable fill for newly created closed shapes."""
        self.drawing_fill_color = ""

    def set_grid_visible(self, visible: bool) -> None:
        """Show or hide grid items."""
        self._begin_history_step("grid_visible")
        self.set_layer_visible(GRID_LAYER, visible)
        self._commit_history_step("grid_visible")

    def set_background_map_visible(self, visible: bool) -> None:
        """Show or hide the background map without unloading it."""
        self.background_map_visible = visible
        if self.background_item is not None:
            self.background_item.setVisible(visible and self.layer_visibility.get(BACKGROUND_LAYER, True))
        self._emit_layers_changed()

    def is_background_map_visible(self) -> bool:
        """Return whether the background map overlay is enabled."""
        return bool(getattr(self, "background_map_visible", True))

    def unload_background_image(self) -> None:
        """Remove the map background while preserving cameras and drawings."""
        rect = self.scene.sceneRect()
        width = int(rect.width()) or 4000
        height = int(rect.height()) or 3000
        self.remove_background_item()
        self.background_source_pixmap = None
        self.background_x = 0.0
        self.background_y = 0.0
        self.remove_grid_items()
        self.scene.setSceneRect(0, 0, width, height)
        self._ensure_canvas_bounds(width, height)
        self._add_grid_items(width, height, self.grid_size)
        self.fit_in_view()

    def remove_background_item(self) -> None:
        """Remove only the background image layer."""
        if self.background_item is not None:
            self.scene.removeItem(self.background_item)
            self.background_item = None
        if getattr(self, "background_move_outline", None) is not None:
            self.background_move_outline.setVisible(False)

    def remove_grid_items(self) -> None:
        """Remove only grid layer items."""
        for item in self.grid_items:
            self.scene.removeItem(item)
        self.grid_items.clear()

    def set_camera_info_visibility(self, field: str, visible: bool) -> None:
        """Toggle one camera metadata field on all map markers."""
        if field not in {"name", "zone", "ip"}:
            return
        self.camera_info_visibility[field] = visible
        for item in self.camera_items.values():
            item.set_info_visibility(self.camera_info_visibility)

    def add_text_annotation(self, text: str, font_size: int = 18, color: str | None = None) -> Any:
        """Add a text annotation at the center of the current viewport."""
        center = self.mapToScene(self.viewport().rect().center())
        shape = self.drawing_tool.text_shape(center, text, color or self.drawing_color, font_size)
        self.add_drawing_shape(shape, emit_created=True)
        return shape

    def selected_text_annotation(self) -> DrawingShape | None:
        """Return the selected text annotation model when exactly one text item is selected."""
        selected_items = [item for item in self.scene.selectedItems() if item.data(1) == "drawing"]
        if len(selected_items) != 1 or not isinstance(selected_items[0], QGraphicsTextItem):
            return None
        return self._text_shape_from_item(selected_items[0])

    def update_selected_text_annotation(self, text: str, font_size: int, color: str) -> DrawingShape | None:
        """Update the selected text annotation and emit persistence data."""
        selected = self.selected_text_annotation()
        if selected is None:
            return None
        item = self._selected_text_item()
        if item is None:
            return None

        self._begin_history_step("text_update")
        item.setPlainText(text)
        font = item.font()
        font.setPointSize(font_size)
        item.setFont(font)
        item.setDefaultTextColor(QColor(color))

        updated = self._text_shape_from_item(item)
        self.drawing_updated.emit(updated)
        self._commit_history_step("text_update")
        return updated

    def add_image_annotation(self, image_path: str, width: int, height: int) -> Any:
        """Add an image annotation at the center of the current viewport."""
        center = self.mapToScene(self.viewport().rect().center())
        display_width = max(float(width), 1.0)
        display_height = max(float(height), 1.0)
        scene_rect = self.scene.sceneRect()
        if not scene_rect.isNull() and scene_rect.width() > 0 and scene_rect.height() > 0:
            scale = min(1.0, scene_rect.width() / display_width, scene_rect.height() / display_height)
            display_width *= scale
            display_height *= scale
        x = center.x() - display_width / 2
        y = center.y() - display_height / 2
        if not scene_rect.isNull():
            x = min(max(x, scene_rect.left()), max(scene_rect.left(), scene_rect.right() - display_width))
            y = min(max(y, scene_rect.top()), max(scene_rect.top(), scene_rect.bottom() - display_height))
        shape = self.drawing_tool.image_shape(QPointF(x, y), image_path, display_width, display_height)
        self.add_drawing_shape(shape, emit_created=True)
        return shape

    def delete_selected_drawings(self) -> int:
        """Delete selected drawings and unbind selected cameras from the scene."""
        self._begin_history_step("delete_selected")
        deleted = 0
        for item in list(self.scene.selectedItems()):
            if item.data(1) == "drawing":
                shape_id = item.data(0)
                self.scene.removeItem(item)
                self.pan_item_flags.pop(item, None)
                self.item_default_flags.pop(item, None)
                if shape_id:
                    self.drawing_deleted.emit(str(shape_id))
                deleted += 1
            elif item.data(1) == "camera" and isinstance(item, CameraItem):
                camera_id = item.camera.id
                self.scene.removeItem(item)
                self.camera_items.pop(camera_id, None)
                self.pan_item_flags.pop(item, None)
                self.item_default_flags.pop(item, None)
                self.camera_deleted.emit(camera_id)
                deleted += 1
        if deleted:
            self._emit_layers_changed()
        self._commit_history_step("delete_selected")
        return deleted

    def rotate_selected_cameras(self, degrees: float = 15.0) -> int:
        """Rotate selected camera viewing directions and emit persistence updates."""
        self._begin_history_step("camera_rotate")
        rotated = 0
        for item in self.scene.selectedItems():
            if item.data(1) != "camera" or not isinstance(item, CameraItem) or item.camera.device_kind != DEVICE_KIND_CAMERA:
                continue
            item.camera.rotation = (item.camera.rotation + degrees) % 360
            item.update_tooltip()
            item.update()
            self.camera_rotated.emit(item.camera.id, item.camera.rotation)
            rotated += 1
        if rotated:
            self._emit_layers_changed()
        self._commit_history_step("camera_rotate")
        return rotated

    def clear_map_items(self) -> None:
        """Remove cameras and annotation items for a layout switch."""
        if hasattr(self, "clear_topology_highlight"):
            self.clear_topology_highlight()
        self._remove_device_link_items()
        self.device_links = []
        self.device_catalog = {}
        for item in list(self.scene.items()):
            if item.data(1) in {"camera", "drawing"}:
                self.pan_item_flags.pop(item, None)
                self.item_default_flags.pop(item, None)
                self.scene.removeItem(item)
        self.camera_items.clear()
        self.item_default_flags.clear()
        self.pan_item_flags.clear()
        self._emit_layers_changed()

    def get_layer_states(self) -> list[LayerState]:
        """Return the current grouped layer states for UI panels."""
        items_by_layer = self._items_by_layer()
        return [
            LayerState(
                layer_id=layer.id,
                display_name=self.layer_display_names.get(layer.id, layer.name),
                visible=self.layer_visibility.get(layer.id, layer.visible),
                locked=self.layer_locked.get(layer.id, layer.locked),
                item_count=len(items_by_layer.get(layer.id, [])),
                active=layer.id == self.active_layer_id and not layer.is_group,
                group_id=layer.group_id,
                is_group=layer.is_group,
            )
            for layer in self.canvas_layers
        ]

    def get_layer_object_states(self, layer_id: str) -> list[LayerObjectState]:
        """Return object rows for one layer."""
        rows: list[LayerObjectState] = []
        for item in self._items_for_layer(layer_id):
            object_type = str(item.data(1) or "")
            object_id = str(item.data(0) or "")
            label = object_id
            if object_type == "camera" and isinstance(item, CameraItem):
                object_id = item.camera.id
                label = item.camera.name
            elif object_type == "drawing":
                label = self._drawing_label(item)
            rows.append(
                LayerObjectState(
                    object_id=object_id,
                    layer_id=layer_id,
                    label=label,
                    object_type=object_type,
                    visible=self._item_object_visible(item),
                    locked=bool(item.data(6)),
                    z_index=int(item.data(7) or 0),
                )
            )
        return rows

    def set_active_layer(self, layer_id: str) -> bool:
        """Select the layer that receives new canvas annotations."""
        layer_id = self._resolve_layer_id(layer_id)
        if layer_id not in self.layer_display_names:
            return False
        changed = self.active_layer_id != layer_id
        self.active_layer_id = layer_id
        if changed:
            try:
                self.active_layer_changed.emit(layer_id)
            except Exception:
                pass
            self._emit_layers_changed()
        return True

    def set_layer_visible(self, layer_id: str, visible: bool) -> None:
        """Show or hide every item in a layer."""
        layer_id = self._resolve_layer_id(layer_id)
        self.layer_visibility[layer_id] = visible
        if layer_id == GRID_LAYER:
            self.grid_visible = visible
        targets = self._items_for_layer(layer_id)
        if any(layer.id == layer_id and layer.is_group for layer in self.canvas_layers):
            child_ids = {layer.id for layer in self.canvas_layers if layer.group_id == layer_id}
            targets = [item for child_id in child_ids for item in self._items_for_layer(child_id)]
        for item in targets:
            self._apply_item_visibility(item)
        self._emit_layers_changed()

    def set_layer_locked(self, layer_id: str, locked: bool) -> None:
        """Enable or disable selection and movement for a layer."""
        layer_id = self._resolve_layer_id(layer_id)
        self.layer_locked[layer_id] = locked
        targets = self._items_for_layer(layer_id)
        if any(layer.id == layer_id and layer.is_group for layer in self.canvas_layers):
            child_ids = {layer.id for layer in self.canvas_layers if layer.group_id == layer_id}
            targets = [item for child_id in child_ids for item in self._items_for_layer(child_id)]
        for item in targets:
            self._set_item_locked(item, self._item_effective_locked(item))
        self._set_item_interaction_suspended(getattr(self, "item_interaction_suspended", False))
        self._emit_layers_changed()

    def select_layer_items(self, layer_id: str) -> int:
        """Select all visible, unlocked items in a layer."""
        layer_id = self._resolve_layer_id(layer_id)
        self.scene.clearSelection()
        if self.layer_locked.get(layer_id, False):
            return 0
        selected = 0
        for item in self._items_for_layer(layer_id):
            if item.isVisible() and item.flags() & item.GraphicsItemFlag.ItemIsSelectable:
                item.setSelected(True)
                selected += 1
        return selected

    def delete_layer_items(self, layer_id: str) -> int:
        """Delete supported layer contents and emit persistence signals."""
        layer_id = self._resolve_layer_id(layer_id)
        if layer_id == BACKGROUND_LAYER:
            had_background = self.background_item is not None
            self.unload_background_image()
            return int(had_background)
        if layer_id == GRID_LAYER:
            deleted = len(self.grid_items)
            self.remove_grid_items()
            return deleted

        deleted = 0
        for item in list(self._items_for_layer(layer_id)):
            object_type = item.data(1)
            object_id = item.data(0)
            self.scene.removeItem(item)
            self.pan_item_flags.pop(item, None)
            self.item_default_flags.pop(item, None)
            if object_type == "camera" and isinstance(item, CameraItem):
                self.camera_items.pop(item.camera.id, None)
                self.camera_deleted.emit(item.camera.id)
            elif object_id:
                self.drawing_deleted.emit(str(object_id))
            deleted += 1
        if deleted:
            self._emit_layers_changed()
        return deleted

    def rename_layer(self, layer_id: str, display_name: str) -> None:
        """Rename a layer for the current application session."""
        layer_id = self._resolve_layer_id(layer_id)
        if display_name.strip():
            self.layer_display_names[layer_id] = display_name.strip()
            self._emit_layers_changed()

    def rename_layer_object(self, object_type: str, object_id: str, display_name: str) -> bool:
        """Rename one object row in the Layers panel without changing layer membership."""
        display_name = display_name.strip()
        if not display_name:
            return False
        if object_type == "camera":
            item = self.camera_items.get(object_id)
            if item is None:
                return False
            self._begin_history_step("object_rename")
            item.camera.name = display_name
            item.update_tooltip()
            item.update()
        elif object_type == "drawing":
            target = next((item for item in self.scene.items() if str(item.data(0) or "") == object_id), None)
            if target is None:
                return False
            self._begin_history_step("object_rename")
            target.setData(3, display_name)
        else:
            return False
        self.object_renamed.emit(object_type, object_id, display_name)
        self._emit_layers_changed()
        self._commit_history_step("object_rename")
        return True

    def set_layer_object_locked(self, object_type: str, object_id: str, locked: bool) -> bool:
        """Lock or unlock one object from the Layers panel."""
        item = self._find_layer_object_item(object_type, object_id)
        if item is None:
            return False
        self._begin_history_step("object_lock")
        item.setData(6, locked)
        if object_type == "camera" and isinstance(item, CameraItem):
            item.camera.object_locked = locked
        self._set_item_locked(item, self._item_effective_locked(item))
        self.object_locked_changed.emit(object_type, object_id, locked)
        self._emit_layers_changed()
        self._commit_history_step("object_lock")
        return True

    def set_layer_object_visible(self, object_type: str, object_id: str, visible: bool) -> bool:
        """Show or hide one canvas object without changing its layer visibility."""
        item = self._find_layer_object_item(object_type, object_id)
        if item is None:
            return False
        self._begin_history_step("object_visibility")
        item.setData(9, visible)
        if object_type == "camera" and isinstance(item, CameraItem):
            item.camera.object_visible = visible
        if not visible:
            item.setSelected(False)
        self._apply_item_visibility(item)
        self.object_visibility_changed.emit(object_type, object_id, visible)
        self._emit_layers_changed()
        self._commit_history_step("object_visibility")
        return True

    def set_default_layer_names(self, names: dict[str, str]) -> None:
        """Update translated default names without overwriting custom names."""
        for layer_id, name in names.items():
            if layer_id not in self.layer_display_names:
                continue
            if self.layer_display_names[layer_id] == self.layer_default_names[layer_id]:
                self.layer_display_names[layer_id] = name
            self.layer_default_names[layer_id] = name

    def move_layer(self, layer_id: str, direction: int) -> bool:
        """Move an annotation layer up or down within the annotation stack."""
        layer_id = self._resolve_layer_id(layer_id)
        if layer_id not in self.annotation_layer_order or direction == 0:
            return False
        current_index = self.annotation_layer_order.index(layer_id)
        new_index = current_index - 1 if direction < 0 else current_index + 1
        if not 0 <= new_index < len(self.annotation_layer_order):
            return False
        self.annotation_layer_order[current_index], self.annotation_layer_order[new_index] = (
            self.annotation_layer_order[new_index],
            self.annotation_layer_order[current_index],
        )
        self.apply_layer_z_values()
        self._emit_layers_changed()
        return True

    def apply_layer_z_values(self) -> None:
        """Apply standard z-values to all managed scene items."""
        items_by_layer = self._items_by_layer()
        for item in items_by_layer.get(BACKGROUND_LAYER, []):
            item.setZValue(-30)
        for item in items_by_layer.get(GRID_LAYER, []):
            item.setZValue(-20)
        for index, layer_id in enumerate(self.annotation_layer_order):
            for item in items_by_layer.get(layer_id, []):
                item.setZValue(index * 1000 + int(item.data(7) or 0))

    def move_layer_object(self, object_type: str, object_id: str, direction: int) -> bool:
        """Move one object forward/backward within its layer."""
        item = self._find_layer_object_item(object_type, object_id)
        if item is None or direction == 0:
            return False
        layer_id = str(item.data(2) or "")
        siblings = sorted(
            self._items_for_layer(layer_id),
            key=lambda candidate: (int(candidate.data(7) or 0), str(candidate.data(0) or "")),
        )
        if len(siblings) < 2:
            return False
        for index, candidate in enumerate(siblings):
            candidate.setData(7, index)
        current_index = siblings.index(item)
        target_index = current_index + (1 if direction > 0 else -1)
        if not 0 <= target_index < len(siblings):
            return False
        self._begin_history_step("object_z")
        siblings[current_index], siblings[target_index] = siblings[target_index], siblings[current_index]
        for index, candidate in enumerate(siblings):
            candidate.setData(7, index)
            object_type_value = str(candidate.data(1) or "")
            object_id_value = str(candidate.data(0) or "")
            if object_type_value == "camera" and isinstance(candidate, CameraItem):
                object_id_value = candidate.camera.id
                candidate.camera.z_index = index
            self.object_z_changed.emit(object_type_value, object_id_value, index)
        self.apply_layer_z_values()
        self._emit_layers_changed()
        self._commit_history_step("object_z")
        return True

    def move_layer_object_to_index(self, object_type: str, object_id: str, layer_id: str, target_index: int) -> bool:
        """Move one object to an explicit z-order index within a layer."""
        layer_id = self._resolve_layer_id(layer_id)
        item = self._find_layer_object_item(object_type, object_id)
        if item is None or str(item.data(2) or "") != layer_id:
            return False
        siblings = sorted(
            self._items_for_layer(layer_id),
            key=lambda candidate: (int(candidate.data(7) or 0), str(candidate.data(0) or "")),
        )
        if item not in siblings:
            return False
        target_index = max(0, min(target_index, len(siblings) - 1))
        current_index = siblings.index(item)
        if current_index == target_index:
            return False
        self._begin_history_step("object_z")
        siblings.pop(current_index)
        siblings.insert(target_index, item)
        for index, candidate in enumerate(siblings):
            candidate.setData(7, index)
            object_type_value = str(candidate.data(1) or "")
            object_id_value = str(candidate.data(0) or "")
            if object_type_value == "camera" and isinstance(candidate, CameraItem):
                object_id_value = candidate.camera.id
                candidate.camera.z_index = index
            self.object_z_changed.emit(object_type_value, object_id_value, index)
        self.apply_layer_z_values()
        self._emit_layers_changed()
        self._commit_history_step("object_z")
        return True

    def top_selectable_item_at(self, view_pos: Any) -> Any | None:
        """Return the highest visible, unlocked canvas object at a viewport position."""
        scene_pos = self.mapToScene(view_pos)
        candidates = [
            item
            for item in self.scene.items(scene_pos)
            if self._is_priority_selectable_item(item)
        ]
        if not candidates:
            return None
        return max(candidates, key=self._selection_priority)

    def move_selected_items_to_layer(self, layer_id: str) -> int:
        """Move selected cameras and drawings into a target layer."""
        layer_id = self._resolve_layer_id(layer_id)
        if layer_id not in self.layer_display_names:
            return 0
        self._begin_history_step("selection_layer_move")
        moved = 0
        for item in self.scene.selectedItems():
            object_type = item.data(1)
            object_id = item.data(0)
            if object_type == "camera" and isinstance(item, CameraItem):
                item.camera.layer_id = layer_id
                item.setData(2, layer_id)
                self.object_layer_changed.emit("camera", item.camera.id, layer_id)
                moved += 1
            elif object_type == "drawing" and object_id:
                item.setData(2, layer_id)
                self.object_layer_changed.emit("drawing", str(object_id), layer_id)
                moved += 1
        self.apply_layer_z_values()
        if moved:
            self._emit_layers_changed()
        self._commit_history_step("selection_layer_move")
        return moved

    def select_layer_object(self, object_type: str, object_id: str, clear_existing: bool = True) -> bool:
        """Select one canvas object by id."""
        if clear_existing:
            self.scene.clearSelection()
        item = self._find_layer_object_item(object_type, object_id)
        if item is None or self._item_effective_locked(item) or not item.isVisible():
            return False
        if not item.flags() & item.GraphicsItemFlag.ItemIsSelectable:
            item.setFlags(item.flags() | item.GraphicsItemFlag.ItemIsSelectable)
        item.setSelected(True)
        try:
            # Notify UI panels about a programmatic object selection
            self.layer_object_selected.emit(object_type, object_id)
        except Exception:
            pass
        return True

    def select_camera_item(self, camera_id: str, center: bool = True) -> bool:
        """Select one placed camera item from an external panel."""
        self.scene.clearSelection()
        item = self.camera_items.get(camera_id)
        if item is None or self._item_effective_locked(item) or not item.isVisible():
            return False
        item.setSelected(True)
        if center:
            self.centerOn(item)
        return True

    def move_layer_object_to_layer(self, object_type: str, object_id: str, layer_id: str) -> bool:
        """Move one object to another layer."""
        layer_id = self._resolve_layer_id(layer_id)
        if layer_id not in self.annotation_layer_order:
            return False
        item = self._find_layer_object_item(object_type, object_id)
        if item is None:
            return False
        self._begin_history_step("object_layer_move")
        item.setData(2, layer_id)
        if object_type == "camera" and isinstance(item, CameraItem):
            item.camera.layer_id = layer_id
            self.object_layer_changed.emit("camera", item.camera.id, layer_id)
        elif object_type == "drawing":
            self.object_layer_changed.emit("drawing", object_id, layer_id)
        else:
            self._commit_history_step("object_layer_move")
            return False
        self.apply_layer_z_values()
        self._emit_layers_changed()
        self._commit_history_step("object_layer_move")
        return True

    def _find_layer_object_item(self, object_type: str, object_id: str) -> Any | None:
        for item in self.scene.items():
            if object_type == "camera" and isinstance(item, CameraItem) and item.camera.id == object_id:
                return item
            if object_type == "drawing" and str(item.data(0) or "") == object_id:
                return item
        return None

    def _selected_text_item(self) -> QGraphicsTextItem | None:
        selected_items = [item for item in self.scene.selectedItems() if item.data(1) == "drawing"]
        if len(selected_items) == 1 and isinstance(selected_items[0], QGraphicsTextItem):
            return selected_items[0]
        return None

    def _text_shape_from_item(self, item: QGraphicsTextItem) -> DrawingShape:
        color = item.defaultTextColor().name()
        font_size = item.font().pointSize()
        if font_size <= 0:
            font_size = 18
        return DrawingShape(
            id=str(item.data(0) or ""),
            shape_type="Text",
            points=[item.pos().x(), item.pos().y(), float(item.rotation()) % 360],
            color=color,
            line_thickness=font_size,
            label=item.toPlainText(),
            layer_id=str(item.data(2) or ""),
            display_name=str(item.data(3) or ""),
            object_locked=bool(item.data(6)),
            z_index=int(item.data(7) or 0),
            object_visible=self._item_object_visible(item),
        )

    def _persist_selected_drawing_positions(self) -> None:
        for item in self.scene.selectedItems():
            if item.data(1) != "drawing":
                continue
            shape = self._drawing_shape_from_item(item)
            if shape is not None:
                self.drawing_updated.emit(shape)

    def _drawing_shape_from_item(self, item: Any) -> DrawingShape | None:
        color = "#ef4444"
        line_thickness = 2
        fill_color = ""
        if hasattr(item, "pen"):
            pen = item.pen()
            color = pen.color().name()
            line_thickness = max(1, int(pen.widthF() or pen.width() or 1))
        if isinstance(item, (QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPolygonItem)) and hasattr(item, "brush"):
            brush = item.brush()
            if brush.style() != Qt.BrushStyle.NoBrush and brush.color().isValid():
                fill_color = brush.color().name()
        pos = item.pos()
        if isinstance(item, QGraphicsTextItem):
            return self._text_shape_from_item(item)
        if isinstance(item, QGraphicsLineItem):
            line = item.line()
            points = [
                line.x1() + pos.x(),
                line.y1() + pos.y(),
                line.x2() + pos.x(),
                line.y2() + pos.y(),
            ]
            return self._drawing_shape_model(item, "Line", points, color, line_thickness)
        if isinstance(item, QGraphicsRectItem):
            rect = item.rect()
            points = [
                rect.left() + pos.x(),
                rect.top() + pos.y(),
                rect.right() + pos.x(),
                rect.bottom() + pos.y(),
                float(item.rotation()) % 360,
            ]
            shape_type = str(item.data(8) or "Rectangle")
            return self._drawing_shape_model(item, shape_type, points, color, line_thickness, fill_color)
        if isinstance(item, QGraphicsEllipseItem):
            rect = item.rect()
            points = [
                rect.left() + pos.x(),
                rect.top() + pos.y(),
                rect.right() + pos.x(),
                rect.bottom() + pos.y(),
                float(item.rotation()) % 360,
            ]
            return self._drawing_shape_model(item, "Ellipse", points, color, line_thickness, fill_color)
        if isinstance(item, QGraphicsPolygonItem):
            points: list[float] = []
            for point in item.polygon():
                scene_point = item.mapToScene(point)
                points.extend([scene_point.x(), scene_point.y()])
            return self._drawing_shape_model(item, str(item.data(8) or "Polygon"), points, color, line_thickness, fill_color)
        if isinstance(item, QGraphicsPathItem):
            path = item.path()
            points = []
            for index in range(path.elementCount()):
                element = path.elementAt(index)
                points.extend([element.x + pos.x(), element.y + pos.y()])
            return self._drawing_shape_model(item, "Freehand", points, color, line_thickness)
        if isinstance(item, QGraphicsPixmapItem):
            pixmap = item.pixmap()
            return self._drawing_shape_model(
                item,
                "Image",
                [pos.x(), pos.y(), float(pixmap.width()), float(pixmap.height()), float(item.rotation()) % 360],
                color,
                line_thickness,
            )
        return None

    def _drawing_shape_model(
        self,
        item: Any,
        shape_type: str,
        points: list[float],
        color: str,
        line_thickness: int,
        fill_color: str = "",
    ) -> DrawingShape:
        return DrawingShape(
            id=str(item.data(0) or ""),
            shape_type=shape_type,
            points=points,
            color=color,
            line_thickness=line_thickness,
            label="",
            image_path=str(getattr(item, "data", lambda _role: "")(4) or ""),
            layer_id=str(item.data(2) or ""),
            display_name=str(item.data(3) or ""),
            object_locked=bool(item.data(6)),
            z_index=int(item.data(7) or 0),
            fill_color=fill_color,
            object_visible=self._item_object_visible(item),
        )

    def _items_for_layer(self, layer_id: str) -> list[Any]:
        layer_id = self._resolve_layer_id(layer_id)
        return self._items_by_layer().get(layer_id, [])

    def _items_by_layer(self) -> dict[str, list[Any]]:
        items_by_layer: dict[str, list[Any]] = {}
        if self.background_item is not None:
            items_by_layer.setdefault(BACKGROUND_LAYER, []).append(self.background_item)
        if self.grid_items:
            items_by_layer.setdefault(GRID_LAYER, []).extend(self.grid_items)
        for item in self.scene.items():
            layer_id = item.data(2)
            if layer_id in {None, BACKGROUND_LAYER, GRID_LAYER}:
                continue
            items_by_layer.setdefault(str(layer_id), []).append(item)
        return items_by_layer

    def _resolve_layer_id(self, layer_id: str) -> str:
        if layer_id in self.layer_display_names or layer_id in {BACKGROUND_LAYER, GRID_LAYER}:
            return layer_id
        legacy = f"layer_{self.current_layout_id}_{layer_id}"
        return legacy if legacy in self.layer_display_names else layer_id

    def _drawing_label(self, item: Any) -> str:
        display_name = str(item.data(3) or "").strip()
        if display_name:
            return display_name
        object_id = str(item.data(0) or "")
        if isinstance(item, QGraphicsTextItem) and item.toPlainText().strip():
            return item.toPlainText().strip()
        item_type = item.__class__.__name__.replace("QGraphics", "").replace("Item", "")
        return f"{item_type} {object_id[-6:]}" if object_id else item_type

    def _set_item_locked(self, item: Any, locked: bool) -> None:
        original_flags = self.item_default_flags.setdefault(item, item.flags())
        blocked_flags = (
            item.GraphicsItemFlag.ItemIsSelectable
            | item.GraphicsItemFlag.ItemIsMovable
            | item.GraphicsItemFlag.ItemIsFocusable
        )
        item.setFlags(original_flags & ~blocked_flags if locked else original_flags)
        if locked:
            item.setSelected(False)

    def _is_priority_selectable_item(self, item: Any) -> bool:
        if item.data(1) not in {"camera", "drawing"}:
            return False
        if not item.isVisible() or self._item_effective_locked(item):
            return False
        return bool(item.flags() & item.GraphicsItemFlag.ItemIsSelectable)

    def _selection_priority(self, item: Any) -> tuple[int, int, float]:
        layer_id = str(item.data(2) or "")
        try:
            layer_index = self.annotation_layer_order.index(layer_id)
        except ValueError:
            layer_index = -1
        return (layer_index, int(item.data(7) or 0), float(item.zValue()))
