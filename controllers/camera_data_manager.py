"""Camera business logic and CRUD operations."""

import sqlite3
from datetime import datetime
from pathlib import Path

from config.i18n import t
from models.camera_data_model import Camera
from models.camera_db_manager import CameraDbManager
from models.device_catalog import DEVICE_KIND_CAMERA
from controllers.camera_layer_operations import CameraLayerOperations
from controllers.camera_layout_operations import CameraLayoutOperations
from controllers.device_link_operations import DeviceLinkOperations
from controllers.drawing_shape_operations import DrawingShapeOperations
from services.camera_csv_service import export_cameras_to_csv, import_cameras_from_csv
from utils.validators import is_non_empty_text, is_valid_ipv4


class CameraDataManager(CameraLayoutOperations, CameraLayerOperations, DeviceLinkOperations, DrawingShapeOperations):
    """Validate and persist camera records."""

    def __init__(self, db_path: str | Path = "assets/data/camera_manager.db") -> None:
        self.db = CameraDbManager(db_path)

    def add_camera(self, camera: Camera, is_placed: bool = False, layout_id: str = "default") -> bool:
        """Add a new camera when its id and IP address are unique."""
        if not self._is_valid_camera(camera) or self.get_layout(layout_id) is None:
            return False
        self.ensure_default_layers(layout_id)

        try:
            self.db.execute(
                """
                INSERT INTO cameras (
                    id, layout_id, name, ip_address, port, camera_type,
                    pos_x, pos_y, rotation, display_scale, status, last_check, notes,
                    zone, dvr_origin, layer_id, location_image_path, device_kind,
                    variant, ping_enabled, fov_degrees, object_locked, z_index, object_visible, badge_text, is_placed
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    def update_camera_position_in_layout(self, camera_id: str, x: float, y: float, layout_id: str) -> bool:
        """Persist a camera map position only inside the active layout."""
        cursor = self.db.execute(
            """
            UPDATE cameras
            SET pos_x = ?,
                pos_y = ?,
                is_placed = 1,
                layer_id = CASE WHEN COALESCE(layer_id, '') = '' THEN ? ELSE layer_id END
            WHERE id = ? AND layout_id = ?
            """,
            (x, y, self.first_layer_id(layout_id), camera_id, layout_id),
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
                    layer_id = ?,
                    location_image_path = ?,
                    device_kind = ?,
                    variant = ?,
                    ping_enabled = ?,
                    fov_degrees = ?,
                    object_locked = ?,
                    z_index = ?,
                    object_visible = ?,
                    badge_text = ?
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
                    camera.location_image_path,
                    camera.device_kind,
                    camera.effective_variant(),
                    int(camera.ping_enabled),
                    int(camera.fov_degrees),
                    int(camera.object_locked),
                    int(camera.z_index),
                    int(camera.object_visible),
                    camera.badge_text[:3].upper(),
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
        self.delete_device_links_for_device(camera_id)
        cursor = self.db.execute("DELETE FROM cameras WHERE id = ?", (camera_id,))
        return cursor.rowcount > 0

    def delete_camera_in_layout(self, camera_id: str, layout_id: str) -> bool:
        """Delete a camera only when it belongs to the active layout."""
        self.delete_device_links_for_device(camera_id, layout_id)
        cursor = self.db.execute("DELETE FROM cameras WHERE id = ? AND layout_id = ?", (camera_id, layout_id))
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

    def unplace_camera_in_layout(self, camera_id: str, layout_id: str) -> bool:
        """Remove a camera from the active map while keeping it in storage."""
        cursor = self.db.execute(
            """
            UPDATE cameras
            SET is_placed = 0
            WHERE id = ? AND layout_id = ?
            """,
            (camera_id, layout_id),
        )
        return cursor.rowcount > 0

    def import_cameras_csv(self, file_path: str | Path, layout_id: str = "default") -> int:
        """Import cameras from CSV and return the number of added or updated records."""
        imported = 0
        for camera in import_cameras_from_csv(file_path):
            if self.upsert_camera_from_import(camera, layout_id):
                imported += 1
        return imported

    def upsert_camera_from_import(self, camera: Camera, layout_id: str = "default") -> bool:
        """Add or replace importable camera metadata inside one layout."""
        if self.get_layout(layout_id) is None:
            return False
        existing = self.get_camera_in_layout(camera.id, layout_id)
        if existing is None:
            return self.add_camera(camera, layout_id=layout_id)
        if not self._is_valid_camera(camera):
            return False
        conflicting_ip = self._camera_id_for_ip(camera.ip_address, layout_id)
        if conflicting_ip and conflicting_ip != camera.id:
            return False
        merged = self._merged_import_camera(existing, camera)
        try:
            cursor = self.db.execute(
                """
                UPDATE cameras
                SET name = ?,
                    ip_address = ?,
                    port = ?,
                    camera_type = ?,
                    notes = ?,
                    zone = ?,
                    device_kind = ?,
                    variant = ?,
                    ping_enabled = ?
                WHERE id = ? AND layout_id = ?
                """,
                (
                    merged.name,
                    merged.ip_address,
                    merged.port,
                    merged.camera_type,
                    merged.notes,
                    merged.zone,
                    merged.device_kind,
                    merged.effective_variant(),
                    int(merged.ping_enabled),
                    merged.id,
                    layout_id,
                ),
            )
            return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            return False

    def export_cameras_csv(self, file_path: str | Path, layout_id: str = "default") -> None:
        """Export all cameras to CSV."""
        export_cameras_to_csv(
            self.get_all_cameras(layout_id),
            file_path,
            lambda camera_id: self.parent_ip_for_device(camera_id, layout_id),
        )

    def parent_ip_for_device(self, device_id: str, layout_id: str = "default") -> str:
        """Return comma-separated direct parent IP addresses derived from device links."""
        rows = self.db.fetch_all(
            """
            SELECT parent.ip_address
            FROM device_links AS links
            JOIN cameras AS parent
              ON parent.id = links.target_device_id
             AND parent.layout_id = links.layout_id
            WHERE links.layout_id = ?
              AND links.source_device_id = ?
              AND COALESCE(parent.ip_address, '') <> ''
            ORDER BY parent.name, parent.ip_address, parent.id
            """,
            (layout_id, device_id),
        )
        return ", ".join(dict.fromkeys(str(row["ip_address"]) for row in rows if row["ip_address"]))

    def get_camera(self, camera_id: str) -> Camera | None:
        """Return one camera by id."""
        row = self.db.fetch_one("SELECT * FROM cameras WHERE id = ?", (camera_id,))
        if row:
            self.ensure_default_layers(row["layout_id"])
            row = self.db.fetch_one("SELECT * FROM cameras WHERE id = ?", (camera_id,))
        return self._row_to_camera(row) if row else None

    def get_camera_in_layout(self, camera_id: str, layout_id: str) -> Camera | None:
        """Return one camera only when it belongs to the requested layout."""
        row = self.db.fetch_one("SELECT * FROM cameras WHERE id = ? AND layout_id = ?", (camera_id, layout_id))
        if row:
            self.ensure_default_layers(layout_id)
            row = self.db.fetch_one("SELECT * FROM cameras WHERE id = ? AND layout_id = ?", (camera_id, layout_id))
        return self._row_to_camera(row) if row else None

    def get_all_cameras(self, layout_id: str = "default") -> list[Camera]:
        """Return all cameras ordered by name."""
        if self.get_layout(layout_id) is None:
            return []
        self.ensure_default_layers(layout_id)
        rows = self.db.fetch_all("SELECT * FROM cameras WHERE layout_id = ? ORDER BY name", (layout_id,))
        return [self._row_to_camera(row) for row in rows]

    def get_unplaced_cameras(self, layout_id: str = "default") -> list[Camera]:
        """Return cameras that should appear in the sidebar."""
        if self.get_layout(layout_id) is None:
            return []
        self.ensure_default_layers(layout_id)
        rows = self.db.fetch_all(
            "SELECT * FROM cameras WHERE layout_id = ? AND is_placed = 0 ORDER BY name",
            (layout_id,),
        )
        return [self._row_to_camera(row) for row in rows]

    def get_placed_cameras(self, layout_id: str = "default") -> list[Camera]:
        """Return cameras that should appear on the map."""
        if self.get_layout(layout_id) is None:
            return []
        self.ensure_default_layers(layout_id)
        rows = self.db.fetch_all(
            "SELECT * FROM cameras WHERE layout_id = ? AND is_placed = 1 ORDER BY name",
            (layout_id,),
        )
        return [self._row_to_camera(row) for row in rows]

    def get_all_cameras_for_ping(self, layout_id: str = "default") -> list[Camera]:
        """Return cameras that should be monitored by PingService."""
        return [camera for camera in self.get_all_cameras(layout_id) if camera.ping_enabled and is_valid_ipv4(camera.ip_address)]

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

    def update_camera_rotation_in_layout(self, camera_id: str, rotation: float, layout_id: str) -> bool:
        """Persist a camera viewing direction only inside one layout."""
        cursor = self.db.execute(
            "UPDATE cameras SET rotation = ? WHERE id = ? AND layout_id = ?",
            (rotation % 360, camera_id, layout_id),
        )
        return cursor.rowcount > 0

    def update_camera_scale(self, camera_id: str, display_scale: float) -> bool:
        """Persist a camera marker display scale."""
        cursor = self.db.execute(
            "UPDATE cameras SET display_scale = ? WHERE id = ?",
            (max(0.5, min(display_scale, 3.0)), camera_id),
        )
        return cursor.rowcount > 0

    def update_camera_scale_in_layout(self, camera_id: str, display_scale: float, layout_id: str) -> bool:
        """Persist a camera marker display scale only inside one layout."""
        cursor = self.db.execute(
            "UPDATE cameras SET display_scale = ? WHERE id = ? AND layout_id = ?",
            (max(0.5, min(display_scale, 3.0)), camera_id, layout_id),
        )
        return cursor.rowcount > 0

    def seed_default_cameras(self, layout_id: str = "default") -> None:
        """Create sample cameras only when the database is empty."""
        return

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
            camera.location_image_path,
            camera.device_kind,
            camera.effective_variant(),
            int(camera.ping_enabled),
            int(camera.fov_degrees),
            int(camera.object_locked),
            int(camera.z_index),
            int(camera.object_visible),
            camera.badge_text[:3].upper(),
            int(is_placed),
        )

    def _is_valid_camera(self, camera: Camera) -> bool:
        has_valid_identity = is_non_empty_text(camera.id) and is_non_empty_text(camera.name) and 1 <= camera.port <= 65535
        if not has_valid_identity:
            return False
        return not camera.ip_address or is_valid_ipv4(camera.ip_address)

    def _camera_id_for_ip(self, ip_address: str, layout_id: str) -> str:
        if not ip_address:
            return ""
        row = self.db.fetch_one(
            "SELECT id FROM cameras WHERE layout_id = ? AND ip_address = ?",
            (layout_id, ip_address),
        )
        return str(row["id"]) if row else ""

    def _merged_import_camera(self, existing: Camera, imported: Camera) -> Camera:
        return Camera(
            id=existing.id,
            name=imported.name,
            ip_address=imported.ip_address,
            port=imported.port,
            camera_type=imported.camera_type,
            position_x=existing.position_x,
            position_y=existing.position_y,
            rotation=existing.rotation,
            display_scale=existing.display_scale,
            status=existing.status,
            last_check=existing.last_check,
            notes=imported.notes,
            zone=imported.zone,
            dvr_origin=existing.dvr_origin,
            layer_id=existing.layer_id,
            location_image_path=existing.location_image_path,
            device_kind=imported.device_kind,
            variant=imported.effective_variant(),
            ping_enabled=imported.ping_enabled,
            fov_degrees=existing.fov_degrees,
            object_locked=existing.object_locked,
            z_index=existing.z_index,
            object_visible=existing.object_visible,
            badge_text=existing.badge_text,
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
                "location_image_path": row["location_image_path"] or "",
                "device_kind": row["device_kind"] or DEVICE_KIND_CAMERA,
                "variant": row["variant"] or row["camera_type"] or "",
                "ping_enabled": bool(row["ping_enabled"]),
                "fov_degrees": int(row["fov_degrees"] or 80),
                "object_locked": bool(row["object_locked"]),
                "z_index": int(row["z_index"] or 0),
                "object_visible": bool(row["object_visible"]),
                "badge_text": row["badge_text"] or "",
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
