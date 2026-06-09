"""SQLite database manager for camera map persistence."""

import shutil
import sqlite3
from pathlib import Path
from typing import Any

from utils.app_paths import resolve_app_path


class CameraDbManager:
    """Manage a single SQLite connection and schema initialization."""

    def __init__(self, db_path: str | Path = "assets/data/camera_manager.db") -> None:
        self.db_path = Path(":memory:") if str(db_path) == ":memory:" else resolve_app_path(db_path)
        if self.db_path != Path(":memory:"):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.backup_database()

        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.init_db()

    def backup_database(self) -> Path | None:
        """Create a startup backup for an existing database file."""
        if self.db_path == Path(":memory:") or not self.db_path.exists():
            return None

        backup_path = self.db_path.with_suffix(f"{self.db_path.suffix}.bak")
        shutil.copy2(self.db_path, backup_path)
        return backup_path

    def init_db(self) -> None:
        """Create required tables and indexes if they do not exist."""
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS map_layouts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                background_path TEXT NOT NULL DEFAULT '',
                grid_size INTEGER DEFAULT 20,
                canvas_width INTEGER DEFAULT 4000,
                canvas_height INTEGER DEFAULT 3000,
                background_scale REAL DEFAULT 1.0,
                background_x REAL DEFAULT 0.0,
                background_y REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS cameras (
                id TEXT PRIMARY KEY,
                layout_id TEXT NOT NULL DEFAULT 'default',
                name TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                port INTEGER DEFAULT 554,
                camera_type TEXT DEFAULT 'Fixed',
                pos_x REAL DEFAULT 0.0,
                pos_y REAL DEFAULT 0.0,
                rotation REAL DEFAULT 0.0,
                display_scale REAL DEFAULT 1.0,
                status INTEGER DEFAULT 0,
                last_check TEXT,
                notes TEXT DEFAULT '',
                zone TEXT DEFAULT '',
                dvr_origin TEXT DEFAULT '',
                layer_id TEXT DEFAULT '',
                location_image_path TEXT DEFAULT '',
                device_kind TEXT DEFAULT 'Camera',
                variant TEXT DEFAULT '',
                ping_enabled INTEGER DEFAULT 1,
                fov_degrees INTEGER DEFAULT 80,
                object_locked INTEGER DEFAULT 0,
                z_index INTEGER DEFAULT 0,
                object_visible INTEGER DEFAULT 1,
                badge_text TEXT DEFAULT '',
                layer_display_name TEXT DEFAULT '',
                is_placed INTEGER DEFAULT 0,
                FOREIGN KEY (layout_id) REFERENCES map_layouts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS device_links (
                id TEXT PRIMARY KEY,
                layout_id TEXT NOT NULL DEFAULT 'default',
                source_device_id TEXT NOT NULL,
                target_device_id TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (layout_id) REFERENCES map_layouts(id) ON DELETE CASCADE,
                FOREIGN KEY (source_device_id) REFERENCES cameras(id) ON DELETE CASCADE,
                FOREIGN KEY (target_device_id) REFERENCES cameras(id) ON DELETE CASCADE,
                UNIQUE(layout_id, source_device_id, target_device_id)
            );

            CREATE TABLE IF NOT EXISTS canvas_layers (
                id TEXT PRIMARY KEY,
                layout_id TEXT NOT NULL DEFAULT 'default',
                name TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0,
                visible INTEGER DEFAULT 1,
                locked INTEGER DEFAULT 0,
                group_id TEXT DEFAULT '',
                is_group INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (layout_id) REFERENCES map_layouts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS drawing_shapes (
                id TEXT PRIMARY KEY,
                layout_id TEXT NOT NULL DEFAULT 'default',
                shape_type TEXT NOT NULL,
                points TEXT NOT NULL,
                color TEXT DEFAULT '#ef4444',
                line_thickness INTEGER DEFAULT 2,
                label TEXT DEFAULT '',
                image_path TEXT DEFAULT '',
                layer_id TEXT DEFAULT '',
                display_name TEXT DEFAULT '',
                object_locked INTEGER DEFAULT 0,
                z_index INTEGER DEFAULT 0,
                fill_color TEXT DEFAULT '',
                object_visible INTEGER DEFAULT 1,
                FOREIGN KEY (layout_id) REFERENCES map_layouts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS ping_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id TEXT NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                is_online INTEGER NOT NULL,
                latency REAL,
                FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_cameras_layout_placed
                ON cameras(layout_id, is_placed);
            CREATE INDEX IF NOT EXISTS idx_drawing_shapes_layout
                ON drawing_shapes(layout_id);
            CREATE INDEX IF NOT EXISTS idx_canvas_layers_layout_position
                ON canvas_layers(layout_id, position);
            CREATE INDEX IF NOT EXISTS idx_device_links_layout
                ON device_links(layout_id);
            CREATE INDEX IF NOT EXISTS idx_ping_history_camera_time
                ON ping_history(camera_id, timestamp);
            """
        )
        self._add_missing_columns(
            "cameras",
            {
                "zone": "TEXT DEFAULT ''",
                "dvr_origin": "TEXT DEFAULT ''",
                "display_scale": "REAL DEFAULT 1.0",
                "layer_id": "TEXT DEFAULT ''",
                "location_image_path": "TEXT DEFAULT ''",
                "device_kind": "TEXT DEFAULT 'Camera'",
                "variant": "TEXT DEFAULT ''",
                "ping_enabled": "INTEGER DEFAULT 1",
                "fov_degrees": "INTEGER DEFAULT 80",
                "object_locked": "INTEGER DEFAULT 0",
                "z_index": "INTEGER DEFAULT 0",
                "object_visible": "INTEGER DEFAULT 1",
                "badge_text": "TEXT DEFAULT ''",
                "layer_display_name": "TEXT DEFAULT ''",
            },
        )
        self._add_missing_columns(
            "canvas_layers",
            {
                "group_id": "TEXT DEFAULT ''",
                "is_group": "INTEGER DEFAULT 0",
            },
        )
        self._add_missing_columns(
            "drawing_shapes",
            {
                "image_path": "TEXT DEFAULT ''",
                "layer_id": "TEXT DEFAULT ''",
                "display_name": "TEXT DEFAULT ''",
                "object_locked": "INTEGER DEFAULT 0",
                "z_index": "INTEGER DEFAULT 0",
                "fill_color": "TEXT DEFAULT ''",
                "object_visible": "INTEGER DEFAULT 1",
            },
        )
        self._add_missing_columns(
            "map_layouts",
            {
                "canvas_width": "INTEGER DEFAULT 4000",
                "canvas_height": "INTEGER DEFAULT 3000",
                "background_scale": "REAL DEFAULT 1.0",
                "background_x": "REAL DEFAULT 0.0",
                "background_y": "REAL DEFAULT 0.0",
            },
        )
        self.execute("DROP INDEX IF EXISTS idx_cameras_ip_address")
        self.execute("DROP INDEX IF EXISTS idx_cameras_layout_ip_address")
        self.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_cameras_layout_ip_address_present
            ON cameras(layout_id, ip_address)
            WHERE COALESCE(ip_address, '') <> ''
            """
        )

    def _add_missing_columns(self, table_name: str, columns: dict[str, str]) -> None:
        """Add lightweight migration columns for existing local databases."""
        existing = {row["name"] for row in self.fetch_all(f"PRAGMA table_info({table_name})")}
        for column_name, column_definition in columns.items():
            if column_name not in existing:
                self.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        """Execute a write query and commit it."""
        cursor = self.connection.execute(query, params)
        self.connection.commit()
        return cursor

    def fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        """Fetch a single row."""
        return self.connection.execute(query, params).fetchone()

    def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        """Fetch all matching rows."""
        return list(self.connection.execute(query, params).fetchall())

    def close(self) -> None:
        """Close the SQLite connection."""
        self.connection.close()
