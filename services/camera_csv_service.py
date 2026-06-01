"""CSV import/export helpers for camera records."""

import csv
from pathlib import Path

from models.camera_data_model import Camera

CSV_FIELDS = ["id", "name", "ip_address", "port", "camera_type", "zone", "dvr_origin", "notes"]


def export_cameras_to_csv(cameras: list[Camera], file_path: str | Path) -> None:
    """Write cameras to a CSV file with stable field names."""
    with Path(file_path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for camera in cameras:
            writer.writerow({field: getattr(camera, field) for field in CSV_FIELDS})


def import_cameras_from_csv(file_path: str | Path) -> list[Camera]:
    """Read camera rows from a CSV file."""
    cameras: list[Camera] = []
    with Path(file_path).open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            cameras.append(
                Camera(
                    id=(row.get("id") or "").strip(),
                    name=(row.get("name") or "").strip(),
                    ip_address=(row.get("ip_address") or "").strip(),
                    port=int(row.get("port") or 554),
                    camera_type=(row.get("camera_type") or "Fixed").strip(),
                    zone=(row.get("zone") or "").strip(),
                    dvr_origin=(row.get("dvr_origin") or "").strip(),
                    notes=(row.get("notes") or "").strip(),
                )
            )
    return cameras
