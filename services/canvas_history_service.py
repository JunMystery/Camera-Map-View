"""In-memory undo/redo history for the active canvas layout."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from typing import Any

from controllers.camera_data_manager import CameraDataManager


@dataclass(frozen=True)
class CanvasStateSnapshot:
    """Serializable state for one layout-scoped canvas history entry."""

    layout_id: str
    layout: dict[str, Any]
    cameras: list[dict[str, Any]]
    layers: list[dict[str, Any]]
    drawings: list[dict[str, Any]]
    device_links: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a stable dictionary for hashing and restore."""
        return {
            "layout_id": self.layout_id,
            "layout": self.layout,
            "cameras": self.cameras,
            "layers": self.layers,
            "drawings": self.drawings,
            "device_links": self.device_links,
        }

    def digest(self) -> str:
        """Return a stable hash for change detection."""
        payload = json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CanvasHistoryEntry:
    """One undoable canvas state transition."""

    label: str
    before: CanvasStateSnapshot
    after: CanvasStateSnapshot


class CanvasHistoryManager:
    """Store recent canvas snapshots and restore them on demand."""

    def __init__(
        self,
        snapshot_callback: Callable[[], CanvasStateSnapshot | None],
        restore_callback: Callable[[CanvasStateSnapshot], None],
        changed_callback: Callable[[], None] | None = None,
        limit: int = 10,
    ) -> None:
        self.snapshot_callback = snapshot_callback
        self.restore_callback = restore_callback
        self.changed_callback = changed_callback
        self.limit = limit
        self.undo_stack: list[CanvasHistoryEntry] = []
        self.redo_stack: list[CanvasHistoryEntry] = []
        self._pending_label = ""
        self._pending_before: CanvasStateSnapshot | None = None
        self.is_restoring = False

    def begin(self, label: str) -> bool:
        """Capture the state before a canvas mutation starts."""
        if self.is_restoring or self._pending_before is not None:
            return False
        snapshot = self.snapshot_callback()
        if snapshot is None:
            return False
        self._pending_label = label
        self._pending_before = snapshot
        return True

    def commit(self, label: str = "") -> bool:
        """Capture the state after a canvas mutation and push a history entry."""
        if self.is_restoring or self._pending_before is None:
            return False
        before = self._pending_before
        entry_label = label or self._pending_label
        self._pending_before = None
        self._pending_label = ""
        after = self.snapshot_callback()
        if after is None or before.digest() == after.digest():
            self._notify_changed()
            return False
        self.undo_stack.append(CanvasHistoryEntry(entry_label, before, after))
        if len(self.undo_stack) > self.limit:
            self.undo_stack = self.undo_stack[-self.limit :]
        self.redo_stack.clear()
        self._notify_changed()
        return True

    def cancel(self) -> None:
        """Discard an unfinished history capture."""
        self._pending_before = None
        self._pending_label = ""
        self._notify_changed()

    @contextmanager
    def capture(self, label: str) -> Iterator[None]:
        """Capture one mutation unless another capture is already active."""
        owns_capture = self.begin(label)
        try:
            yield
        finally:
            if owns_capture:
                self.commit(label)

    def undo(self) -> bool:
        """Restore the previous canvas snapshot."""
        if not self.undo_stack:
            return False
        entry = self.undo_stack.pop()
        self._restore(entry.before)
        self.redo_stack.append(entry)
        self._notify_changed()
        return True

    def redo(self) -> bool:
        """Restore the next canvas snapshot."""
        if not self.redo_stack:
            return False
        entry = self.redo_stack.pop()
        self._restore(entry.after)
        self.undo_stack.append(entry)
        self._notify_changed()
        return True

    def clear(self) -> None:
        """Drop all history for the current layout."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.cancel()

    def can_undo(self) -> bool:
        """Return whether undo is available."""
        return bool(self.undo_stack)

    def can_redo(self) -> bool:
        """Return whether redo is available."""
        return bool(self.redo_stack)

    def _restore(self, snapshot: CanvasStateSnapshot) -> None:
        self.is_restoring = True
        try:
            self.restore_callback(snapshot)
        finally:
            self.is_restoring = False

    def _notify_changed(self) -> None:
        if self.changed_callback is not None:
            self.changed_callback()


def capture_layout_snapshot(manager: CameraDataManager, layout_id: str) -> CanvasStateSnapshot | None:
    """Read one layout's canvas state directly from SQLite."""
    if not layout_id or manager.get_layout(layout_id) is None:
        return None
    return CanvasStateSnapshot(
        layout_id=layout_id,
        layout=_row_dict(manager.db.fetch_one("SELECT * FROM map_layouts WHERE id = ?", (layout_id,))),
        cameras=_row_dicts(manager.db.fetch_all("SELECT * FROM cameras WHERE layout_id = ? ORDER BY id", (layout_id,))),
        layers=_row_dicts(
            manager.db.fetch_all("SELECT * FROM canvas_layers WHERE layout_id = ? ORDER BY position, name, id", (layout_id,))
        ),
        drawings=_row_dicts(manager.db.fetch_all("SELECT * FROM drawing_shapes WHERE layout_id = ? ORDER BY id", (layout_id,))),
        device_links=_row_dicts(
            manager.db.fetch_all(
                "SELECT * FROM device_links WHERE layout_id = ? ORDER BY source_device_id, target_device_id, id",
                (layout_id,),
            )
        ),
    )


def restore_layout_snapshot(manager: CameraDataManager, snapshot: CanvasStateSnapshot) -> None:
    """Replace one layout's persisted canvas state with a snapshot."""
    layout_id = snapshot.layout_id
    connection = manager.db.connection
    with connection:
        _restore_layout_row(connection, snapshot.layout)
        connection.execute("DELETE FROM device_links WHERE layout_id = ?", (layout_id,))
        connection.execute("DELETE FROM drawing_shapes WHERE layout_id = ?", (layout_id,))
        connection.execute("DELETE FROM cameras WHERE layout_id = ?", (layout_id,))
        connection.execute("DELETE FROM canvas_layers WHERE layout_id = ?", (layout_id,))
        _insert_rows(connection, "canvas_layers", snapshot.layers)
        _insert_rows(connection, "cameras", snapshot.cameras)
        _insert_rows(connection, "drawing_shapes", snapshot.drawings)
        _insert_rows(connection, "device_links", snapshot.device_links)


def _restore_layout_row(connection: Any, row: dict[str, Any]) -> None:
    connection.execute(
        """
        UPDATE map_layouts
        SET name = ?, background_path = ?, grid_size = ?, canvas_width = ?,
            canvas_height = ?, background_scale = ?, background_x = ?, background_y = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            row.get("name", ""),
            row.get("background_path", ""),
            int(row.get("grid_size") or 20),
            int(row.get("canvas_width") or 4000),
            int(row.get("canvas_height") or 3000),
            float(row.get("background_scale") or 1.0),
            float(row.get("background_x") or 0.0),
            float(row.get("background_y") or 0.0),
            row.get("id", ""),
        ),
    )


def _insert_rows(connection: Any, table_name: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in columns)
    column_sql = ", ".join(columns)
    values = [tuple(row.get(column) for column in columns) for row in rows]
    connection.executemany(f"INSERT INTO {table_name} ({column_sql}) VALUES ({placeholders})", values)


def _row_dict(row: Any | None) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def _row_dicts(rows: list[Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]
