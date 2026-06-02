"""Map layout CRUD operations mixed into CameraDataManager."""

import sqlite3
import uuid

from models.map_layout_model import MapLayout


class CameraLayoutOperations:
    """Provide CRUD and serialization helpers for map layouts."""

    def get_layouts(self) -> list[MapLayout]:
        """Return all available map layouts."""
        rows = self.db.fetch_all("SELECT * FROM map_layouts ORDER BY name")
        return [self._row_to_layout(row) for row in rows]

    def get_layout(self, layout_id: str) -> MapLayout | None:
        """Return one layout by id."""
        row = self.db.fetch_one("SELECT * FROM map_layouts WHERE id = ?", (layout_id,))
        return self._row_to_layout(row) if row else None

    def create_layout(self, name: str) -> MapLayout:
        """Create a new blank map layout."""
        layout = MapLayout(id=f"layout_{uuid.uuid4().hex[:8]}", name=name)
        self.db.execute(
            """
            INSERT INTO map_layouts (id, name, background_path, grid_size, canvas_width, canvas_height, background_scale)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                layout.id,
                layout.name,
                layout.background_path,
                layout.grid_size,
                layout.canvas_width,
                layout.canvas_height,
                layout.background_scale,
            ),
        )
        return layout

    def update_layout(self, layout: MapLayout) -> bool:
        """Update layout metadata and canvas settings."""
        cursor = self.db.execute(
            """
            UPDATE map_layouts
            SET name = ?, background_path = ?, grid_size = ?, canvas_width = ?,
                canvas_height = ?, background_scale = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                layout.name,
                layout.background_path,
                layout.grid_size,
                layout.canvas_width,
                layout.canvas_height,
                layout.background_scale,
                layout.id,
            ),
        )
        return cursor.rowcount > 0

    def delete_layout(self, layout_id: str) -> bool:
        """Delete a layout and cascade its data."""
        if not layout_id:
            return False
        cursor = self.db.execute("DELETE FROM map_layouts WHERE id = ?", (layout_id,))
        return cursor.rowcount > 0

    def _row_to_layout(self, row: sqlite3.Row) -> MapLayout:
        return MapLayout(
            id=row["id"],
            name=row["name"],
            background_path=row["background_path"] or "",
            grid_size=row["grid_size"] or 20,
            canvas_width=row["canvas_width"] or 4000,
            canvas_height=row["canvas_height"] or 3000,
            background_scale=row["background_scale"] or 1.0,
        )
