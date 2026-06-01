# Camera Map View - Project Architecture

## Overview

Camera Map View is a PyQt6 desktop application for managing camera inventories on one or more map/canvas layouts. The project follows an MVC-style structure:

- `models/`: dataclasses and SQLite schema management.
- `views/`: Qt widgets, dialogs, canvas, dock panels, and scene items.
- `controllers/`: application coordination and persistence-facing business logic.
- `services/`: network ping monitoring and CSV import/export helpers.
- `utils/`: geometry, validation, and image asset utilities.
- `config/`: runtime i18n translations and language selection.

The entrypoint is `main.py`, which creates `views.app_view_window.MainWindow`.

## Data Model And Persistence

SQLite is managed by `models.camera_db_manager.CameraDbManager`. The database lives at `assets/data/camera_manager.db` by default and creates a startup `.bak` backup when reopening an existing file.

Core tables:

- `map_layouts`: independent map/canvas layouts, including name, background path, grid size, canvas size, and background scale.
- `cameras`: camera records scoped by `layout_id`, including placement, rotation, status, zone, and DVR origin.
- `drawing_shapes`: persisted annotations scoped by `layout_id`, including geometry, labels, and inserted image paths.
- `ping_history`: status history records per camera.

`controllers.camera_data_manager.CameraDataManager` handles camera CRUD, drawing persistence, CSV import/export, ping history, and delegates layout CRUD to `controllers.camera_layout_operations.CameraLayoutOperations`.

## UI Composition

`MainWindow` composes the app using dock widgets and a central canvas:

- Control Panel: camera search, grouped DVR lists, placed/unplaced toggle, camera CRUD, CSV import/export.
- Layouts: select, add, rename, and delete independent map layouts.
- Drawing Tools: select, line, rectangle, zone, freehand, text, PNG insert, color, delete, rotate, grid/info toggles.
- Layers: grouped canvas layers with visibility, lock, active drawing layer, selection, deletion, renaming, and annotation z-order controls.
- Status Dashboard: total/online/offline summary.
- Settings: vertical-tab dialog for network, canvas, and appearance settings.

The main toolbar intentionally stays compact: map load/unload, zoom controls, and settings.

## Canvas And Layers

`views.map_view_canvas.MapCanvas` uses `BoundedGraphicsScene` so movable items stay inside the canvas bounds. Canvas behavior is split across helper mixins:

- `map_canvas_surface.py`: background image, grid, canvas resizing, background scaling.
- `map_canvas_actions.py`: layer operations, deletion, selection, grid visibility, camera metadata toggles.
- `map_canvas_drawing_events.py`: drawing-mode mouse events and shape creation.

Managed layer IDs are defined in `views.layer_state`:

- `background`
- `grid`
- `cameras`
- `drawings`
- `images`
- `text`

The selected active annotation layer receives newly added drawings/images/text. Standard z-order:

- Background: `-30`
- Grid: `-20`
- Annotation layers: `0..20`
- Cameras: `50`

## Camera Workflow

Camera records can be created, edited, deleted, imported, and exported from the Control Panel. Cameras are grouped by DVR and collapsed by default. Search filters by name, IP address, DVR origin, and zone.

Dragging a camera from the unplaced list onto the canvas marks it placed and persists its position. Camera items show status, tooltip details, configurable metadata labels, and a rotation ring when selected. Rotation can be changed by dragging the ring or using the rotate command.

## Multi-Layout Workflow

Each layout is an independent workspace:

- Cameras and drawings are scoped by `layout_id`.
- Layout settings persist canvas size, grid size, background path, and background scale.
- Switching layouts clears visible camera/drawing items and reloads only the selected layout.
- The default layout cannot be deleted.

## Network Monitoring

`services.network_ping_service.PingService` runs in a `QThread` and emits camera status updates. It supports:

- Configurable ping interval.
- Timeout seconds.
- Retry count before marking a camera offline.
- ICMP ping first, then TCP fallback.

Runtime network settings are edited through the Settings dialog.

## Internationalization

`config.i18n` stores translation keys for Vietnamese, English, and Japanese. UI code should call `t(key, **placeholders)` instead of hardcoding user-facing text. Translation tests verify language coverage and placeholder consistency.

## Verification

Current test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest tests
.\.venv\Scripts\python.exe -m compileall main.py models controllers views services utils config tests
git diff --check
```

Expected notes:

- `config/i18n.py` is allowed to exceed the 300-line file guideline because it is a configuration/dictionary file.
- Existing Git line-ending warnings may appear for files previously touched with LF/CRLF differences.
