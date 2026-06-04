"""Drawing-shape persistence operations for camera map layouts."""

import json
import sqlite3

from models.drawing_shape_model import DrawingShape


class DrawingShapeOperations:
    """Persist drawing annotations and their layer membership."""

    def add_drawing_shape(self, shape: DrawingShape, layout_id: str = "default") -> bool:
        """Persist a map drawing shape."""
        self.ensure_default_layers(layout_id)
        try:
            self.db.execute(
                """
                INSERT INTO drawing_shapes (
                    id, layout_id, shape_type, points, color, line_thickness, label, image_path,
                    layer_id, display_name, object_locked, z_index, fill_color, object_visible
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    shape.id,
                    layout_id,
                    shape.shape_type,
                    json.dumps(shape.points),
                    shape.color,
                    shape.line_thickness,
                    shape.label,
                    shape.image_path,
                    self._resolved_shape_layer_id(shape.layer_id, layout_id),
                    shape.display_name,
                    int(shape.object_locked),
                    int(shape.z_index),
                    shape.fill_color,
                    int(shape.object_visible),
                ),
            )
            return True
        except sqlite3.IntegrityError:
            return False

    def delete_drawing_shape(self, shape_id: str) -> bool:
        """Delete a persisted drawing shape by id."""
        cursor = self.db.execute("DELETE FROM drawing_shapes WHERE id = ?", (shape_id,))
        return cursor.rowcount > 0

    def update_drawing_shape(self, shape: DrawingShape, layout_id: str = "default") -> bool:
        """Update a persisted drawing shape without changing the schema."""
        cursor = self.db.execute(
            """
            UPDATE drawing_shapes
            SET points = ?, color = ?, line_thickness = ?, label = ?, image_path = ?,
                layer_id = ?, display_name = ?, object_locked = ?, z_index = ?, fill_color = ?,
                object_visible = ?
            WHERE id = ? AND layout_id = ?
            """,
            (
                json.dumps(shape.points),
                shape.color,
                shape.line_thickness,
                shape.label,
                shape.image_path,
                self._resolved_shape_layer_id(shape.layer_id, layout_id),
                shape.display_name,
                int(shape.object_locked),
                int(shape.z_index),
                shape.fill_color,
                int(shape.object_visible),
                shape.id,
                layout_id,
            ),
        )
        return cursor.rowcount > 0

    def update_drawing_shape_display_name(self, shape_id: str, display_name: str, layout_id: str = "default") -> bool:
        """Persist only the layer-panel display name for one drawing object."""
        cursor = self.db.execute(
            """
            UPDATE drawing_shapes
            SET display_name = ?
            WHERE id = ? AND layout_id = ?
            """,
            (display_name, shape_id, layout_id),
        )
        return cursor.rowcount > 0

    def get_drawing_shapes(self, layout_id: str = "default") -> list[DrawingShape]:
        """Return persisted drawing shapes for a layout."""
        self.ensure_default_layers(layout_id)
        rows = self.db.fetch_all(
            """
            SELECT * FROM drawing_shapes
            WHERE layout_id = ?
            ORDER BY id
            """,
            (layout_id,),
        )
        return [self._row_to_drawing_shape(row) for row in rows]

    def _default_shape_layer_id(self, layout_id: str, shape_type: str) -> str:
        return self.first_layer_id(layout_id)

    def _resolved_shape_layer_id(self, layer_id: str, layout_id: str) -> str:
        if layer_id and any(layer.id == layer_id for layer in self.get_layers(layout_id)):
            return layer_id
        return self.first_layer_id(layout_id)

    def _row_to_drawing_shape(self, row: sqlite3.Row) -> DrawingShape:
        return DrawingShape(
            id=row["id"],
            shape_type=row["shape_type"],
            points=json.loads(row["points"]),
            color=row["color"],
            line_thickness=row["line_thickness"],
            label=row["label"] or "",
            image_path=row["image_path"] or "",
            layer_id=row["layer_id"] or "",
            display_name=row["display_name"] or "",
            object_locked=bool(row["object_locked"]),
            z_index=int(row["z_index"] or 0),
            fill_color=row["fill_color"] or "",
            object_visible=bool(row["object_visible"]),
        )
