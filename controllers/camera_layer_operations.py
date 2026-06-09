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
                INSERT INTO canvas_layers (id, layout_id, name, position, visible, locked, group_id, is_group)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (self._new_layer_id(), layout_id, "Layer 1", 0, 1, 0, "", 0),
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
            INSERT INTO canvas_layers (id, layout_id, name, position, visible, locked, group_id, is_group)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (layer.id, layer.layout_id, layer.name, layer.position, int(layer.visible), int(layer.locked), "", 0),
        )
        return layer

    def create_layer_group(self, name: str, layout_id: str = "default") -> CanvasLayer:
        """Create a top-level one-level layer group."""
        self._migrate_legacy_default_layers(layout_id)
        row = self.db.fetch_one(
            "SELECT COALESCE(MAX(position), -1) + 1 AS next_position FROM canvas_layers WHERE layout_id = ?",
            (layout_id,),
        )
        group = CanvasLayer(
            id=self._new_layer_id("group"),
            layout_id=layout_id,
            name=name.strip() or "Group",
            position=int(row["next_position"] if row else 0),
            is_group=True,
        )
        self.db.execute(
            """
            INSERT INTO canvas_layers (id, layout_id, name, position, visible, locked, group_id, is_group)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (group.id, group.layout_id, group.name, group.position, int(group.visible), int(group.locked), "", 1),
        )
        return group

    def get_layers(self, layout_id: str = "default") -> list[CanvasLayer]:
        """Return the ordered layers for one layout."""
        self.ensure_default_layers(layout_id)
        rows = self.db.fetch_all(
            """
            SELECT id, layout_id, name, position, visible, locked, group_id, is_group
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
            row = self.db.fetch_one("SELECT is_group FROM canvas_layers WHERE id = ?", (layer_id,))
            if row is not None and bool(row["is_group"]):
                self.db.execute("UPDATE canvas_layers SET group_id = '' WHERE group_id = ?", (layer_id,))
                cursor = self.db.execute("DELETE FROM canvas_layers WHERE id = ?", (layer_id,))
                return cursor.rowcount > 0
            self.db.execute("DELETE FROM cameras WHERE layer_id = ?", (layer_id,))
            self.db.execute("DELETE FROM drawing_shapes WHERE layer_id = ?", (layer_id,))
            cursor = self.db.execute("DELETE FROM canvas_layers WHERE id = ?", (layer_id,))
            return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            return False

    def update_camera_layer(self, camera_id: str, layer_id: str, layout_id: str | None = None) -> bool:
        """Persist a camera layer assignment."""
        if layout_id is None:
            cursor = self.db.execute("UPDATE cameras SET layer_id = ? WHERE id = ?", (layer_id, camera_id))
        else:
            cursor = self.db.execute(
                "UPDATE cameras SET layer_id = ? WHERE id = ? AND layout_id = ?",
                (layer_id, camera_id, layout_id),
            )
        return cursor.rowcount > 0

    def update_drawing_shape_layer(self, shape_id: str, layer_id: str, layout_id: str | None = None) -> bool:
        """Persist a drawing layer assignment."""
        if layout_id is None:
            cursor = self.db.execute("UPDATE drawing_shapes SET layer_id = ? WHERE id = ?", (layer_id, shape_id))
        else:
            cursor = self.db.execute(
                "UPDATE drawing_shapes SET layer_id = ? WHERE id = ? AND layout_id = ?",
                (layer_id, shape_id, layout_id),
            )
        return cursor.rowcount > 0

    def update_camera_object_locked(self, camera_id: str, locked: bool, layout_id: str | None = None) -> bool:
        """Persist a camera object lock flag."""
        if layout_id is None:
            cursor = self.db.execute("UPDATE cameras SET object_locked = ? WHERE id = ?", (int(locked), camera_id))
        else:
            cursor = self.db.execute(
                "UPDATE cameras SET object_locked = ? WHERE id = ? AND layout_id = ?",
                (int(locked), camera_id, layout_id),
            )
        return cursor.rowcount > 0

    def update_drawing_shape_object_locked(self, shape_id: str, locked: bool, layout_id: str | None = None) -> bool:
        """Persist a drawing object lock flag."""
        if layout_id is None:
            cursor = self.db.execute("UPDATE drawing_shapes SET object_locked = ? WHERE id = ?", (int(locked), shape_id))
        else:
            cursor = self.db.execute(
                "UPDATE drawing_shapes SET object_locked = ? WHERE id = ? AND layout_id = ?",
                (int(locked), shape_id, layout_id),
            )
        return cursor.rowcount > 0

    def set_layer_group(self, layer_id: str, group_id: str, layout_id: str = "default") -> bool:
        """Assign a regular layer to a top-level group or remove it from a group."""
        if group_id:
            group = self.db.fetch_one(
                "SELECT id FROM canvas_layers WHERE id = ? AND layout_id = ? AND is_group = 1 AND COALESCE(group_id, '') = ''",
                (group_id, layout_id),
            )
            if group is None:
                return False
        cursor = self.db.execute(
            """
            UPDATE canvas_layers
            SET group_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND layout_id = ? AND is_group = 0
            """,
            (group_id, layer_id, layout_id),
        )
        return cursor.rowcount > 0

    def update_camera_object_visible(self, camera_id: str, visible: bool, layout_id: str | None = None) -> bool:
        """Persist a camera object visibility flag."""
        if layout_id is None:
            cursor = self.db.execute("UPDATE cameras SET object_visible = ? WHERE id = ?", (int(visible), camera_id))
        else:
            cursor = self.db.execute(
                "UPDATE cameras SET object_visible = ? WHERE id = ? AND layout_id = ?",
                (int(visible), camera_id, layout_id),
            )
        return cursor.rowcount > 0

    def update_camera_layer_display_name(
        self,
        camera_id: str,
        display_name: str,
        layout_id: str | None = None,
    ) -> bool:
        """Persist a Layers-panel-only display alias for one camera object."""
        value = display_name.strip()
        if layout_id is None:
            cursor = self.db.execute("UPDATE cameras SET layer_display_name = ? WHERE id = ?", (value, camera_id))
        else:
            cursor = self.db.execute(
                "UPDATE cameras SET layer_display_name = ? WHERE id = ? AND layout_id = ?",
                (value, camera_id, layout_id),
            )
        return cursor.rowcount > 0

    def update_drawing_shape_object_visible(self, shape_id: str, visible: bool, layout_id: str | None = None) -> bool:
        """Persist a drawing object visibility flag."""
        if layout_id is None:
            cursor = self.db.execute("UPDATE drawing_shapes SET object_visible = ? WHERE id = ?", (int(visible), shape_id))
        else:
            cursor = self.db.execute(
                "UPDATE drawing_shapes SET object_visible = ? WHERE id = ? AND layout_id = ?",
                (int(visible), shape_id, layout_id),
            )
        return cursor.rowcount > 0

    def update_camera_z_index(self, camera_id: str, z_index: int, layout_id: str | None = None) -> bool:
        """Persist a camera object z-index."""
        if layout_id is None:
            cursor = self.db.execute("UPDATE cameras SET z_index = ? WHERE id = ?", (z_index, camera_id))
        else:
            cursor = self.db.execute(
                "UPDATE cameras SET z_index = ? WHERE id = ? AND layout_id = ?",
                (z_index, camera_id, layout_id),
            )
        return cursor.rowcount > 0

    def update_drawing_shape_z_index(self, shape_id: str, z_index: int, layout_id: str | None = None) -> bool:
        """Persist a drawing object z-index."""
        if layout_id is None:
            cursor = self.db.execute("UPDATE drawing_shapes SET z_index = ? WHERE id = ?", (z_index, shape_id))
        else:
            cursor = self.db.execute(
                "UPDATE drawing_shapes SET z_index = ? WHERE id = ? AND layout_id = ?",
                (z_index, shape_id, layout_id),
            )
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
            "SELECT id FROM canvas_layers WHERE layout_id = ? AND is_group = 0 ORDER BY position, name LIMIT 1",
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
                INSERT INTO canvas_layers (id, layout_id, name, position, visible, locked, group_id, is_group)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (target_id, layout_id, "Layer 1", 0, 1, 0, "", 0),
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
            "SELECT id, layout_id, name, position, visible, locked, group_id, is_group FROM canvas_layers WHERE layout_id = ?",
            (layout_id,),
        )

    def _normalize_positions(self, layout_id: str) -> None:
        for position, layer in enumerate(self.get_layers(layout_id)):
            self.db.execute("UPDATE canvas_layers SET position = ? WHERE id = ?", (position, layer.id))

    def _new_layer_id(self, prefix: str = "layer") -> str:
        return f"{prefix}_{uuid.uuid4().hex}"

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
            group_id=row["group_id"] or "",
            is_group=bool(row["is_group"]),
        )
