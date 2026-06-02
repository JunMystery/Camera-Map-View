# Camera Map View - Project Architecture

## Overview

Camera Map View is a PyQt6 desktop application for designing and maintaining device placement diagrams on one or more map layouts. It supports camera and network-device inventory management, placement on a canvas, topology links, drawing/text/image annotations, Photoshop-like layers, network status checks, dark/light themes, and portable `.cmvmap` package export/import.

The project follows an MVC-style structure:

- `models/`: dataclasses and SQLite schema management.
- `views/`: Qt widgets, dialogs, canvas behavior, dock panels, icons, themes, and scene items.
- `controllers/`: application coordination and persistence-facing business logic.
- `services/`: network monitoring, CSV import/export, and portable package import/export.
- `utils/`: geometry, validation, and image asset helpers.
- `config/`: runtime i18n translations and language selection.

The entrypoint is `main.py`, which creates `views.app_view_window.MainWindow`.

## Runtime Composition

`MainWindow` owns the top-level window, menu bar, central canvas, dock panels, controllers, status dashboard, and ping service.

Current UI composition:

- **Menu bar:** File, View, Language, and a top-level Settings action.
- **Control Panel:** fixed left dock that combines layout selection/CRUD and device inventory/CSV actions.
- **MapCanvas:** central `QGraphicsView` for background map, grid, pan/zoom, device items, topology-link overlays, drawing annotations, and drag/drop placement.
- **Drawing Tools:** fixed floating child widget anchored near the canvas. It can collapse to one button and cannot be dragged into a separate window.
- **Layers Panel:** docked layer stack with expandable layer groups and nested object rows.
- **Status Dashboard:** total devices plus monitored online/offline counts.
- **Settings Dialog:** horizontal tabs for network, canvas, and appearance settings.

There is no secondary toolbar under the menu bar. Drawing and annotation commands live in the floating Drawing Tools panel and menu actions remain available where needed.

## Data Model And Persistence

SQLite is managed by `models.camera_db_manager.CameraDbManager`. The default database path is:

```text
assets/data/camera_manager.db
```

When an existing database is opened, a startup backup is created at:

```text
assets/data/camera_manager.db.bak
```

Core tables:

- `map_layouts`: independent workspaces with name, background path, grid size, canvas size, and background scale.
- `cameras`: device records scoped by `layout_id`, including device kind, variant, optional IP, ping preference, placement, rotation/display data for cameras, status, zone, DVR origin, layer membership, and placed/unplaced state.
- `device_links`: directed upstream topology links scoped by `layout_id`, for example `Camera -> AP -> Switch -> Server`.
- `canvas_layers`: user-managed layer stack per layout, including name, position, visibility, and lock state.
- `drawing_shapes`: persisted annotations scoped by `layout_id`, including geometry, color, text labels, PNG asset paths, and layer membership.
- `ping_history`: status history records per camera.

`controllers.camera_data_manager.CameraDataManager` is the facade for camera CRUD, layer operations, layout operations, drawing persistence, CSV import/export, and ping history. It mixes in:

- `CameraLayoutOperations`
- `CameraLayerOperations`
- `DrawingShapeOperations`

## Layout Workflow

Each layout is an independent workspace:

- Cameras and drawings are scoped by `layout_id`.
- Layer stacks are scoped by `layout_id`.
- Canvas size, grid size, background path, and background scale are persisted per layout.
- Switching layouts clears visible canvas items and reloads only the selected layout.
- The default layout cannot be deleted.

The combined Control Panel exposes layout selection plus add, rename, and delete actions.

## Device Workflow

Device records can be created, edited, deleted, imported from CSV, and exported to CSV from the Control Panel. Supported device kinds are Camera, Server, Switch, Hub, DVR, AP, Router, and Firewall. Each kind has preset variants in the properties dialog.

The device list:

- Groups cameras by DVR origin.
- Supports search by name, IP address, DVR origin, zone, device kind, and variant.
- Switches between unplaced and placed devices.
- Groups status as Online, Offline, and Unknown. Unknown devices are those with ping disabled or no IP.
- Drags child device rows onto the canvas.

Dropping a device onto `MapCanvas` marks it placed, stores its position, assigns it to the active canvas layer, and adds a scene item. Placed devices can show configurable labels for name, zone, IP, and DVR origin.

In `Select` mode, device items can be moved, edited, or unbound from the canvas. Camera items additionally support rotation, resizing, location images, and field-of-view rendering. In `Pan` mode, device and drawing item interaction is suspended so canvas dragging cannot accidentally edit objects.

Topology links can be edited in device properties or created on the canvas with the Link Device tool. Links are hidden by default. Selecting a placed device renders the full connected chain around it.

## Canvas Modes And Drawing Tools

Available canvas modes are defined by `views.map_drawing_tools.DrawingMode`:

- `PAN`
- `SELECT`
- `LINE`
- `RECTANGLE`
- `ZONE`
- `FREEHAND`
- `LINK`

The app opens in `PAN` mode by default. `PAN` uses `ScrollHandDrag`, clears selection, and disables item selectable/movable/focus flags until another mode is selected.

The Drawing Tools panel contains icon-only actions for:

- Pan
- Select
- Draw group: line, rectangle, zone, freehand
- Text annotation
- PNG annotation
- Color
- Delete selected
- Rotate selected camera
- Link device
- Grid visibility
- Camera info visibility: name, zone, IP, DVR

Text annotations use `DrawingShape.line_thickness` as font size. Legacy text with `line_thickness <= 2` renders at the default size `18`.

## Layers

Layers now behave like a simplified Photoshop layer stack:

- No default item-type groups are shown or maintained for new layouts.
- A layout with no user layers gets one base layer named `Layer 1`.
- New devices, drawings, text annotations, and PNG annotations are assigned to the currently active layer.
- The Layers panel shows layer rows with visibility controls, names, object counts, and expandable child object rows.
- Selecting a layer makes it the active target for new objects.
- Selecting an object row selects that object on the canvas.
- Layers can be created, renamed, deleted, moved up/down, hidden/shown, collapsed/expanded, selected as a group, and used as the target for moving selected objects.

Runtime migration handles legacy layer IDs such as `*_cameras`, `*_drawings`, `*_images`, and `*_text` by moving their cameras/drawings into a normal user layer and removing legacy layer rows.

`MapCanvas.layers_changed` refreshes `LayersPanel` after canvas changes such as placing, unbinding, moving, rotating, resizing, adding, deleting, or moving objects between layers.

## Portable Map Packages

`services.map_package_service` exports and imports the current layout as a `.cmvmap` package. The file is a ZIP archive containing:

- `manifest.json`
- `assets/` files for the background map and PNG annotations when those source files exist

The manifest includes:

- Schema version
- Layout metadata
- Current settings snapshot
- Camera info visibility
- Devices and placed/unplaced state
- Device links
- Canvas layers
- Drawing shapes
- Asset references

Import creates a new layout instead of overwriting the current layout. Layer IDs and object IDs are remapped where needed, and extracted assets are placed under:

```text
assets/maps/package_<layout_id>/
```

## Network Monitoring

`services.network_ping_service.PingService` runs in a `QThread` and emits device status updates for monitored devices. It supports:

- Configurable ping interval.
- Timeout seconds.
- Retry count before marking a camera offline.
- ICMP ping first, then TCP fallback.

Runtime network settings are edited through Settings. Status updates are persisted in `ping_history`, reflected on visible device items, and summarized in the status dashboard. Devices with ping disabled or blank IP are not monitored and appear as Unknown.

## Themes And Reusable UI Assets

Theme colors and stylesheets live in `views.ui_theme`. Custom vector icons are generated by `views.tool_icons` with `QPainter`, allowing icon colors to adapt to dark and light themes.

Theme-aware UI surfaces include:

- Main window and menu bar.
- Control Panel.
- Drawing Tools floating panel and popup menus.
- Layers Panel.
- Settings dialog tabs and fields.
- Camera item rendering.

The dark theme uses black and neutral dark surfaces instead of blue-black. The light theme uses light backgrounds with dark text and recolored icons.

## Internationalization

`config.i18n` stores translation keys for Vietnamese, English, and Japanese. UI code should call `t(key, **placeholders)` instead of hardcoding user-facing text.

Translation tests verify:

- Required keys exist for every supported language.
- Placeholder consistency is preserved.
- Visible UI text can be retranslatable at runtime.

## Verification

Current project checks:

```powershell
python -m pytest tests
python -m compileall main.py models controllers views services utils config tests
git diff --check
```

Expected notes:

- `config/i18n.py` is allowed to exceed the 300-line guideline because it is a configuration dictionary.
- Existing Git line-ending warnings may appear for files previously touched with LF/CRLF differences.
