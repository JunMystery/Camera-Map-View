"""Device-link persistence operations for network topology overlays."""

import sqlite3
import uuid

from models.device_link_model import DeviceLink


class DeviceLinkOperations:
    """Persist directed links between devices in a layout."""

    def add_device_link(self, source_device_id: str, target_device_id: str, layout_id: str = "default") -> bool:
        """Create one source -> target device link if it is valid and unique."""
        if not source_device_id or not target_device_id or source_device_id == target_device_id:
            return False
        if not self._device_in_layout(source_device_id, layout_id) or not self._device_in_layout(target_device_id, layout_id):
            return False
        if self._would_create_cycle(source_device_id, target_device_id, layout_id):
            return False
        try:
            self.db.execute(
                """
                INSERT INTO device_links (id, layout_id, source_device_id, target_device_id)
                VALUES (?, ?, ?, ?)
                """,
                (f"link_{uuid.uuid4().hex}", layout_id, source_device_id, target_device_id),
            )
            return True
        except sqlite3.IntegrityError:
            return False

    def replace_device_links(self, source_device_id: str, target_device_ids: list[str], layout_id: str = "default") -> None:
        """Replace all outgoing links for one source device."""
        self.db.execute(
            "DELETE FROM device_links WHERE layout_id = ? AND source_device_id = ?",
            (layout_id, source_device_id),
        )
        for target_device_id in dict.fromkeys(target_device_ids):
            self.add_device_link(source_device_id, target_device_id, layout_id)

    def get_device_links(self, layout_id: str = "default") -> list[DeviceLink]:
        """Return all device links in a layout."""
        rows = self.db.fetch_all(
            """
            SELECT * FROM device_links
            WHERE layout_id = ?
            ORDER BY source_device_id, target_device_id
            """,
            (layout_id,),
        )
        return [self._row_to_device_link(row) for row in rows]

    def get_linked_device_ids(self, source_device_id: str, layout_id: str = "default") -> list[str]:
        """Return outgoing target ids for one source device."""
        rows = self.db.fetch_all(
            """
            SELECT target_device_id FROM device_links
            WHERE layout_id = ? AND source_device_id = ?
            ORDER BY target_device_id
            """,
            (layout_id, source_device_id),
        )
        return [str(row["target_device_id"]) for row in rows]

    def get_incoming_device_ids(self, target_device_id: str, layout_id: str = "default") -> list[str]:
        """Return source ids that point to one target device."""
        rows = self.db.fetch_all(
            """
            SELECT source_device_id FROM device_links
            WHERE layout_id = ? AND target_device_id = ?
            ORDER BY source_device_id
            """,
            (layout_id, target_device_id),
        )
        return [str(row["source_device_id"]) for row in rows]

    def delete_device_link_between(self, source_device_id: str, target_device_id: str, layout_id: str = "default") -> bool:
        """Delete one source -> target link."""
        cursor = self.db.execute(
            """
            DELETE FROM device_links
            WHERE layout_id = ? AND source_device_id = ? AND target_device_id = ?
            """,
            (layout_id, source_device_id, target_device_id),
        )
        return cursor.rowcount > 0

    def _would_create_cycle(self, source_device_id: str, target_device_id: str, layout_id: str) -> bool:
        """Return whether adding source -> target would make a topology cycle."""
        visited: set[str] = set()
        pending = [target_device_id]
        while pending:
            current = pending.pop()
            if current == source_device_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            rows = self.db.fetch_all(
                """
                SELECT target_device_id FROM device_links
                WHERE layout_id = ? AND source_device_id = ?
                """,
                (layout_id, current),
            )
            pending.extend(str(row["target_device_id"]) for row in rows)
        return False

    def delete_device_links_for_device(self, device_id: str, layout_id: str | None = None) -> None:
        """Remove links touching a deleted device."""
        if layout_id is None:
            self.db.execute(
                """
                DELETE FROM device_links
                WHERE source_device_id = ? OR target_device_id = ?
                """,
                (device_id, device_id),
            )
            return
        self.db.execute(
            """
            DELETE FROM device_links
            WHERE layout_id = ? AND (source_device_id = ? OR target_device_id = ?)
            """,
            (layout_id, device_id, device_id),
        )

    def _device_in_layout(self, device_id: str, layout_id: str) -> bool:
        row = self.db.fetch_one(
            "SELECT id FROM cameras WHERE id = ? AND layout_id = ?",
            (device_id, layout_id),
        )
        return row is not None

    def _row_to_device_link(self, row) -> DeviceLink:
        return DeviceLink(
            id=row["id"],
            layout_id=row["layout_id"],
            source_device_id=row["source_device_id"],
            target_device_id=row["target_device_id"],
        )
