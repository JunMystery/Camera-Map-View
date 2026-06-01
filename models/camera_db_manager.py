"""SQLite database manager for camera map persistence."""

import shutil
import sqlite3
from pathlib import Path
from typing import Any


class CameraDbManager:
    """Manage a single SQLite connection and schema initialization."""

    def __init__(self, db_path: str | Path = "assets/data/camera_manager.db") -> None:
        self.db_path = Path(db_path)
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
                status INTEGER DEFAULT 0,
                last_check TEXT,
                notes TEXT DEFAULT '',
                zone TEXT DEFAULT '',
                dvr_origin TEXT DEFAULT '',
                is_placed INTEGER DEFAULT 0,
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
            CREATE UNIQUE INDEX IF NOT EXISTS idx_cameras_layout_ip_address
                ON cameras(layout_id, ip_address);
            CREATE INDEX IF NOT EXISTS idx_drawing_shapes_layout
                ON drawing_shapes(layout_id);
            CREATE INDEX IF NOT EXISTS idx_ping_history_camera_time
                ON ping_history(camera_id, timestamp);
            """
        )
        self.execute(
            """
            INSERT OR IGNORE INTO map_layouts (id, name, background_path)
            VALUES (?, ?, ?)
            """,
            ("default", "Default Layout", ""),
        )
        self._add_missing_columns("cameras", {"zone": "TEXT DEFAULT ''", "dvr_origin": "TEXT DEFAULT ''"})
        self._add_missing_columns("drawing_shapes", {"image_path": "TEXT DEFAULT ''"})
        self._add_missing_columns(
            "map_layouts",
            {
                "canvas_width": "INTEGER DEFAULT 4000",
                "canvas_height": "INTEGER DEFAULT 3000",
                "background_scale": "REAL DEFAULT 1.0",
            },
        )
        self.execute("DROP INDEX IF EXISTS idx_cameras_ip_address")

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
