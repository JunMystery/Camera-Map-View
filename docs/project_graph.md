# Camera Map View - Project Graph

## Runtime Entry Flow

```text
main.py
+-- views.app_view_window.MainWindow
    +-- MapCanvas
    +-- ControlLayoutPanel
    |   +-- layout selector/actions
    |   +-- status filter
    |   +-- topology-tree device list
    |   +-- placed/unplaced toggle
    |   +-- CSV actions
    +-- DrawingToolsPanel
    +-- LayersPanel
    +-- StatusDashboard
    +-- SettingsDialog
    +-- CameraDataManager
    +-- CameraPlacementController
    +-- PingService
```

`ControlLayoutPanel` is assigned to both `MainWindow.camera_panel` and `MainWindow.layouts_panel` for compatibility with existing controller wiring.

## Module Dependency Graph

```text
Views
+-- app_view_window.py
|   +-- app_docks.py
|   +-- app_camera_actions.py
|   +-- app_layout_actions.py
|   +-- app_package_actions.py
|   +-- app_settings_actions.py
|   +-- control_layout_panel.py
|   +-- drawing_tools_panel.py
|   +-- layers_panel.py
|   +-- map_view_canvas.py
|   +-- settings_dialog.py
|   +-- status_dashboard.py
+-- map_view_canvas.py
|   +-- map_canvas_surface.py
|   +-- map_canvas_actions.py
|   +-- map_canvas_drawing_events.py
|   +-- bounded_graphics_scene.py
|   +-- camera_view_item.py
|   +-- map_drawing_tools.py
+-- camera_view_dialog.py
|   +-- device_connections_dialog.py
+-- camera_location_image_dialog.py
+-- layout_properties_dialog.py
+-- confirm_dialog.py
+-- layer_state.py
+-- ui_theme.py
+-- tool_icons.py

Controllers
+-- camera_data_manager.py
|   +-- camera_layout_operations.py
|   +-- camera_layer_operations.py
|   +-- device_link_operations.py
|   +-- drawing_shape_operations.py
+-- camera_placement_controller.py

Models
+-- camera_data_model.py
+-- drawing_shape_model.py
+-- canvas_layer_model.py
+-- map_layout_model.py
+-- device_link_model.py
+-- device_catalog.py
+-- camera_db_manager.py

Services
+-- app_settings_service.py
+-- active_ping_service.py
+-- camera_csv_service.py
+-- map_package_service.py
+-- network_ping_service.py

Utils
+-- app_paths.py
+-- geometry.py
+-- image_assets.py
+-- validators.py

Config
+-- i18n.py
+-- strings/
    +-- UIUX_VI_Strings.xml
    +-- UIUX_EN_Strings.xml
    +-- UIUX_JP_Strings.xml

Assets
+-- icons/
|   +-- buttons/*.svg
|   +-- devices/*.svg
+-- data/
+-- maps/

Scripts
+-- seed_demo_layout.py
+-- build_windows_exe.py
```

`config/i18n.py` loads XML resources at startup and exposes the stable runtime API used by views and controllers: `t()`, `set_language()`, `get_language()`, `TRANSLATIONS`, `SUPPORTED_LANGUAGES`, and `LANGUAGE_LABELS`.

## Main Window Wiring

```text
MainWindow.__init__()
+-- central widget
|   +-- MapCanvas
|   +-- StatusDashboard
+-- init_camera_dock()
|   +-- fixed left QDockWidget
|   +-- empty dock title bar
|   +-- ControlLayoutPanel
|   |   +-- internal title row
|   |   +-- close button -> dock.close()
|   +-- camera_panel alias -> ControlLayoutPanel
|   +-- layouts_panel alias -> ControlLayoutPanel
+-- init_menus_and_toolbars()
|   +-- File menu
|   +-- Action menu
|   +-- View menu
|   +-- Language menu
|   +-- top-level Settings action
|   +-- init_drawing_tools_dock()
|       +-- fixed floating DrawingToolsPanel
|       +-- visible collapsed by default
+-- CameraDataManager
+-- CanvasHistoryManager
+-- load first layout or show blank canvas
+-- init_layouts_dock()
|   +-- no-op; layouts live in ControlLayoutPanel
+-- init_layers_dock()
|   +-- right QDockWidget
|   +-- empty dock title bar
|   +-- hidden by default
|   +-- LayersPanel
|       +-- internal title row
|       +-- close button -> layers_dock.close()
+-- CameraPlacementController
+-- PingService.start()
+-- enter_blank_layout_state() when no layout exists
```

## Menu And Action Graph

```text
File
+-- open_action -> select_background_image()
+-- unload_map_action -> confirm -> unload_background_image()
+-- import_package_action -> import_map_package_file()
+-- export_package_action -> export_current_map_package()
+-- export_snapshot_action -> export_canvas_snapshot()
+-- exit_action -> close() -> confirm -> stop PingService

Action
+-- undo_action -> CanvasHistoryManager.undo()
+-- redo_action -> CanvasHistoryManager.redo()

View
+-- zoom_in_action -> MapCanvas.scale(1.25)
+-- zoom_out_action -> MapCanvas.scale(0.8)
+-- zoom_fit_action -> MapCanvas.fit_in_view()
+-- grid_action -> MapCanvas.set_grid_visible()
+-- toggle_background_map_action -> MapCanvas.set_background_map_visible()
+-- control dock toggle
+-- layers dock toggle

Language
+-- vi/en/jp actions -> set_language() -> retranslate()

Settings
+-- open_settings() -> SettingsDialog(Network, Appearance)
```

When `current_layout_id` is empty, layout-dependent actions are disabled. Import package, create layout, settings, language, and basic panel visibility remain available.

There is no toolbar under the menu bar.

## Layout Flow

```text
App startup
+-- CameraDataManager.get_layouts()
    +-- has layouts -> switch/load first sorted layout
    +-- no layouts -> MapCanvas.show_blank_canvas()
                   -> ControlLayoutPanel.set_cameras([], set(), [])
                   -> LayersPanel disabled
                   -> layout-dependent actions disabled
```

```text
Add layout
+-- ControlLayoutPanel.layout_add_requested
+-- MainWindow.add_layout()
    +-- LayoutPropertiesDialog(create)
    +-- CameraDataManager.create_layout()
    +-- CameraDataManager.update_layout(canvas settings)
    +-- switch_layout(new_layout_id)
```

```text
Edit layout
+-- ControlLayoutPanel.layout_rename_requested
+-- MainWindow.rename_layout(layout_id)
    +-- LayoutPropertiesDialog(edit)
    +-- CameraDataManager.update_layout()
    +-- apply_layout_to_canvas() when editing current layout
    +-- save_current_layout_state()
```

```text
Delete layout
+-- ControlLayoutPanel.layout_delete_requested
+-- confirm_dialog.confirm()
+-- CameraDataManager.delete_layout(layout_id)
    +-- remaining layouts -> switch first sorted layout
    +-- no layouts -> enter_blank_layout_state()
```

SQLite layout scoping:

```text
map_layouts.id
+-- cameras.layout_id
+-- device_links.layout_id
+-- canvas_layers.layout_id
+-- drawing_shapes.layout_id
```

## Device Workflow Graph

```text
ControlLayoutPanel
+-- Add device -> CameraPropertiesDialog
|   +-- Manage connections -> DeviceConnectionsDialog
|   +-- CameraDataManager.add_camera(layout_id)
|   +-- CameraDataManager.replace_device_links()
+-- Edit device -> CameraPropertiesDialog
|   +-- CameraDataManager.update_camera_details()
|   +-- CameraDataManager.replace_device_links()
+-- Delete device -> CameraDataManager.delete_camera_in_layout()
+-- Import CSV -> CameraDataManager.import_cameras_csv(layout_id)
+-- Export CSV -> CameraDataManager.export_cameras_csv(layout_id)
+-- Drag selected device rows onto device row
|   +-- preflight self/duplicate/cycle/descendant
|   +-- CameraPlacementController.add_device_link(source, target)
|   +-- refresh MapCanvas links and ControlLayoutPanel tree
+-- Drag selected linked rows to blank tree space or context Ungroup
|   +-- CameraPlacementController.unlink_devices_from_group(source_ids)
|   +-- delete outgoing parent links for selected sources
|   +-- preserve downstream child links
|   +-- refresh MapCanvas links and ControlLayoutPanel tree
+-- Context Change parent device
|   +-- DeviceParentPickerDialog(all layout devices, including unplaced)
|   +-- search by name/IP/kind/variant/Parent IP
|   +-- exclude self and descendants
|   +-- CameraPlacementController.change_device_parent(source, target)
|       +-- remove existing outgoing parent links
|       +-- create source -> target when validation succeeds
|       +-- refresh MapCanvas links and ControlLayoutPanel tree
+-- Drag device row -> MapCanvas.dropEvent()
    +-- CameraPlacementController.handle_camera_dropped()
        +-- assign active layer
        +-- CameraDataManager.update_camera_position_in_layout()
        +-- CameraDataManager.update_camera_layer()
        +-- MapCanvas.add_camera_item()
```

Placed device context flow:

```text
CameraItem.contextMenuEvent()
+-- Location image -> CameraPlacementController.show_location_image()
|   +-- CameraLocationImageDialog when image exists
|   +-- edit properties when image is missing
+-- Ping -> CameraPlacementController.ping_camera()
|   +-- active_ping_service.open_active_ping()
+-- Properties -> CameraPlacementController.edit_camera()
```

Placed device edit flow:

```text
CameraItem
+-- moved -> MapCanvas.camera_moved -> CameraPlacementController.update_camera_position()
+-- rotated by handle -> MapCanvas.camera_rotated -> CameraDataManager.update_camera_rotation_in_layout()
+-- resized by near-body handle -> MapCanvas.camera_resized -> CameraDataManager.update_camera_scale_in_layout()
+-- deleted/unbound -> MapCanvas.camera_deleted -> CameraPlacementController.unplace_camera()
+-- link mode click -> MapCanvas.device_link_created -> CameraPlacementController.add_device_link()
+-- selection changed -> MapCanvas.refresh_device_links()
+-- topology focus from ControlLayoutPanel -> MapCanvas.highlight_device_topology()
```

## Control Panel Grouping Flow

```text
ControlLayoutPanel.set_cameras(cameras, placed_ids, device_links)
+-- filter by placed/unplaced tab
+-- filter by search text
+-- filter by status dropdown
+-- build incoming/outgoing maps from source -> target links
+-- keep ancestor paths and matching subtrees for search context
+-- when search is active, auto-expand matched ancestor paths and scroll to first match
+-- when search is empty, preserve only user-expanded groups and keep new groups collapsed
+-- roots = linked devices without outgoing upstream target
+-- add root device tree items
+-- recursively add downstream children
+-- unlinked devices -> Unlinked group
```

Status bucket:

```text
ping disabled or blank IP -> Unknown
ping enabled and status True -> Online
ping enabled and status False -> Offline
```

## Canvas Mode Graph

```text
DrawingToolsPanel
+-- pan_action -> MainWindow.set_canvas_mode(PAN)
+-- move_background_action -> MainWindow.set_canvas_mode(MOVE_BACKGROUND)
+-- select_action -> MainWindow.set_canvas_mode(SELECT)
+-- draw_line_action -> MainWindow.set_canvas_mode(LINE)
+-- draw_freehand_action -> MainWindow.set_canvas_mode(FREEHAND)
+-- Shapes menu
|   +-- draw_rectangle_action -> MainWindow.set_canvas_mode(RECTANGLE)
|   +-- draw_rounded_rectangle_action -> MainWindow.set_canvas_mode(ROUNDED_RECTANGLE)
|   +-- draw_ellipse_action -> MainWindow.set_canvas_mode(ELLIPSE)
|   +-- draw_triangle_action -> MainWindow.set_canvas_mode(TRIANGLE)
|   +-- draw_zone_action -> MainWindow.set_canvas_mode(ZONE)
+-- add_text_action -> add/edit TextAnnotationDialog
+-- insert_png_action -> import_image_asset() -> MapCanvas.add_image_annotation()
+-- choose_color_action -> QColorDialog
+-- choose_fill_color_action -> QColorDialog or No fill
+-- delete_selected_action -> MapCanvas.delete_selected_drawings()
+-- link_device_action -> MapCanvas.set_drawing_mode(LINK)
+-- toggle_background_map_action -> MapCanvas.set_background_map_visible()
+-- grid_action -> MapCanvas.set_grid_visible()
+-- info actions -> MapCanvas.set_camera_info_visibility()
```

Mode behavior:

```text
PAN
+-- QGraphicsView.ScrollHandDrag
+-- clear scene selection
+-- suspend item selectable/movable/focus flags
+-- left drag pans canvas

MOVE_BACKGROUND
+-- enabled only when a background map exists
+-- drag background item visually without moving devices/drawings
+-- persist background_x/background_y on release
+-- Esc rolls back active background drag

SELECT
+-- restore item interaction flags
+-- allow device/drawing select and move
+-- allow camera rotate and resize handles
+-- allow device resize handle for every device kind
+-- allow device markers to move outside sceneRect for edge placement
+-- no direct right-click unlink on visible DeviceLinkItem

LINK
+-- click source device
+-- click target/upstream device
+-- emit device_link_created(source, target)
+-- right-click link does not unlink

Drawing modes
+-- use cross cursor
+-- create DrawingShape previews
+-- persist final shape through drawing_created signal
+-- freeform coordinates by default
+-- hold Ctrl to snap draw/move/resize to grid
```

Canvas zoom and pan:

```text
wheelEvent()
+-- read angleDelta().y()
+-- clamp zoom to min/max
+-- scale under mouse anchor
+-- accept event

mouse/middle/space pan
+-- middle drag pans any mode
+-- left drag pans in PAN
+-- Space temporarily enables hand-drag panning
```

`Esc` cancels in-progress drawing previews, panning, link source selection, and camera rotate/resize interactions.

## Topology Link Visibility Flow

```text
MapCanvas.refresh_device_links()
+-- remove previous overlay items
+-- selected/focused device ids come from canvas selection or Control Panel focus
+-- related = downstream_links(device_id) + upstream_path_links(device_id)
+-- create DeviceLinkItem(link_role="downstream") for lower subtree links
+-- create DeviceLinkItem(link_role="upstream") for parent/root path links
+-- no selected/focused device -> no topology link overlays
```

```text
downstream_links(target_id)
+-- start with selected device as visited target
+-- include every link where target is visited
+-- add each source to visited
+-- repeat until no new downstream source is found
```

```text
upstream_path_links(source_id)
+-- enumerate outgoing source -> target paths
+-- choose deterministic longest path
+-- render that one path upward
```

`DeviceLinkItem.shape()` uses a wide stroke for hit testing, while paint/pen keeps the visible dashed line thin. Canvas context-menu unlink is disabled; unlink actions live in the Control Panel and connection dialogs.

Topology highlight flow:

```text
ControlLayoutPanel current device row
+-- CameraPlacementController.focus_camera_from_panel()
    +-- MapCanvas.highlight_device_topology(device_id, center=True)
        +-- selected device role = selected
        +-- upstream/downstream related devices role = related
        +-- selected device outline blinks red/yellow from canvas timer
        +-- related device outlines blink cyan/blue from canvas timer
        +-- highlighted cameras use expanded FOV radius/alpha
        +-- siblings outside selected path/subtree remain unhighlighted
```

```text
ControlLayoutPanel multi-select placed device rows
+-- CameraPlacementController.focus_cameras_from_panel(device_ids)
    +-- MapCanvas.highlight_device_topologies(device_ids, center=False)
        +-- selected device roles = selected
        +-- union upstream/downstream related devices role = related
        +-- upstream link role wins when the same link appears in multiple paths
```

## Canvas And Layer Graph

```text
MapCanvas
+-- background item
|   +-- QGraphicsPixmapItem
+-- canvas bounds item
|   +-- QGraphicsRectItem independent from grid visibility
+-- grid items
|   +-- QGraphicsLineItem
+-- device items
|   +-- CameraItem
+-- temporary device link overlay items
|   +-- DeviceLinkItem
+-- drawing items
    +-- SelectableLineItem
    +-- TransformableRectItem
    +-- TransformableRoundedRectItem
    +-- TransformableEllipseItem
    +-- TransformablePolygonItem
    +-- SelectablePathItem
    +-- TransformableTextItem
    +-- TransformableImageItem
```

Layer state flow:

```text
CameraDataManager.get_layers(layout_id)
+-- CameraLayerOperations.ensure_default_layers()
    +-- migrate legacy type-group layers when present
    +-- create Layer 1 when the layout has no layers
    +-- assign objects without layer_id to first layer

MapCanvas.set_canvas_layers(layers, layout_id)
+-- stores layer names, visibility, locked state, z-order
+-- chooses active layer
+-- applies layer z-values
+-- emits layers_changed

LayersPanel.refresh()
+-- reads MapCanvas.get_layer_states()
+-- reads MapCanvas.get_layer_object_states(layer_id)
+-- builds layer rows and child object rows
+-- preserves expanded/collapsed layer groups
```

Layer action flow:

```text
LayersPanel
+-- close button -> layers_dock.close()
+-- add layer -> CameraDataManager.create_layer() -> MapCanvas.set_canvas_layers()
+-- rename layer -> MapCanvas.rename_layer() + CameraDataManager.rename_layer()
+-- delete layer/object -> canvas delete + manager delete
+-- move layer up/down -> CameraDataManager.move_layer() -> MapCanvas.set_canvas_layers()
+-- move object up/down -> MapCanvas.move_layer_object() -> object_z_changed
+-- visibility icon button -> MapCanvas.set_layer_visible() + CameraDataManager.set_layer_visible()
+-- layer lock -> MapCanvas.set_layer_locked() + CameraDataManager.set_layer_locked()
+-- object visibility icon -> MapCanvas.set_layer_object_visible() -> object_visibility_changed
+-- object lock -> MapCanvas.set_layer_object_locked() -> object_locked_changed
+-- object row rename -> MapCanvas.rename_layer_object() -> object_renamed
+-- object drag/drop -> MapCanvas.move_layer_objects_to_layer() -> object_layer_changed
+-- object reorder drag/drop -> MapCanvas.move_layer_objects_to_index() -> object_z_changed
+-- object row select -> MapCanvas.select_layer_object()
```

Layer z-value rule:

```text
background -> -30
grid -> -20
user layer item -> layer_position * 1000 + object_z_index
device links -> 45
camera handles/selection visuals -> item paint overlay
```

Layer grouping rule:

```text
group position
+-- layer position
    +-- object z_index
```

Groups are one level only. A group can contain layers; a group cannot contain another group.

## Multi-Layout Data Flow

```text
ControlLayoutPanel.layout_selected(layout_id)
+-- MainWindow.switch_layout(layout_id)
    +-- invalid or empty id -> enter_blank_layout_state()
    +-- save_current_layout_state()
    +-- apply_layout_to_canvas(layout)
    +-- CameraPlacementController.load_cameras(layout_id)
        +-- MapCanvas.clear_map_items()
        +-- CameraDataManager.get_layers(layout_id)
        +-- MapCanvas.set_canvas_layers()
        +-- CameraDataManager.get_placed_cameras(layout_id)
        +-- CameraDataManager.get_all_cameras(layout_id)
        +-- CameraDataManager.get_device_links(layout_id)
        +-- ControlLayoutPanel.set_cameras()
        +-- MapCanvas.add_camera_item()
        +-- CameraDataManager.get_drawing_shapes(layout_id)
        +-- MapCanvas.add_drawing_shape()
        +-- MapCanvas.set_device_links()
```

## Drawing Persistence Flow

```text
MapCanvas drawing event
+-- DrawingTool.shape_from_points() or freehand_shape()
+-- shape.layer_id = active_layer_id
+-- MapCanvas.add_drawing_shape(shape, emit_created=True)
    +-- drawing_created(shape)
        +-- CameraPlacementController.add_drawing_shape()
            +-- CameraDataManager.add_drawing_shape(layout_id)
```

Text edit flow:

```text
MainWindow.add_text_annotation()
+-- TextAnnotationDialog
+-- existing text selected -> MapCanvas.update_selected_text_annotation()
|   +-- drawing_updated(shape)
|       +-- CameraPlacementController.update_drawing_shape()
+-- no selected text -> MapCanvas.add_text_annotation()
    +-- drawing_created(shape)
```

Image annotation flow:

```text
MainWindow.insert_png_annotation()
+-- QFileDialog
+-- import_image_asset()
    +-- copy/downscale supported image into assets/maps/
    +-- max height 1440px, preserve ratio
    +-- fit display size inside scene only when larger than canvas
    +-- MapCanvas.add_image_annotation()
    +-- drawing_created(shape)
```

Text/Image transform flow:

```text
SELECT mode
+-- selected TransformableTextItem
|   +-- resize handle -> update font size in line_thickness
|   +-- rotate handle -> persist points [x, y, rotation]
+-- selected TransformableImageItem
    +-- resize handle -> persist points [x, y, width, height, rotation]
    +-- rotate handle -> persist points [x, y, width, height, rotation]
+-- Esc -> rollback active transform
    +-- release -> drawing_updated(shape)
```

Shape transform flow:

```text
SELECT mode
+-- selected TransformableRectItem / Rounded / Ellipse / Polygon
    +-- side handles resize one axis
    +-- corner handles resize two axes
    +-- rotate handle stores rotation or baked scene points
+-- selected TransformableImageItem
    +-- side handles resize one axis
    +-- corner handles keep image aspect ratio
    +-- rotation uses scene-space center to avoid visual flicker
+-- hold Ctrl during transform -> snap handle target to grid
```

## CSV Import/Export Flow

```text
Import CSV
+-- AppCameraActions.import_cameras_csv()
    +-- services.camera_csv_service.import_cameras_from_csv()
        +-- normalize BOM/whitespace/header case
        +-- skip blank rows
        +-- generate dev_<uuid8> for rows with data and blank id
        +-- ignore parent_ip and legacy dvr_origin on import
    +-- CameraDataManager.import_cameras_csv(layout_id)
        +-- existing id in current layout -> update metadata in place
        +-- new id -> insert device
        +-- preserve placement, scale, rotation, layer, z, visibility, lock, image, badge
        +-- reject duplicate IP conflicts with a different device in the layout
    +-- refresh ControlLayoutPanel, canvas items, ping list, dashboard
```

```text
Export CSV
+-- CameraDataManager.export_cameras_csv(layout_id)
    +-- parent_ip = derived from direct outgoing source -> target links
    +-- no dvr_origin column in exported header
```

## Package Export/Import Flow

```text
Export diagram
+-- MainWindow.export_current_map_package()
    +-- save_current_layout_state()
    +-- collect layout
    +-- collect settings
    +-- collect camera_info_visibility
    +-- collect devices with is_placed
    +-- collect device_links
    +-- collect layers
    +-- collect drawing_shapes
    +-- services.map_package_service.export_map_package()
        +-- create .cmvmap ZIP
        +-- add background asset when present
        +-- add image annotation assets when present
        +-- add camera location photos when present
        +-- write manifest.json
```

## Snapshot Export Flow

```text
Export snapshot
+-- MainWindow.export_canvas_snapshot()
    +-- QFileDialog save PNG/JPEG
    +-- MapCanvas.export_snapshot(path)
        +-- save selected items
        +-- clear selection and handles
        +-- QGraphicsScene.render(full sceneRect)
        +-- restore selection/link overlays
        +-- hidden layers/objects stay hidden in output
        +-- device portions outside sceneRect are cropped from output
```

```text
Import diagram
+-- MainWindow.import_map_package_file()
    +-- services.map_package_service.import_map_package()
        +-- read manifest.json
        +-- validate schema version 1/2/3/4/5/6
        +-- create new layout
        +-- import/remap layers
        +-- extract assets to assets/maps/package_<layout_id>/
        +-- import/remap devices
        +-- import/remap camera location photos
        +-- import/remap device_links
        +-- import drawings
    +-- refresh_layouts_panel()
    +-- switch_layout(new_layout_id)
```

## Settings Flow

```text
Settings action
+-- MainWindow.open_settings()
    +-- SettingsDialog(settings, theme_changed=apply_theme_choice)
        +-- Network tab
        |   +-- ping interval
        |   +-- timeout
        |   +-- retries
        +-- Appearance tab
            +-- theme dropdown
                +-- apply_theme_choice(light_theme)
                    +-- settings["light_theme"] = value
                    +-- apply_theme()
```

Saving app settings:

```text
SettingsDialog.accepted
+-- MainWindow.settings.update(dialog.values())
+-- save_app_settings()
+-- PingService.update_settings()
+-- apply_theme()
```

Layout canvas settings moved out of Settings:

```text
LayoutPropertiesDialog
+-- name
+-- canvas width
+-- canvas height
+-- grid size
+-- background scale
+-- background X/Y offset
+-- CameraDataManager.update_layout()
+-- MainWindow.apply_layout_to_canvas() when current
```

When a layout has a background image, background scale and background X/Y drive the pixmap size and position. Canvas width/height remain independent and the scene expands only if the offset background exceeds the configured canvas. When a layout has no background image, canvas width/height and grid size drive the default grid scene.

## Ping Status Flow

```text
PingService
+-- monitors cameras/devices with ping_enabled and valid IP in current layout
+-- status_updated(camera_id, is_online, latency_ms)
    +-- CameraPlacementController.handle_camera_status_updated()
        +-- CameraDataManager.update_camera_status()
        |   +-- update cameras.status/last_check
        |   +-- insert ping_history row
        +-- MapCanvas.update_camera_status()
        +-- ControlLayoutPanel refresh
        +-- StatusDashboard.update_counts()
        +-- status bar message
```

Active ping is separate:

```text
CameraItem context Ping
+-- CameraPlacementController.ping_camera()
    +-- active_ping_service.open_active_ping(ip)
        +-- Windows: cmd.exe /k ping -t <ip>
        +-- non-Windows: ping <ip>
```

Active ping does not write `ping_history`.
