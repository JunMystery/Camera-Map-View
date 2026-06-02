# Camera Map View

Camera Map View is a PyQt6 desktop application for designing camera placement diagrams on map or floor-plan backgrounds. It manages layouts, camera inventory, drawing annotations, layers, network status checks, and portable diagram export/import packages.

## Prerequisites

- Python 3.11 or newer. The current workspace has been verified with Python 3.14.
- Windows is the primary development environment for this repository.
- A desktop session capable of running Qt/PyQt6 applications.
- Optional: a virtual environment for isolated Python dependencies.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

If you prefer using an installed Python directly:

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Environment Variables

No environment variables are required. The application stores local runtime data under `assets/data/` and imported assets under `assets/`.

The repository includes `.env.example` only to document that no secret or runtime `.env` configuration is expected.

## Common Workflows

- **Load or unload a background map:** use `File > Load background map` or `File > Unload background map`. Unload asks for confirmation.
- **Create layouts:** use the layout selector and icon buttons in the left Control Panel.
- **Manage cameras:** use the camera list in the Control Panel. Cameras are grouped by DVR, searchable by name/IP/DVR/zone, and can be dragged onto the canvas.
- **Navigate the canvas:** the app starts in `Pan` mode so dragging the canvas does not accidentally move items.
- **Edit items:** switch to `Select` mode before moving, rotating, resizing, editing, or deleting cameras and drawings.
- **Draw annotations:** use the floating Drawing Tools panel for line, rectangle, zone, freehand, text, PNG image, color, delete, rotate, grid, and camera info toggles.
- **Manage layers:** use the Layers panel like a Photoshop-style layer stack. New cameras, drawings, text, and images go into the currently active layer.
- **Export/import a diagram:** use `File > Export diagram...` or `File > Import diagram...`. Export writes a single `.cmvmap` ZIP package containing `manifest.json` and related assets.
- **Change theme:** open `Settings` on the menu bar and choose Dark or Light from the theme dropdown. The theme applies immediately.

## Project Structure

```text
Camera-Map-View/
+-- main.py                         # PyQt application entrypoint
+-- config/
|   +-- i18n.py                      # Translation dictionary and language helpers
+-- controllers/
|   +-- camera_data_manager.py       # Camera, drawing, layout, and layer persistence facade
|   +-- camera_layout_operations.py  # Layout CRUD operations
|   +-- camera_layer_operations.py   # Photoshop-like layer persistence
|   +-- camera_placement_controller.py
|   +-- drawing_shape_operations.py
+-- models/
|   +-- camera_db_manager.py         # SQLite schema and connection manager
|   +-- camera_data_model.py         # Camera dataclass
|   +-- canvas_layer_model.py        # Canvas layer dataclass
|   +-- drawing_shape_model.py       # Drawing annotation dataclass
|   +-- map_layout_model.py          # Layout dataclass
+-- services/
|   +-- camera_csv_service.py        # Camera CSV import/export
|   +-- map_package_service.py       # .cmvmap package import/export
|   +-- network_ping_service.py      # Background camera status checks
+-- utils/
|   +-- geometry.py
|   +-- image_assets.py
|   +-- validators.py
+-- views/
|   +-- app_view_window.py           # MainWindow composition and menu actions
|   +-- app_docks.py                 # Control, drawing tools, and layers panel setup
|   +-- control_layout_panel.py      # Combined layout and camera panel
|   +-- drawing_tools_panel.py       # Fixed floating drawing toolbar
|   +-- layers_panel.py              # Layer stack and object tree
|   +-- map_view_canvas.py           # Canvas view, pan/zoom/drop behavior
|   +-- map_canvas_*.py              # Canvas surface, actions, and drawing event helpers
|   +-- camera_view_item.py          # Camera graphics item
|   +-- settings_dialog.py           # Settings tabs and immediate theme selection
|   +-- ui_theme.py                  # Reusable theme tokens and stylesheets
|   +-- tool_icons.py                # Reusable painted vector icons
+-- docs/
|   +-- README.md
|   +-- project_architectural.md
|   +-- project_graph.md
+-- tests/
```

## Architecture And Stack

- **UI:** PyQt6 widgets, `QGraphicsView`, `QGraphicsScene`, dock widgets, custom title bars, and custom painted icons.
- **Persistence:** SQLite via `models.camera_db_manager.CameraDbManager`.
- **Pattern:** MVC-style organization with view widgets, controller coordination, model dataclasses, and service modules.
- **Networking:** `PingService` runs in a Qt thread and checks camera status with ICMP/TCP fallback.
- **Images:** Pillow/OpenCV dependencies support image handling; PNG annotations are copied into reusable local assets.
- **Packaging:** `.cmvmap` files are ZIP archives with a JSON manifest and packaged background/image assets.
- **Internationalization:** `config.i18n.t()` provides Vietnamese, English, and Japanese UI text.

## Data Storage

The default database path is:

```text
assets/data/camera_manager.db
```

When an existing database is opened, `CameraDbManager` creates:

```text
assets/data/camera_manager.db.bak
```

Local database files are ignored by Git.

## Verification

Run the focused project checks before handing off changes:

```powershell
python -m pytest tests
python -m compileall main.py models controllers views services utils config tests
git diff --check
```

Expected notes:

- `pytest` may show a cache warning if `.pytest_cache` already exists.
- `git diff --check` may report Git line-ending conversion warnings on Windows while still exiting successfully.

## Documentation

Detailed documentation lives in:

- [docs/README.md](docs/README.md)
- [docs/project_architectural.md](docs/project_architectural.md)
- [docs/project_graph.md](docs/project_graph.md)
