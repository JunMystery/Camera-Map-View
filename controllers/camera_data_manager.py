"""Camera business logic and CRUD operations."""

import sqlite3
from datetime import datetime
from pathlib import Path

from config.i18n import t
from models.camera_data_model import Camera
from models.camera_db_manager import CameraDbManager
from controllers.camera_layer_operations import CameraLayerOperations
from controllers.camera_layout_operations import CameraLayoutOperations
from controllers.drawing_shape_operations import DrawingShapeOperations
from services.camera_csv_service import export_cameras_to_csv, import_cameras_from_csv
from utils.validators import is_non_empty_text, is_valid_ipv4


class CameraDataManager(CameraLayoutOperations, CameraLayerOperations, DrawingShapeOperations):
    """Validate and persist camera records."""

    def __init__(self, db_path: str | Path = "assets/data/camera_manager.db") -> None:
        self.db = CameraDbManager(db_path)

    def add_camera(self, camera: Camera, is_placed: bool = False, layout_id: str = "default") -> bool:
        """Add a new camera when its id and IP address are unique."""
        if not self._is_valid_camera(camera):
            return False
        self.ensure_default_layers(layout_id)

        try:
            self.db.execute(
                """
                INSERT INTO cameras (
                    id, layout_id, name, ip_address, port, camera_type,
                    pos_x, pos_y, rotation, display_scale, status, last_check, notes,
                    zone, dvr_origin, layer_id, is_placed
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._camera_to_row_params(camera, layout_id, is_placed),
            )
            return True
        except sqlite3.IntegrityError:
            return False

    def update_camera_position(self, camera_id: str, x: float, y: float) -> bool:
        """Persist a camera map position and mark it as placed."""
        cursor = self.db.execute(
            """
            UPDATE cameras
            SET pos_x = ?,
                pos_y = ?,
                is_placed = 1,
                layer_id = CASE WHEN COALESCE(layer_id, '') = '' THEN ? ELSE layer_id END
            WHERE id = ?
            """,
            (x, y, self._camera_fallback_layer_id(camera_id), camera_id),
        )
        return cursor.rowcount > 0

    def update_camera_details(self, camera: Camera) -> bool:
        """Update editable camera metadata while preserving placement state."""
        if not self._is_valid_camera(camera):
            return False

        try:
            cursor = self.db.execute(
                """
                UPDATE cameras
                SET name = ?,
                    ip_address = ?,
                    port = ?,
                    camera_type = ?,
                    rotation = ?,
                    display_scale = ?,
                    status = ?,
                    last_check = ?,
                    notes = ?,
                    zone = ?,
                    dvr_origin = ?,
                    layer_id = ?
                WHERE id = ?
                """,
                (
                    camera.name,
                    camera.ip_address,
                    camera.port,
                    camera.camera_type,
                    camera.rotation,
                    camera.display_scale,
                    int(camera.status),
                    camera.last_check.isoformat() if camera.last_check else None,
                    camera.notes,
                    camera.zone,
                    camera.dvr_origin,
                    camera.layer_id,
                    camera.id,
                ),
            )
            return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            return False

    def update_camera_status(
        self,
        camera_id: str,
        is_online: bool,
        latency_ms: float,
        checked_at: datetime | None = None,
    ) -> bool:
        """Persist the latest camera status and append ping history."""
        timestamp = (checked_at or datetime.now()).isoformat()
        cursor = self.db.execute(
            """
            UPDATE cameras
            SET status = ?, last_check = ?
            WHERE id = ?
            """,
            (int(is_online), timestamp, camera_id),
        )
        if cursor.rowcount == 0:
            return False

        self.db.execute(
            """
            INSERT INTO ping_history (camera_id, timestamp, is_online, latency)
            VALUES (?, ?, ?, ?)
            """,
            (camera_id, timestamp, int(is_online), latency_ms),
        )
        return True

    def delete_camera(self, camera_id: str) -> bool:
        """Delete a camera by id."""
        cursor = self.db.execute("DELETE FROM cameras WHERE id = ?", (camera_id,))
        return cursor.rowcount > 0

    def unplace_camera(self, camera_id: str) -> bool:
        """Remove a camera from the map while keeping it in storage."""
        cursor = self.db.execute(
            """
            UPDATE cameras
            SET is_placed = 0
            WHERE id = ?
            """,
            (camera_id,),
        )
        return cursor.rowcount > 0

    def import_cameras_csv(self, file_path: str | Path, layout_id: str = "default") -> int:
        """Import cameras from CSV and return the number of added records."""
        added = 0
        for camera in import_cameras_from_csv(file_path):
            if self.add_camera(camera, layout_id=layout_id):
                added += 1
        return added

    def export_cameras_csv(self, file_path: str | Path, layout_id: str = "default") -> None:
        """Export all cameras to CSV."""
        export_cameras_to_csv(self.get_all_cameras(layout_id), file_path)

    def get_camera(self, camera_id: str) -> Camera | None:
        """Return one camera by id."""
        row = self.db.fetch_one("SELECT * FROM cameras WHERE id = ?", (camera_id,))
        if row:
            self.ensure_default_layers(row["layout_id"])
            row = self.db.fetch_one("SELECT * FROM cameras WHERE id = ?", (camera_id,))
        return self._row_to_camera(row) if row else None

    def get_all_cameras(self, layout_id: str = "default") -> list[Camera]:
        """Return all cameras ordered by name."""
        self.ensure_default_layers(layout_id)
        rows = self.db.fetch_all("SELECT * FROM cameras WHERE layout_id = ? ORDER BY name", (layout_id,))
        return [self._row_to_camera(row) for row in rows]

    def get_unplaced_cameras(self, layout_id: str = "default") -> list[Camera]:
        """Return cameras that should appear in the sidebar."""
        self.ensure_default_layers(layout_id)
        rows = self.db.fetch_all(
            "SELECT * FROM cameras WHERE layout_id = ? AND is_placed = 0 ORDER BY name",
            (layout_id,),
        )
        return [self._row_to_camera(row) for row in rows]

    def get_placed_cameras(self, layout_id: str = "default") -> list[Camera]:
        """Return cameras that should appear on the map."""
        self.ensure_default_layers(layout_id)
        rows = self.db.fetch_all(
            "SELECT * FROM cameras WHERE layout_id = ? AND is_placed = 1 ORDER BY name",
            (layout_id,),
        )
        return [self._row_to_camera(row) for row in rows]

    def get_all_cameras_for_ping(self, layout_id: str = "default") -> list[Camera]:
        """Return cameras that should be monitored by PingService."""
        return self.get_all_cameras(layout_id)

    def get_ping_history(self, camera_id: str) -> list[dict[str, object]]:
        """Return ping history records for one camera."""
        rows = self.db.fetch_all(
            """
            SELECT camera_id, timestamp, is_online, latency
            FROM ping_history
            WHERE camera_id = ?
            ORDER BY timestamp
            """,
            (camera_id,),
        )
        return [
            {
                "camera_id": row["camera_id"],
                "timestamp": row["timestamp"],
                "is_online": bool(row["is_online"]),
                "latency": row["latency"],
            }
            for row in rows
        ]

    def update_camera_rotation(self, camera_id: str, rotation: float) -> bool:
        """Persist a camera viewing direction."""
        cursor = self.db.execute(
            "UPDATE cameras SET rotation = ? WHERE id = ?",
            (rotation % 360, camera_id),
        )
        return cursor.rowcount > 0

    def update_camera_scale(self, camera_id: str, display_scale: float) -> bool:
        """Persist a camera marker display scale."""
        cursor = self.db.execute(
            "UPDATE cameras SET display_scale = ? WHERE id = ?",
            (max(0.5, min(display_scale, 3.0)), camera_id),
        )
        return cursor.rowcount > 0

    def seed_default_cameras(self, layout_id: str = "default") -> None:
        """Create sample cameras only when the database is empty."""
        if layout_id != "default" or self.get_all_cameras(layout_id):
            return

        for camera in self._default_cameras():
            self.add_camera(camera, layout_id=layout_id)

    def _camera_to_row_params(
        self,
        camera: Camera,
        layout_id: str,
        is_placed: bool,
    ) -> tuple[object, ...]:
        return (
            camera.id,
            layout_id,
            camera.name,
            camera.ip_address,
            camera.port,
            camera.camera_type,
            camera.position_x,
            camera.position_y,
            camera.rotation,
            camera.display_scale,
            int(camera.status),
            camera.last_check.isoformat() if camera.last_check else None,
            camera.notes,
            camera.zone,
            camera.dvr_origin,
            self._resolved_layer_id(camera.layer_id, layout_id),
            int(is_placed),
        )

    def _is_valid_camera(self, camera: Camera) -> bool:
        return (
            is_non_empty_text(camera.id)
            and is_non_empty_text(camera.name)
            and is_valid_ipv4(camera.ip_address)
            and 1 <= camera.port <= 65535
        )

    def _row_to_camera(self, row: sqlite3.Row) -> Camera:
        return Camera.from_dict(
            {
                "id": row["id"],
                "name": row["name"],
                "ip_address": row["ip_address"],
                "port": row["port"],
                "camera_type": row["camera_type"],
                "position_x": row["pos_x"],
                "position_y": row["pos_y"],
                "rotation": row["rotation"],
                "display_scale": row["display_scale"] or 1.0,
                "status": bool(row["status"]),
                "last_check": row["last_check"],
                "notes": row["notes"] or "",
                "zone": row["zone"] or "",
                "dvr_origin": row["dvr_origin"] or "",
                "layer_id": row["layer_id"] or "",
            }
        )

    def _default_cameras(self) -> list[Camera]:
        return [
            Camera("cam_01", t("seed.cam_01.name"), "192.168.1.100", 554, "Fixed", status=True, notes=t("seed.cam_01.notes")),
            Camera("cam_02", t("seed.cam_02.name"), "192.168.1.101", 554, "Dome", status=True, notes=t("seed.cam_02.notes")),
            Camera("cam_03", t("seed.cam_03.name"), "192.168.1.102", 554, "Fixed", status=False, notes=t("seed.cam_03.notes")),
            Camera("cam_04", t("seed.cam_04.name"), "192.168.1.103", 554, "PTZ", status=True, rotation=45.0, notes=t("seed.cam_04.notes")),
            Camera("cam_05", t("seed.cam_05.name"), "192.168.1.104", 554, "Dome", status=False, notes=t("seed.cam_05.notes")),
        ]

    def _camera_fallback_layer_id(self, camera_id: str) -> str:
        row = self.db.fetch_one("SELECT layout_id FROM cameras WHERE id = ?", (camera_id,))
        if row is None:
            return ""
        self.ensure_default_layers(row["layout_id"])
        return self.first_layer_id(row["layout_id"])

    def _resolved_layer_id(self, layer_id: str, layout_id: str) -> str:
        if layer_id and any(layer.id == layer_id for layer in self.get_layers(layout_id)):
            return layer_id
        return self.first_layer_id(layout_id)
