"""Export and import one camera map layout as a portable ZIP package."""

from dataclasses import asdict
import json
from pathlib import Path
import shutil
import uuid
from zipfile import ZipFile, ZIP_DEFLATED

from controllers.camera_data_manager import CameraDataManager
from models.camera_data_model import Camera
from models.canvas_layer_model import CanvasLayer
from models.device_link_model import DeviceLink
from models.drawing_shape_model import DrawingShape
from models.map_layout_model import MapLayout

SCHEMA_VERSION = 3


def export_map_package(
    path: str | Path,
    layout: MapLayout,
    settings: dict[str, object],
    camera_info_visibility: dict[str, bool],
    cameras: list[dict[str, object]],
    layers: list[CanvasLayer],
    drawings: list[DrawingShape],
    device_links: list[DeviceLink] | None = None,
) -> bool:
    """Write a current-layout package to disk."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "layout": asdict(layout),
        "settings": settings,
        "camera_info_visibility": camera_info_visibility,
        "cameras": cameras,
        "layers": [asdict(layer) for layer in layers],
        "drawings": [asdict(shape) for shape in drawings],
        "device_links": [asdict(link) for link in device_links or []],
        "assets": {"background": "", "drawings": {}, "camera_photos": {}},
    }
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        _add_layout_assets(archive, manifest, layout, cameras, drawings)
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return True


def import_map_package(path: str | Path, manager: CameraDataManager) -> str | None:
    """Import a package into a new layout and return the new layout id."""
    source = Path(path)
    if not source.exists():
        return None
    with ZipFile(source, "r") as archive:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        if int(manifest.get("schema_version", 0)) not in {1, 2, SCHEMA_VERSION}:
            return None
        layout = _create_import_layout(manager, manifest)
        asset_dir = Path("assets/maps") / f"package_{layout.id}"
        asset_dir.mkdir(parents=True, exist_ok=True)
        layer_map = _import_layers(manager, manifest.get("layers", []), layout.id)
        _apply_layout_assets(archive, manifest, asset_dir, layout)
        manager.update_layout(layout)
        camera_id_map = _import_cameras(manager, archive, manifest, asset_dir, layout.id, layer_map)
        _import_device_links(manager, manifest, layout.id, camera_id_map)
        _import_drawings(manager, archive, manifest, asset_dir, layout.id, layer_map)
        return layout.id


def _add_layout_assets(
    archive: ZipFile,
    manifest: dict[str, object],
    layout: MapLayout,
    cameras: list[dict[str, object]],
    drawings: list[DrawingShape],
) -> dict[str, str]:
    assets = manifest["assets"]
    if isinstance(assets, dict) and layout.background_path:
        background = _add_asset(archive, layout.background_path, "background")
        if background:
            assets["background"] = background
    drawing_assets = assets.get("drawings") if isinstance(assets, dict) else None
    if not isinstance(drawing_assets, dict):
        return
    for shape in drawings:
        if shape.shape_type != "Image" or not shape.image_path:
            continue
        asset_name = _add_asset(archive, shape.image_path, f"drawing_{shape.id}")
        if asset_name:
            drawing_assets[shape.id] = asset_name
    camera_assets = assets.get("camera_photos") if isinstance(assets, dict) else None
    if not isinstance(camera_assets, dict):
        return
    for camera in cameras:
        camera_id = str(camera.get("id") or "")
        photo_path = str(camera.get("location_image_path") or "")
        if not camera_id or not photo_path:
            continue
        asset_name = _add_asset(archive, photo_path, f"camera_{camera_id}")
        if asset_name:
            camera_assets[camera_id] = asset_name


def _add_asset(archive: ZipFile, file_path: str, prefix: str) -> str:
    source = Path(file_path)
    if not source.exists() or not source.is_file():
        return ""
    safe_name = f"{prefix}_{uuid.uuid4().hex[:8]}{source.suffix.lower()}"
    archive.write(source, f"assets/{safe_name}")
    return f"assets/{safe_name}"


def _create_import_layout(manager: CameraDataManager, manifest: dict[str, object]) -> MapLayout:
    layout_data = dict(manifest.get("layout", {}))
    name = str(layout_data.get("name") or "Imported Layout")
    layout = manager.create_layout(f"{name} Imported")
    layout.grid_size = int(layout_data.get("grid_size") or layout.grid_size)
    layout.canvas_width = int(layout_data.get("canvas_width") or layout.canvas_width)
    layout.canvas_height = int(layout_data.get("canvas_height") or layout.canvas_height)
    layout.background_scale = float(layout_data.get("background_scale") or layout.background_scale)
    return layout


def _import_layers(manager: CameraDataManager, rows: list[dict[str, object]], layout_id: str) -> dict[str, str]:
    manager.ensure_default_layers(layout_id)
    layer_map: dict[str, str] = {}
    legacy_target_id = manager.first_layer_id(layout_id)
    for row in rows:
        old_id = str(row.get("id") or "")
        kind = _default_kind(old_id)
        if kind:
            layer_map[old_id] = legacy_target_id
            continue
        new_id = f"layer_{uuid.uuid4().hex}"
        layer_map[old_id] = new_id
        manager.db.execute(
            """
            INSERT OR REPLACE INTO canvas_layers (id, layout_id, name, position, visible, locked)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id,
                layout_id,
                str(row.get("name") or "Layer"),
                int(row.get("position") or 0),
                int(bool(row.get("visible", True))),
                int(bool(row.get("locked", False))),
            ),
        )
    return layer_map


def _apply_layout_assets(archive: ZipFile, manifest: dict[str, object], asset_dir: Path, layout: MapLayout) -> None:
    assets = manifest.get("assets", {})
    background = assets.get("background") if isinstance(assets, dict) else ""
    if isinstance(background, str) and background:
        layout.background_path = _extract_asset(archive, background, asset_dir)


def _import_cameras(
    manager: CameraDataManager,
    archive: ZipFile,
    manifest: dict[str, object],
    asset_dir: Path,
    layout_id: str,
    layer_map: dict[str, str],
) -> None:
    assets = manifest.get("assets", {})
    camera_assets = assets.get("camera_photos", {}) if isinstance(assets, dict) else {}
    camera_asset_dir = asset_dir / "camera_photos"
    camera_asset_dir.mkdir(parents=True, exist_ok=True)
    camera_id_map: dict[str, str] = {}
    for row in manifest.get("cameras", []):
        data = dict(row)
        old_id = str(data.get("id") or "")
        is_placed = bool(data.pop("is_placed", False))
        data["id"] = _unique_id(old_id or "cam", "cam")
        camera_id_map[old_id] = str(data["id"])
        data["layer_id"] = layer_map.get(str(data.get("layer_id") or ""), manager.first_layer_id(layout_id))
        asset_name = camera_assets.get(old_id) if isinstance(camera_assets, dict) else ""
        if asset_name:
            data["location_image_path"] = _extract_asset(archive, str(asset_name), camera_asset_dir)
        elif data.get("location_image_path"):
            data["location_image_path"] = ""
        manager.add_camera(Camera.from_dict(data), is_placed=is_placed, layout_id=layout_id)
    return camera_id_map


def _import_device_links(
    manager: CameraDataManager,
    manifest: dict[str, object],
    layout_id: str,
    camera_id_map: dict[str, str],
) -> None:
    for row in manifest.get("device_links", []):
        source_id = camera_id_map.get(str(row.get("source_device_id") or ""))
        target_id = camera_id_map.get(str(row.get("target_device_id") or ""))
        if source_id and target_id:
            manager.add_device_link(source_id, target_id, layout_id)


def _import_drawings(
    manager: CameraDataManager,
    archive: ZipFile,
    manifest: dict[str, object],
    asset_dir: Path,
    layout_id: str,
    layer_map: dict[str, str],
) -> None:
    assets = manifest.get("assets", {})
    drawing_assets = assets.get("drawings", {}) if isinstance(assets, dict) else {}
    for row in manifest.get("drawings", []):
        data = dict(row)
        old_id = str(data.get("id") or "")
        data["id"] = _unique_id(old_id or "shape", "shape")
        data["layer_id"] = layer_map.get(str(data.get("layer_id") or ""), _default_layer_for_shape(manager, layout_id, data))
        if data.get("shape_type") == "Image":
            asset_name = drawing_assets.get(old_id) if isinstance(drawing_assets, dict) else ""
            if asset_name:
                data["image_path"] = _extract_asset(archive, str(asset_name), asset_dir)
        manager.add_drawing_shape(DrawingShape(**data), layout_id)


def _extract_asset(archive: ZipFile, asset_name: str, asset_dir: Path) -> str:
    if asset_name not in archive.namelist():
        return ""
    target = asset_dir / Path(asset_name).name
    with archive.open(asset_name) as source, target.open("wb") as output:
        shutil.copyfileobj(source, output)
    return str(target)


def _default_kind(layer_id: str) -> str:
    for kind in ("cameras", "drawings", "images", "text"):
        if layer_id.endswith(f"_{kind}"):
            return kind
    return ""


def _default_layer_for_shape(manager: CameraDataManager, layout_id: str, data: dict[str, object]) -> str:
    return manager.first_layer_id(layout_id)


def _unique_id(value: str, prefix: str) -> str:
    return f"{value}_{uuid.uuid4().hex[:8]}" if value else f"{prefix}_{uuid.uuid4().hex}"
