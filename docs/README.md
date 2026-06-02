# Camera Map View Documentation

This folder documents the current application architecture, runtime wiring, and data flow for Camera Map View.

## Documents

- [Project Architecture](project_architectural.md): current module responsibilities, UI composition, persistence, workflows, i18n, packaging, and verification.
- [Project Graph](project_graph.md): text diagrams for runtime wiring, data flow, canvas/layer flow, device topology, package import/export, and settings.

## Current Product Shape

Camera Map View is a PyQt6 desktop diagramming tool for camera and network-device map layouts. The current UI is organized around:

- A fixed left Control Panel with layout management, device inventory, topology-tree grouping, status filtering, CSV actions, and a panel-local close button.
- A central `MapCanvas` with mouse-wheel zoom, pan, background map support, grid rendering, device markers, field-of-view rendering, topology-link overlays, and drawing annotations.
- A fixed floating Drawing Tools panel anchored near the canvas.
- A right Layers panel with user-managed layers, nested object rows, visibility, lock, rename, drag/drop, delete, and front/back ordering.
- A menu bar with File, Action, View, Language, and Settings.

The app can start with zero layouts. In that state the canvas and panels are blank, layout-dependent actions are disabled, and the user must create a layout or import a `.cmvmap` package before editing.

## Persistence Summary

Local data is stored in SQLite at `assets/data/camera_manager.db`. The core tables are:

- `map_layouts`
- `cameras`
- `device_links`
- `canvas_layers`
- `drawing_shapes`
- `ping_history`

Each layout owns its devices, topology links, drawing annotations, layer stack, background map path, grid size, canvas dimensions, and background scale. Layouts can all be deleted, including legacy `default` layouts; when the last layout is deleted the app returns to the blank state.

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

Each kind has preset variants. Cameras additionally support location photos and FOV choices `80`, `180`, and `360`. Device links are directed from a lower/source device to an upstream/target device, for example `Camera -> AP -> Switch -> Router`.

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

Diagram export writes a `.cmvmap` ZIP package containing `manifest.json` plus available assets for background maps, PNG annotations, and camera location photos. Import creates a new layout instead of overwriting the current one.

## Demo Data

The repository includes `scripts/seed_demo_layout.py`, an idempotent seed script that creates or refreshes a sample multi-floor building layout with devices, topology links, layers, and annotations.
