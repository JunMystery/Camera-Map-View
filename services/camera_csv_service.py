"""CSV import/export helpers for camera records."""

import csv
import uuid
from pathlib import Path

from models.camera_data_model import Camera

CSV_FIELDS = [
    "id",
    "name",
    "ip_address",
    "port",
    "camera_type",
    "device_kind",
    "variant",
    "ping_enabled",
    "zone",
    "parent_ip",
    "notes",
]


def export_cameras_to_csv(
    cameras: list[Camera],
    file_path: str | Path,
    parent_ip_lookup=None,
) -> None:
    """Write cameras to a CSV file with stable field names."""
    with Path(file_path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for camera in cameras:
            row = {field: getattr(camera, field, "") for field in CSV_FIELDS}
            row["parent_ip"] = parent_ip_lookup(camera.id) if parent_ip_lookup is not None else ""
            row["ping_enabled"] = int(camera.ping_enabled)
            writer.writerow(row)


def import_cameras_from_csv(file_path: str | Path) -> list[Camera]:
    """Read camera rows from a CSV file."""
    cameras: list[Camera] = []
    with Path(file_path).open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            row = _normalized_row(row)
            if not _has_import_data(row):
                continue
            port = _parse_port(row.get("port"))
            if port is None:
                continue
            camera_id = (row.get("id") or "").strip() or f"dev_{uuid.uuid4().hex[:8]}"
            ip_address = (row.get("ip_address") or "").strip()
            ping_value = (row.get("ping_enabled") or "").strip()
            ping_enabled = ping_value not in {"0", "false", "False"} if ping_value else bool(ip_address)
            cameras.append(
                Camera(
                    id=camera_id,
                    name=(row.get("name") or "").strip(),
                    ip_address=ip_address,
                    port=port,
                    camera_type=(row.get("camera_type") or "Fixed").strip(),
                    device_kind=(row.get("device_kind") or "Camera").strip(),
                    variant=(row.get("variant") or row.get("camera_type") or "Fixed").strip(),
                    ping_enabled=ping_enabled,
                    zone=(row.get("zone") or "").strip(),
                    notes=(row.get("notes") or "").strip(),
                )
            )
    return cameras


def _normalized_row(row: dict[str, str | None]) -> dict[str, str | None]:
    """Normalize CSV headers so imports from Excel/manual files still map fields."""
    normalized: dict[str, str | None] = {}
    for key, value in row.items():
        if key is None:
            continue
        normalized[key.strip().lstrip("\ufeff").lower()] = value
    return normalized


def _has_import_data(row: dict[str, str | None]) -> bool:
    data_fields = ["id", "name", "ip_address", "device_kind", "variant", "zone", "parent_ip", "dvr_origin", "notes"]
    return any((row.get(field) or "").strip() for field in data_fields)


def _parse_port(value: str | None) -> int | None:
    try:
        return int((value or "").strip() or 554)
    except ValueError:
        return None
