# Camera Map View - Project Architecture

## Overview

Camera Map View is a PyQt6 desktop application for designing and maintaining camera and network-device placement diagrams across independent map layouts. It supports device inventory management, canvas placement, directed topology links, drawing/text/image annotations, user-managed layers, network monitoring, active ping sessions, camera location photos, dark/light themes, multilingual UI strings, static snapshot export, and portable `.cmvmap` package export/import.

The project follows an MVC-style structure:

- `models/`: dataclasses, device catalog, link model, layout model, layer model, and SQLite schema management.
- `views/`: Qt widgets, dialogs, canvas behavior, dock panels, drawing tools, icons, themes, and scene items.
- `controllers/`: application coordination and persistence-facing business logic.
- `services/`: app settings, network monitoring, active ping launcher, CSV import/export, and portable package import/export.
- `utils/`: geometry, validation, and image asset helpers.
- `config/`: runtime i18n loader plus XML UI/UX string resources.
- `assets/`: local data, button SVGs, device SVGs, map assets, and imported camera photos.
- `scripts/`: utility scripts such as the demo layout seed.

The entrypoint is `main.py`, which creates `views.app_view_window.MainWindow`.

## Runtime Composition

`MainWindow` owns the top-level window, menu bar, central canvas, dock panels, controllers, status dashboard, and ping service.

Current UI composition:

- **Menu bar:** File, Action, View, Language, and a top-level Settings action.
- **Control Panel:** fixed left dock with layout selection/CRUD, device inventory/CSV actions, link-tree grouping, status filter, placed/unplaced toggle, and a close button inside the panel header.
- **MapCanvas:** central `QGraphicsView` for background map, theme-aware canvas edit boundary, optional grid, mouse-wheel zoom, pan, rubber-band multi-select in Select mode, device items, camera FOV, topology-link overlays, drawing annotations, and drag/drop placement.
- **Drawing Tools:** fixed floating child widget anchored near the canvas. It has Draw and Shapes menus, a live color swatch, can collapse to one button, and cannot be dragged into a separate window.
- **Layers Panel:** docked two-column user layer stack with nested object rows, icon visibility, object locks, drag/drop layer reassignment, and front/back ordering.
- **Status Dashboard:** total devices plus monitored online/offline counts.
- **Settings Dialog:** application-level Network and Appearance tabs only.
- **Layout Properties Dialog:** layout name, canvas width/height, grid size, and background scale.

Dock title bars are hidden with empty title-bar widgets. Panel titles and close buttons live inside the panel headers, while `QDockWidget.windowTitle()` remains available for View menu toggle actions.

The Drawing Tools panel is self-contained and is not exposed as `View > Drawing Tools`.

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
- `cameras`: layout-scoped device records. Fields include device kind, variant, optional IP, ping preference, placement, rotation/display scale, camera FOV, status, zone, DVR origin, layer membership, location photo path, object lock, object z-index, and placed/unplaced state.
- `device_links`: layout-scoped directed upstream topology links, for example `Camera -> AP -> Switch -> Router`.
- `canvas_layers`: user-managed layer stack per layout, including name, position, visibility, and lock state.
- `drawing_shapes`: layout-scoped annotations, including geometry, color, text labels, image asset paths, layer membership, display name, object lock, and object z-index.
- `ping_history`: status history records for monitored devices.

`controllers.camera_data_manager.CameraDataManager` is the facade for device CRUD, layer operations, layout operations, directed link operations, drawing persistence, CSV import/export, and ping history. It mixes in:

- `CameraLayoutOperations`
- `CameraLayerOperations`
- `DeviceLinkOperations`
- `DrawingShapeOperations`

## Layout Workflow

Each layout is an independent workspace:

- Devices and drawings are scoped by `layout_id`.
- Device links are scoped by `layout_id`.
- Layer stacks are scoped by `layout_id`.
- Canvas size, grid size, background path, and background scale are persisted per layout.
- Switching layouts clears visible canvas items and reloads only the selected layout.
- Creating a layout opens `LayoutPropertiesDialog` so the user provides name and canvas settings up front.
- Editing a layout uses the same dialog and applies canvas settings immediately when the edited layout is active.
- Deleting a layout requires confirmation and may delete any layout, including a legacy `default` layout.
- If no layouts remain, the app enters a blank state.

Blank state behavior:

- `current_layout_id` is empty.
- The canvas is cleared and shows no default grid workspace.
- Device and layer panels are empty.
- Layout-dependent actions are disabled, including background map actions, CSV device actions, drawing tools, link tool, package export, and layer operations.
- Creating a layout or importing a package re-enables normal editing.

## Device Workflow

Device records can be created, edited, deleted, imported from CSV, and exported to CSV from the Control Panel. Supported device kinds are Camera, Server, Switch, Hub, DVR, AP, Router, Firewall, and PC. Each kind has preset variants in `models.device_catalog`.

Device properties support:

- Generic device name, kind, variant, optional IP, RTSP port, zone, DVR origin, status, ping preference, and notes.
- Camera-only FOV choices `80`, `180`, and `360`.
- Camera location image upload/removal. Images are imported into `assets/camera_photos/` as JPG with max height `1440px` and quality `75`.
- A dedicated "Manage connections" dialog for outgoing links and read-only incoming links.

The Control Panel device list:

- Defaults to the Placed tab, with Unplaced available beside it.
- Supports search by name, IP address, DVR origin, zone, device kind, and variant.
- Uses a status dropdown filter: All, Online, Offline, Unknown.
- Builds a topology tree from directed links: roots are devices without an upstream outgoing target, children are downstream devices that point into each parent, and standalone devices appear under Unlinked.
- Preserves topology context during search by keeping ancestor paths and matching subtrees visible instead of making linked devices look unlinked.
- Supports multi-select quick linking: drag one or more device rows onto an upstream device row to create `source -> target` links.
- Supports ungrouping/unlinking from the topology tree: right-click selected device rows and choose Ungroup, or drag linked rows to blank tree space.
- Uses SVG device icons and supports dragging device rows onto the canvas.
- Selecting a placed device row switches the canvas to Select mode, centers that device, and clears LayersPanel selection.

Dropping a device onto `MapCanvas` marks it placed, stores its position, assigns it to the active canvas layer, and adds a scene item. Placed devices can show configurable labels for name, zone, IP, and DVR origin.

In `Select` mode, device and drawing items can be selected individually or with rubber-band drag selection. Device items can be moved, edited, deleted from storage, unplaced from the canvas, or resized from the selected resize handle. The resize handle is drawn near the device body with a larger hit area than its visual square so it is easier to grab. Device movement is not clamped to the canvas boundary; users can move markers outside the edit area near map edges, and snapshot export crops anything outside the scene rectangle. Camera items additionally support direct rotation by dragging the selected rotation ring, location image viewing, and FOV rendering.

## Device Topology Links

Topology links use the direction `source_device -> upstream_target_device`.

Links can be edited in `DeviceConnectionsDialog` or created on the canvas with the Link Device tool. The Link Device tool only creates links; it does not remove links.

The Control Panel topology tree can also create or remove links. Dropping one or more device rows onto another device row creates upstream links to the target when validation succeeds. Dropping linked rows onto blank tree space or using the Ungroup context action removes their outgoing parent links and refreshes the panel immediately, while preserving downstream child links.

Links are hidden by default. Selecting exactly one placed device renders only the related topology:

- Downstream closure: all lower devices that directly or indirectly point into the selected device.
- Upstream path: one deterministic path from the selected device toward the highest upstream/root device.

This means selecting an endpoint camera shows its path upward, selecting an AP or switch shows its downstream branch plus one upstream path, and selecting a root/router/server-style device shows the downstream tree under it.

Link removal is intentionally tied to `Select` mode. When related links are visible, right-clicking a link opens "Remove device link". The link item uses a wide hit-test shape for easier right-clicking while keeping the visible dashed line thin.

## Camera Location Images And Active Ping

Camera context menu actions are ordered:

1. Location image
2. Ping
3. Properties

Location image opens a modal viewer when a photo exists. The viewer supports:

- Mouse-wheel zoom in/out around the cursor.
- Left-button pan through `ScrollHandDrag`.
- Zoom in, zoom out, and fit controls.

If a camera has no location photo, the controller reports it and opens Properties so the user can upload one.

Active ping opens an OS terminal session for the device IP. On Windows it launches:

```text
cmd.exe /k ping -t <ip>
```

Active ping is user-managed and does not write to `ping_history`.

## Canvas Modes And Drawing Tools

Available canvas modes are defined by `views.map_drawing_tools.DrawingMode`:

- `PAN`
- `SELECT`
- `LINE`
- `RECTANGLE`
- `ROUNDED_RECTANGLE`
- `ELLIPSE`
- `TRIANGLE`
- `ZONE`
- `FREEHAND`
- `LINK`

The app opens in `PAN` mode by default. `PAN` uses `ScrollHandDrag`, clears selection, and disables item selectable/movable/focus flags until another mode is selected.

Canvas interaction:

- Mouse wheel zooms around the cursor and clamps zoom between configured min/max factors.
- Middle-drag pans the canvas.
- Left-drag pans in `PAN`.
- Space temporarily enables hand-drag panning.
- `Esc` cancels in-progress drawing, panning, link source selection, and camera handle interactions.
- Drawing and movement are freeform by default; holding `Ctrl` temporarily snaps the current draw, move, or resize operation to the active grid size.
- The canvas edit boundary is separate from grid lines, so turning the grid off hides only grid lines while keeping the editable scene area visible in both themes.

The Drawing Tools panel contains icon-only actions for:

- Pan
- Select
- Draw group: line, freehand
- Shapes group: rectangle, rounded rectangle, ellipse/circle, triangle, polygon/zone
- Text annotation
- Image annotation
- Color
- Delete selected
- Link device
- Grid visibility
- Camera/device info visibility: name, zone, IP, DVR

Text annotations use `DrawingShape.line_thickness` as font size. Legacy text with `line_thickness <= 2` renders at the default size `18`. In Select mode, text, image, and shape annotations expose resize and rotation handles. Text rotation is stored in `DrawingShape.points` as `[x, y, rotation]`; image size and rotation are stored as `[x, y, width, height, rotation]`; rectangle-style shapes can store `[x1, y1, x2, y2, rotation]`. Legacy records without rotation still render with rotation `0`.

Background maps and inserted image annotations are imported through `utils.image_assets`. Supported image formats include PNG, JPG/JPEG, BMP, WEBP, and any format Qt can decode from the file dialog. Images taller than `1440px` are scaled down to height `1440` while preserving aspect ratio; images at or below `1440px` height keep their original pixel size. Inserted image annotations keep their original display size when they fit inside the current canvas and scale down only when needed to fit the scene.

Line, freehand, rectangle, rounded rectangle, ellipse, triangle, and zone items use stroke-only hit tests. Filled/bounding areas do not block selection of devices, text, or images inside them; users select these drawings by clicking the visible stroke/border.

## Layers

Layers behave like a simplified Photoshop layer stack:

- No legacy type-group layers are shown or maintained for new layouts.
- A layout with no user layers gets one base layer named `Layer 1`.
- New devices, drawings, text annotations, and image annotations are assigned to the currently active layer.
- Layer rows support expand/collapse, visibility, lock, rename, delete, and up/down reordering.
- Object rows support rename, lock, delete, drag/drop to another layer, selection on canvas, and up/down front/back movement within their layer.
- Camera object rename changes the real `Camera.name`.
- Drawing/image/text object rename persists `DrawingShape.display_name` without changing visible text content on the canvas.
- Object lock disables selection/movement for that object and persists through reload.
- Object z-index persists through reload and package export/import.

Runtime migration handles legacy layer IDs such as `*_cameras`, `*_drawings`, `*_images`, and `*_text` by moving their cameras/drawings into a normal user layer and removing legacy layer rows.

`MapCanvas.layers_changed` refreshes `LayersPanel` after canvas changes such as placing, unbinding, moving, rotating, resizing, adding, deleting, renaming, locking, z-order changes, or moving objects between layers.

## Undo And Redo

Undo/Redo is session-local and stores the last 10 canvas-state changes for the active layout. Each history entry is a before/after snapshot of persisted layout state: layout canvas settings, background path, cameras, drawings, device links, and layers.

UI-only state such as current selection, zoom/pan position, panel visibility, filters, and search text is not stored. History is cleared when switching, deleting, importing, or entering a blank layout to avoid restoring state into the wrong layout. Restores write the snapshot back to SQLite and reload the current layout through the normal controller flow so Control Panel and LayersPanel refresh together.

## Portable Map Packages

`services.map_package_service` exports and imports the current layout as a `.cmvmap` package. The file is a ZIP archive containing:

- `manifest.json`
- `assets/` files for the background map, image annotations, and camera location photos when those source files exist

The current package schema version is `3`. The manifest includes:

- Schema version
- Layout metadata
- Current settings snapshot
- Camera info visibility
- Devices and placed/unplaced state
- Device links
- Canvas layers
- Drawing shapes
- Asset references, including `camera_photos`

Import creates a new layout instead of overwriting the current layout. Layer IDs and object IDs are remapped where needed, and extracted assets are placed under:

```text
assets/maps/package_<layout_id>/
```

Camera location photos are extracted under:

```text
assets/maps/package_<layout_id>/camera_photos/
```

## Static Snapshot Export

`MainWindow.export_canvas_snapshot()` writes a PNG or JPEG image for reports. It calls `MapCanvas.export_snapshot(path)`, which renders the full `sceneRect()` from the `QGraphicsScene`, not the viewport or application chrome.

Snapshot export temporarily clears selection before rendering so selection outlines and transform handles do not appear. It then restores the previous selection and link overlays. Because rendering uses normal item visibility, hidden layers, hidden objects, hidden grid, and hidden background items are excluded from the exported image.

## CSV Import And Export

CSV import/export handles device inventory fields:

- `id`
- `name`
- `ip_address`
- `port`
- `camera_type`
- `device_kind`
- `variant`
- `ping_enabled`
- `zone`
- `dvr_origin`
- `notes`

CSV intentionally does not include camera location photos or topology links. Those belong to `.cmvmap` packages.

## Network Monitoring

`services.network_ping_service.PingService` runs in a `QThread` and emits device status updates for monitored devices. It supports:

- Configurable ping interval.
- Timeout seconds.
- Retry count before marking a device offline.
- ICMP ping first, then TCP fallback.

Runtime network settings are edited through Settings. Status updates are persisted in `ping_history`, reflected on visible device items, and summarized in the status dashboard. Devices with ping disabled or blank IP are not monitored and appear as Unknown.

## Themes, Icons, And Reusable UI Assets

Theme colors and stylesheets live in `views.ui_theme`.

Button icons and device icons are loaded from SVG files when present:

- `assets/icons/buttons/*.svg`
- `assets/icons/devices/*.svg`

`views.tool_icons` falls back to QPainter-rendered icons if an asset is missing. Device icons are used in the Control Panel drag pixmap and on canvas device markers.

Theme-aware UI surfaces include:

- Main window and menu bar.
- Control Panel.
- Drawing Tools floating panel and popup menus.
- Layers Panel.
- Settings dialog tabs and fields.
- Device properties and connection dialogs.
- Camera/device item rendering.

The dark theme uses black and neutral dark surfaces instead of blue-black. The light theme uses light backgrounds with dark text and recolored icons.

## Internationalization

UI/UX translation text is stored in XML resource files under `config/strings/`:

- `UIUX_VI_Strings.xml`
- `UIUX_EN_Strings.xml`
- `UIUX_JP_Strings.xml`

`config.i18n` is the runtime facade/loader for those files. It preserves the existing public API (`t`, `set_language`, `get_language`, `TRANSLATIONS`, `SUPPORTED_LANGUAGES`, and `LANGUAGE_LABELS`) so UI code can keep calling `t(key, **placeholders)` instead of hardcoding user-facing text.

The loader validates XML structure at startup:

- Expected file names exist for every supported language.
- The root `purpose` is `UIUX`.
- The root `language` matches the configured language.
- Keys are unique inside each file.
- Every supported language provides the same key set.

Translation tests verify:

- XML files use the required `UIUX_(VI|EN|JP)_Strings.xml` naming convention.
- Required keys exist for every supported language.
- Placeholder consistency is preserved.
- Visible UI text can be retranslatable at runtime.

## Demo Layout Seed

`scripts/seed_demo_layout.py` creates or refreshes an idempotent sample layout:

- Layout id: `layout_demo_multifloor`
- Layout name: multi-floor building demo
- Canvas size: `4200 x 3000`
- Grid size: `50`
- Device coverage: Camera, Server, Firewall, Router, Switch, AP, DVR/NVR, and PC.
- Topology links include many-to-one cases such as multiple cameras to AP/switch and multiple switches to core infrastructure.
- Drawing annotations include floor boundaries, server room, text labels, and backbone hints.

The script accepts `--db-path` for seeding a non-default SQLite database.

## Verification

Current project checks:

```powershell
python -m pytest tests
python -m compileall main.py models controllers views services utils config tests scripts
git diff --check
```

Expected notes:

- `config/i18n.py` should stay a small loader/facade; the UI/UX text belongs in `config/strings/UIUX_*_Strings.xml`.
- Existing Git line-ending warnings may appear for files previously touched with LF/CRLF differences.
