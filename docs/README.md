# Camera Map View Documentation

This folder documents the current application architecture, runtime wiring, and data flow for Camera Map View.

## Documents

- [Project Architecture](project_architectural.md): current module responsibilities, UI composition, persistence, workflows, i18n, packaging, and verification.
- [Project Graph](project_graph.md): text diagrams for runtime wiring, data flow, canvas/layer flow, device topology, package import/export, and settings.

## Current Product Shape

Camera Map View is a PyQt6 desktop diagramming tool for camera and network-device map layouts. The current UI is organized around:

- A fixed left Control Panel with layout management, device inventory, topology-tree grouping, status filtering, CSV actions, and a panel-local close button.
- A central `MapCanvas` with mouse-wheel zoom, pan, rubber-band multi-select in Select mode, background map support, a theme-aware edit-area boundary, optional grid rendering, device markers, field-of-view rendering, topology-link overlays, and drawing annotations.
- A fixed floating Drawing Tools panel anchored near the canvas. It is visible but collapsed by default, opens to icon-only drawing controls, and includes Draw and Shapes menus plus live stroke/fill color swatches.
- A right Layers panel with a compact two-column tree, user-managed layers, one-level layer groups, nested object rows, icon visibility, lock, rename, drag/drop, delete, and front/back ordering. It is hidden by default at startup.
- A menu bar with File, Action, View, Language, and Settings. File can import/export `.cmvmap` packages and export a static snapshot image. The Action menu exposes Undo/Redo for the 10 most recent canvas-state changes in the active layout.

The app can start with zero layouts. In that state the canvas and panels are blank, layout-dependent actions are disabled, and the user must create a layout or import a `.cmvmap` package before editing.

## Persistence Summary

Local data is stored in SQLite at `assets/data/camera_manager.db`. The core tables are:

- `map_layouts`
- `cameras`
- `device_links`
- `canvas_layers`
- `drawing_shapes`
- `ping_history`

Each layout owns its devices, topology links, drawing/text/image annotations, layer stack, background map path, grid size, canvas dimensions, and background scale. Drawing and movement are freeform by default; holding `Ctrl` temporarily snaps the current draw/move/resize operation to the grid. Layouts can all be deleted, including legacy `default` layouts; when the last layout is deleted the app returns to the blank state.

Undo/Redo is in-memory for the current session. It snapshots the active layout's canvas state, including cameras, drawings, device links, layers, background map path, canvas dimensions, grid size, and background scale. It does not persist history across app restarts.

## Device Summary

Supported device kinds are:

- Camera
- Server
- Switch
- Hub
- DVR
- AP
- Router
- Firewall
- PC

Each kind has preset variants. Cameras additionally support location photos and FOV choices `80`, `180`, and `360`. Background maps, image annotations, and camera location photos use a shared import rule: images taller than `1440px` are scaled down to height `1440` while preserving aspect ratio; smaller images keep their original pixel size. Device links are directed from a lower/source device to an upstream/target device, for example `Camera -> AP -> Switch -> Router`.

## Internationalization Summary

UI/UX strings are stored as XML resources under `config/strings/`:

- `UIUX_VI_Strings.xml`
- `UIUX_EN_Strings.xml`
- `UIUX_JP_Strings.xml`

`config/i18n.py` is a small runtime loader/facade that preserves the public translation API used by the app: `t()`, `set_language()`, `get_language()`, `TRANSLATIONS`, `SUPPORTED_LANGUAGES`, and `LANGUAGE_LABELS`.

## Assets And Packages

The app uses SVG assets from:

- `assets/icons/buttons/`
- `assets/icons/devices/`

Diagram export writes a `.cmvmap` ZIP package containing `manifest.json` plus available assets for background maps, image annotations, and camera location photos. Import creates a new layout instead of overwriting the current one.

Snapshot export writes the current scene as PNG/JPEG for reports. It renders the full layout scene, not the application UI, and excludes hidden layers/objects plus selection handles.

Device markers can be moved freely outside the canvas edit boundary so users can position markers near map edges without being blocked by oversized SVG or FOV bounds. Static snapshot export still renders only the canvas `sceneRect`, so any device portion outside that region is cropped from the report image.

The Control Panel topology tree supports quick linking by dragging one or more device rows onto an upstream device row. Dragging linked rows to blank space, or using the row context menu, ungroups them by removing their outgoing upstream link while keeping their downstream child links intact. Right-click unlink directly on canvas links is disabled; link removal is handled from the Control Panel or connection dialogs.

CSV device import is layout-scoped. Existing devices with the same ID in the current layout are updated in place while preserving placement, layer, visibility, lock, z-order, badge, image, rotation, and scale state. Rows with data but no ID are imported with generated IDs, and exported Parent IP is derived from `device_links` rather than stored as an editable field.

## Demo Data

The repository includes:

- `scripts/seed_demo_layout.py`: idempotent seed script that creates or refreshes a sample multi-floor building layout with devices, topology links, layers, and annotations.
- `scripts/build_windows_exe.py`: PyInstaller helper for Windows packaging. It writes app output to `bin/CameraMapView/` and build/spec files to `build/pyinstaller/`. The script is not run automatically.
