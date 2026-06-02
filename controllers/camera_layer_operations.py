"""Persistent layer operations for map canvas objects."""

import sqlite3
import uuid

from models.canvas_layer_model import CanvasLayer, DEFAULT_LAYER_NAMES


class CameraLayerOperations:
    """Manage per-layout canvas layers and object membership."""

    def ensure_default_layers(self, layout_id: str = "default") -> None:
        """Create default layers and assign unlayered objects by type."""
        if not self._layout_exists(layout_id):
            return
        for position, (kind, name) in enumerate(DEFAULT_LAYER_NAMES.items()):
            self.db.execute(
                """
                INSERT OR IGNORE INTO canvas_layers (id, layout_id, name, position)
                VALUES (?, ?, ?, ?)
                """,
                (self.default_layer_id(layout_id, kind), layout_id, name, position),
            )
        self._assign_default_memberships(layout_id)

    def default_layer_id(self, layout_id: str, kind: str) -> str:
        """Return a deterministic default layer id for a layout and kind."""
        return f"layer_{layout_id}_{kind}"

    def create_layer(self, name: str, layout_id: str = "default") -> CanvasLayer:
        """Create a new empty layer at the top of the layout stack."""
        self.ensure_default_layers(layout_id)
        row = self.db.fetch_one(
            "SELECT COALESCE(MAX(position), -1) + 1 AS next_position FROM canvas_layers WHERE layout_id = ?",
            (layout_id,),
        )
        layer = CanvasLayer(
            id=f"layer_{uuid.uuid4().hex}",
            layout_id=layout_id,
            name=name.strip() or "Layer",
            position=int(row["next_position"] if row else 0),
        )
        self.db.execute(
            """
            INSERT INTO canvas_layers (id, layout_id, name, position, visible, locked)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (layer.id, layer.layout_id, layer.name, layer.position, int(layer.visible), int(layer.locked)),
        )
        return layer

    def get_layers(self, layout_id: str = "default") -> list[CanvasLayer]:
        """Return the ordered layers for one layout."""
        self.ensure_default_layers(layout_id)
        rows = self.db.fetch_all(
            """
            SELECT id, layout_id, name, position, visible, locked
            FROM canvas_layers
            WHERE layout_id = ?
            ORDER BY position, name
            """,
            (layout_id,),
        )
        return [self._row_to_layer(row) for row in rows]

    def rename_layer(self, layer_id: str, name: str) -> bool:
        """Rename a layer."""
        cursor = self.db.execute(
            "UPDATE canvas_layers SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (name.strip() or "Layer", layer_id),
        )
        return cursor.rowcount > 0

    def set_layer_visible(self, layer_id: str, visible: bool) -> bool:
        """Persist layer visibility."""
        cursor = self.db.execute(
            "UPDATE canvas_layers SET visible = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (int(visible), layer_id),
        )
        return cursor.rowcount > 0

    def set_layer_locked(self, layer_id: str, locked: bool) -> bool:
        """Persist layer lock state."""
        cursor = self.db.execute(
            "UPDATE canvas_layers SET locked = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (int(locked), layer_id),
        )
        return cursor.rowcount > 0

    def move_layer(self, layer_id: str, direction: int, layout_id: str = "default") -> bool:
        """Move a layer one step up or down."""
        layers = self.get_layers(layout_id)
        index = next((item for item, layer in enumerate(layers) if layer.id == layer_id), -1)
        target = index - 1 if direction < 0 else index + 1
        if index < 0 or not 0 <= target < len(layers):
            return False
        layers[index], layers[target] = layers[target], layers[index]
        for position, layer in enumerate(layers):
            self.db.execute("UPDATE canvas_layers SET position = ? WHERE id = ?", (position, layer.id))
        return True

    def delete_layer(self, layer_id: str) -> bool:
        """Delete a layer and contained cameras/drawings."""
        try:
            self.db.execute("DELETE FROM cameras WHERE layer_id = ?", (layer_id,))
            self.db.execute("DELETE FROM drawing_shapes WHERE layer_id = ?", (layer_id,))
            cursor = self.db.execute("DELETE FROM canvas_layers WHERE id = ?", (layer_id,))
            return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            return False

    def update_camera_layer(self, camera_id: str, layer_id: str) -> bool:
        """Persist a camera layer assignment."""
        cursor = self.db.execute("UPDATE cameras SET layer_id = ? WHERE id = ?", (layer_id, camera_id))
        return cursor.rowcount > 0

    def update_drawing_shape_layer(self, shape_id: str, layer_id: str) -> bool:
        """Persist a drawing layer assignment."""
        cursor = self.db.execute("UPDATE drawing_shapes SET layer_id = ? WHERE id = ?", (layer_id, shape_id))
        return cursor.rowcount > 0

    def layer_object_counts(self, layout_id: str = "default") -> dict[str, int]:
        """Return object counts keyed by layer id."""
        counts: dict[str, int] = {}
        for table in ("cameras", "drawing_shapes"):
            rows = self.db.fetch_all(
                f"SELECT layer_id, COUNT(*) AS count FROM {table} WHERE layout_id = ? GROUP BY layer_id",
                (layout_id,),
            )
            for row in rows:
                layer_id = row["layer_id"] or ""
                counts[layer_id] = counts.get(layer_id, 0) + int(row["count"])
        return counts

    def _assign_default_memberships(self, layout_id: str) -> None:
        camera_layer = self.default_layer_id(layout_id, "cameras")
        drawings_layer = self.default_layer_id(layout_id, "drawings")
        images_layer = self.default_layer_id(layout_id, "images")
        text_layer = self.default_layer_id(layout_id, "text")
        self.db.execute(
            "UPDATE cameras SET layer_id = ? WHERE layout_id = ? AND COALESCE(layer_id, '') = ''",
            (camera_layer, layout_id),
        )
        self.db.execute(
            """
            UPDATE drawing_shapes
            SET layer_id = CASE
                WHEN shape_type = 'Image' THEN ?
                WHEN shape_type = 'Text' THEN ?
                ELSE ?
            END
            WHERE layout_id = ? AND COALESCE(layer_id, '') = ''
            """,
            (images_layer, text_layer, drawings_layer, layout_id),
        )

    def _layout_exists(self, layout_id: str) -> bool:
        return self.db.fetch_one("SELECT id FROM map_layouts WHERE id = ?", (layout_id,)) is not None

    def _row_to_layer(self, row: sqlite3.Row) -> CanvasLayer:
        return CanvasLayer(
            id=row["id"],
            layout_id=row["layout_id"],
            name=row["name"],
            position=row["position"],
            visible=bool(row["visible"]),
            locked=bool(row["locked"]),
        )
