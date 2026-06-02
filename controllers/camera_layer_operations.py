"""Persistent layer operations for map canvas objects."""

import sqlite3
import uuid

from models.canvas_layer_model import CanvasLayer


class CameraLayerOperations:
    """Manage per-layout canvas layers and object membership."""

    def ensure_default_layers(self, layout_id: str = "default") -> None:
        """Create a Photoshop-like base layer and migrate legacy grouped layers."""
        if not self._layout_exists(layout_id):
            return
        self._migrate_legacy_default_layers(layout_id)
        if not self._layer_rows(layout_id):
            self.db.execute(
                """
                INSERT INTO canvas_layers (id, layout_id, name, position, visible, locked)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (self._new_layer_id(), layout_id, "Layer 1", 0, 1, 0),
            )
        self._assign_default_memberships(layout_id)

    def default_layer_id(self, layout_id: str, kind: str) -> str:
        """Return a deterministic default layer id for a layout and kind."""
        return f"layer_{layout_id}_{kind}"

    def create_layer(self, name: str, layout_id: str = "default") -> CanvasLayer:
        """Create a new empty layer at the top of the layout stack."""
        self._migrate_legacy_default_layers(layout_id)
        row = self.db.fetch_one(
            "SELECT COALESCE(MAX(position), -1) + 1 AS next_position FROM canvas_layers WHERE layout_id = ?",
            (layout_id,),
        )
        layer = CanvasLayer(
            id=self._new_layer_id(),
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
        layer_id = self.first_layer_id(layout_id)
        if not layer_id:
            return
        self.db.execute(
            "UPDATE cameras SET layer_id = ? WHERE layout_id = ? AND COALESCE(layer_id, '') = ''",
            (layer_id, layout_id),
        )
        self.db.execute(
            "UPDATE drawing_shapes SET layer_id = ? WHERE layout_id = ? AND COALESCE(layer_id, '') = ''",
            (layer_id, layout_id),
        )

    def first_layer_id(self, layout_id: str = "default") -> str:
        """Return the first user layer for a layout."""
        row = self.db.fetch_one(
            "SELECT id FROM canvas_layers WHERE layout_id = ? ORDER BY position, name LIMIT 1",
            (layout_id,),
        )
        return str(row["id"]) if row else ""

    def _migrate_legacy_default_layers(self, layout_id: str) -> None:
        legacy_ids = [self.default_layer_id(layout_id, kind) for kind in ("cameras", "drawings", "images", "text")]
        legacy_rows = [
            row for row in self._layer_rows(layout_id)
            if row["id"] in legacy_ids
        ]
        if not legacy_rows:
            return
        target_id = next(
            (row["id"] for row in self._layer_rows(layout_id) if row["id"] not in legacy_ids),
            "",
        )
        if not target_id:
            target_id = self._new_layer_id()
            self.db.execute(
                """
                INSERT INTO canvas_layers (id, layout_id, name, position, visible, locked)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (target_id, layout_id, "Layer 1", 0, 1, 0),
            )
        placeholders = ",".join("?" for _ in legacy_ids)
        params = (target_id, layout_id, *legacy_ids)
        self.db.execute(
            f"UPDATE cameras SET layer_id = ? WHERE layout_id = ? AND layer_id IN ({placeholders})",
            params,
        )
        self.db.execute(
            f"UPDATE drawing_shapes SET layer_id = ? WHERE layout_id = ? AND layer_id IN ({placeholders})",
            params,
        )
        self.db.execute(
            f"DELETE FROM canvas_layers WHERE layout_id = ? AND id IN ({placeholders})",
            (layout_id, *legacy_ids),
        )
        self._normalize_positions(layout_id)

    def _layer_rows(self, layout_id: str) -> list[sqlite3.Row]:
        return self.db.fetch_all(
            "SELECT id, layout_id, name, position, visible, locked FROM canvas_layers WHERE layout_id = ?",
            (layout_id,),
        )

    def _normalize_positions(self, layout_id: str) -> None:
        for position, layer in enumerate(self.get_layers(layout_id)):
            self.db.execute("UPDATE canvas_layers SET position = ? WHERE id = ?", (position, layer.id))

    def _new_layer_id(self) -> str:
        return f"layer_{uuid.uuid4().hex}"

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
