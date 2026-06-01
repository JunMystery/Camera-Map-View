"""Reusable action methods for the map canvas widget."""

from typing import Any

from utils.geometry import snap_to_grid
from views.camera_view_item import CameraItem
from views.layer_state import (
    ALL_LAYERS,
    ANNOTATION_LAYERS,
    BACKGROUND_LAYER,
    CAMERAS_LAYER,
    GRID_LAYER,
    LayerState,
)


class MapCanvasActions:
    """Provide toolbar-facing map actions without owning Qt event handling."""

    drawing_color: str
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

    def snap_point(self, x: float, y: float) -> tuple[float, float]:
        """Snap coordinates when snap-to-grid is enabled."""
        if not self.snap_to_grid_enabled:
            return x, y
        return snap_to_grid(x, y, self.grid_size)

    def set_drawing_color(self, color: str) -> None:
        """Set the active drawing color."""
        self.drawing_color = color

    def set_grid_visible(self, visible: bool) -> None:
        """Show or hide grid items."""
        self.set_layer_visible(GRID_LAYER, visible)

    def unload_background_image(self) -> None:
        """Remove the map background while preserving cameras and drawings."""
        self.draw_default_grid()
        self.fit_in_view()

    def remove_background_item(self) -> None:
        """Remove only the background image layer."""
        if self.background_item is not None:
            self.scene.removeItem(self.background_item)
            self.background_item = None

    def remove_grid_items(self) -> None:
        """Remove only grid layer items."""
        for item in self.grid_items:
            self.scene.removeItem(item)
        self.grid_items.clear()

    def set_camera_info_visibility(self, field: str, visible: bool) -> None:
        """Toggle one camera metadata field on all map markers."""
        self.camera_info_visibility[field] = visible
        for item in self.camera_items.values():
            item.set_info_visibility(self.camera_info_visibility)

    def add_text_annotation(self, text: str) -> Any:
        """Add a text annotation at the center of the current viewport."""
        center = self.mapToScene(self.viewport().rect().center())
        shape = self.drawing_tool.text_shape(center, text, self.drawing_color)
        self.add_drawing_shape(shape, emit_created=True)
        return shape

    def add_image_annotation(self, image_path: str, width: int, height: int) -> Any:
        """Add an image annotation at the center of the current viewport."""
        center = self.mapToScene(self.viewport().rect().center())
        scale = min(1.0, 600 / max(width, height))
        shape = self.drawing_tool.image_shape(center, image_path, width * scale, height * scale)
        self.add_drawing_shape(shape, emit_created=True)
        return shape

    def delete_selected_drawings(self) -> int:
        """Delete selected non-camera drawing items from the scene and persistence."""
        deleted = 0
        for item in list(self.scene.selectedItems()):
            if item.data(1) != "drawing":
                continue
            shape_id = item.data(0)
            self.scene.removeItem(item)
            if shape_id:
                self.drawing_deleted.emit(str(shape_id))
            deleted += 1
        return deleted

    def rotate_selected_cameras(self, degrees: float = 15.0) -> int:
        """Rotate selected camera viewing directions and emit persistence updates."""
        rotated = 0
        for item in self.scene.selectedItems():
            if item.data(1) != "camera" or not isinstance(item, CameraItem):
                continue
            item.camera.rotation = (item.camera.rotation + degrees) % 360
            item.update_tooltip()
            item.update()
            self.camera_rotated.emit(item.camera.id, item.camera.rotation)
            rotated += 1
        return rotated

    def clear_map_items(self) -> None:
        """Remove cameras and annotation items for a layout switch."""
        for item in list(self.scene.items()):
            if item.data(1) in {"camera", "drawing"}:
                self.scene.removeItem(item)
        self.camera_items.clear()
        self.item_default_flags.clear()

    def get_layer_states(self) -> list[LayerState]:
        """Return the current grouped layer states for UI panels."""
        return [
            LayerState(
                layer_id=layer_id,
                display_name=self.layer_display_names[layer_id],
                visible=self.layer_visibility[layer_id],
                locked=self.layer_locked[layer_id],
                item_count=len(self._items_for_layer(layer_id)),
                active=layer_id == self.active_layer_id,
            )
            for layer_id in ALL_LAYERS
        ]

    def set_active_layer(self, layer_id: str) -> bool:
        """Select the layer that receives new canvas annotations."""
        if layer_id not in ANNOTATION_LAYERS:
            return False
        self.active_layer_id = layer_id
        return True

    def set_layer_visible(self, layer_id: str, visible: bool) -> None:
        """Show or hide every item in a layer."""
        self.layer_visibility[layer_id] = visible
        if layer_id == GRID_LAYER:
            self.grid_visible = visible
        for item in self._items_for_layer(layer_id):
            item.setVisible(visible)

    def set_layer_locked(self, layer_id: str, locked: bool) -> None:
        """Enable or disable selection and movement for a layer."""
        self.layer_locked[layer_id] = locked
        for item in self._items_for_layer(layer_id):
            self._set_item_locked(item, locked)

    def select_layer_items(self, layer_id: str) -> int:
        """Select all visible, unlocked items in a layer."""
        self.scene.clearSelection()
        if self.layer_locked[layer_id]:
            return 0
        selected = 0
        for item in self._items_for_layer(layer_id):
            if item.isVisible() and item.flags() & item.GraphicsItemFlag.ItemIsSelectable:
                item.setSelected(True)
                selected += 1
        return selected

    def delete_layer_items(self, layer_id: str) -> int:
        """Delete supported layer contents and emit persistence signals."""
        if layer_id == BACKGROUND_LAYER:
            had_background = self.background_item is not None
            self.unload_background_image()
            return int(had_background)
        if layer_id == GRID_LAYER:
            deleted = len(self.grid_items)
            self.remove_grid_items()
            return deleted
        if layer_id == CAMERAS_LAYER:
            self.scene.clearSelection()
            return 0

        deleted = 0
        for item in list(self._items_for_layer(layer_id)):
            shape_id = item.data(0)
            self.scene.removeItem(item)
            if shape_id:
                self.drawing_deleted.emit(str(shape_id))
            deleted += 1
        return deleted

    def rename_layer(self, layer_id: str, display_name: str) -> None:
        """Rename a layer for the current application session."""
        if display_name.strip():
            self.layer_display_names[layer_id] = display_name.strip()

    def set_default_layer_names(self, names: dict[str, str]) -> None:
        """Update translated default names without overwriting custom names."""
        for layer_id, name in names.items():
            if self.layer_display_names[layer_id] == self.layer_default_names[layer_id]:
                self.layer_display_names[layer_id] = name
            self.layer_default_names[layer_id] = name

    def move_layer(self, layer_id: str, direction: int) -> bool:
        """Move an annotation layer up or down within the annotation stack."""
        if layer_id not in ANNOTATION_LAYERS or direction == 0:
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
        return True

    def apply_layer_z_values(self) -> None:
        """Apply standard z-values to all managed scene items."""
        for item in self._items_for_layer(BACKGROUND_LAYER):
            item.setZValue(-30)
        for item in self._items_for_layer(GRID_LAYER):
            item.setZValue(-20)
        for index, layer_id in enumerate(self.annotation_layer_order):
            for item in self._items_for_layer(layer_id):
                item.setZValue(index * 10)
        for item in self._items_for_layer(CAMERAS_LAYER):
            item.setZValue(50)

    def _items_for_layer(self, layer_id: str) -> list[Any]:
        if layer_id == BACKGROUND_LAYER:
            return [self.background_item] if self.background_item is not None else []
        if layer_id == GRID_LAYER:
            return list(self.grid_items)
        if layer_id == CAMERAS_LAYER:
            return list(self.camera_items.values())
        return [item for item in self.scene.items() if item.data(2) == layer_id]

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
