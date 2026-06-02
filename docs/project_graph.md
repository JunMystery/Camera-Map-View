# Camera Map View - Project Graph

## Runtime Entry Flow

```text
main.py
+-- views.app_view_window.MainWindow
    +-- MapCanvas
    +-- ControlLayoutPanel
    |   +-- layout selector/actions
    |   +-- device search/group/filter/actions
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
+-- ui_theme.py
+-- tool_icons.py

Controllers
+-- camera_data_manager.py
|   +-- camera_layout_operations.py
|   +-- camera_layer_operations.py
|   +-- drawing_shape_operations.py
+-- camera_placement_controller.py

Models
+-- camera_data_model.py
+-- drawing_shape_model.py
+-- canvas_layer_model.py
+-- map_layout_model.py
+-- camera_db_manager.py

Services
+-- camera_csv_service.py
+-- map_package_service.py
+-- network_ping_service.py

Utils
+-- geometry.py
+-- image_assets.py
+-- validators.py

Config
+-- i18n.py
```

## Main Window Wiring

```text
MainWindow.__init__()
+-- central widget
|   +-- MapCanvas
|   +-- StatusDashboard
+-- init_camera_dock()
|   +-- fixed left QDockWidget
|   +-- DockTitleBar with red close button
|   +-- ControlLayoutPanel
|   +-- camera_panel alias -> ControlLayoutPanel
|   +-- layouts_panel alias -> ControlLayoutPanel
+-- init_menus_and_toolbars()
|   +-- File menu
|   |   +-- load background map
|   |   +-- unload background map
|   |   +-- import diagram package
|   |   +-- export diagram package
|   |   +-- exit
|   +-- View menu
|   |   +-- zoom in/out/fit
|   |   +-- grid toggle
|   |   +-- reopen panel actions
|   +-- Language menu
|   +-- top-level Settings action
|   +-- init_drawing_tools_dock()
|       +-- fixed floating DrawingToolsPanel
+-- CameraDataManager
+-- init_layouts_dock()
|   +-- no-op; layouts live in ControlLayoutPanel
+-- init_layers_dock()
|   +-- right QDockWidget
|   +-- DockTitleBar with red close button
|   +-- LayersPanel
+-- CameraPlacementController
+-- PingService.start()
```

## Menu And Action Graph

```text
File
+-- open_action -> select_background_image()
+-- unload_map_action -> confirm -> unload_background_image()
+-- import_package_action -> import_map_package_file()
+-- export_package_action -> export_current_map_package()
+-- exit_action -> close() -> confirm -> stop PingService

View
+-- zoom_in_action -> MapCanvas.scale(1.25)
+-- zoom_out_action -> MapCanvas.scale(0.8)
+-- zoom_fit_action -> MapCanvas.fit_in_view()
+-- grid_action -> MapCanvas.set_grid_visible()
+-- control dock toggle
+-- drawing tools reopen
+-- layers dock toggle

Settings
+-- open_settings() -> SettingsDialog
```

There is no toolbar under the menu bar.

## Canvas Mode Graph

```text
DrawingToolsPanel
+-- pan_action -> MainWindow.set_canvas_mode(PAN)
+-- select_action -> MainWindow.set_canvas_mode(SELECT)
+-- draw_line_action -> MainWindow.set_canvas_mode(LINE)
+-- draw_rectangle_action -> MainWindow.set_canvas_mode(RECTANGLE)
+-- draw_zone_action -> MainWindow.set_canvas_mode(ZONE)
+-- draw_freehand_action -> MainWindow.set_canvas_mode(FREEHAND)
+-- add_text_action -> add/edit TextAnnotationDialog
+-- insert_png_action -> import_png_asset() -> MapCanvas.add_image_annotation()
+-- choose_color_action -> QColorDialog
+-- delete_selected_action -> MapCanvas.delete_selected_drawings()
+-- rotate_camera_action -> MapCanvas.rotate_selected_cameras(15)
+-- link_device_action -> MapCanvas.set_drawing_mode(LINK)
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

SELECT
+-- restore item interaction flags
+-- allow device/drawing select and move
+-- allow camera rotate and resize handles
+-- allow LINK mode click source device then target device

Drawing modes
+-- use cross cursor
+-- create DrawingShape previews
+-- persist final shape through drawing_created signal
```

`Esc` cancels in-progress drawing previews, panning, link source selection, and camera rotate/resize interactions.

## Canvas And Layer Graph

```text
MapCanvas
+-- background item
|   +-- QGraphicsPixmapItem
+-- grid items
|   +-- QGraphicsLineItem and border rect
+-- device items
|   +-- CameraItem
+-- temporary device link overlay items
+-- drawing items
    +-- Line
    +-- Rectangle
    +-- Polygon/Zone
    +-- Freehand path
    +-- Text
    +-- Image
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
+-- add layer -> CameraDataManager.create_layer() -> MapCanvas.set_canvas_layers()
+-- rename layer -> MapCanvas.rename_layer() + CameraDataManager.rename_layer()
+-- delete layer -> MapCanvas.delete_layer_items() + CameraDataManager.delete_layer()
+-- move layer -> CameraDataManager.move_layer() -> MapCanvas.set_canvas_layers()
+-- visibility checkbox -> MapCanvas.set_layer_visible() + CameraDataManager.set_layer_visible()
+-- select contents -> MapCanvas.select_layer_items()
+-- move selected -> MapCanvas.move_selected_items_to_layer()
+-- object row select -> MapCanvas.select_layer_object()
```

## Multi-Layout Data Flow

```text
ControlLayoutPanel.layout_selected(layout_id)
+-- MainWindow.switch_layout(layout_id)
    +-- save_current_layout_state()
    +-- apply_layout_to_canvas(layout)
    +-- CameraPlacementController.load_cameras(layout_id)
        +-- MapCanvas.clear_map_items()
        +-- CameraDataManager.get_layers(layout_id)
        +-- MapCanvas.set_canvas_layers()
        +-- CameraDataManager.get_placed_cameras(layout_id)
        +-- CameraDataManager.get_all_cameras(layout_id)
        +-- ControlLayoutPanel.set_cameras()
        +-- MapCanvas.add_camera_item()
        +-- CameraDataManager.get_drawing_shapes(layout_id)
        +-- MapCanvas.add_drawing_shape()
```

SQLite layout scoping:

```text
map_layouts.id
+-- cameras.layout_id
+-- canvas_layers.layout_id
+-- drawing_shapes.layout_id
```

## Device Workflow Graph

```text
ControlLayoutPanel
+-- Import CSV -> CameraDataManager.import_cameras_csv(layout_id)
+-- Export CSV -> CameraDataManager.export_cameras_csv(layout_id)
+-- Add device -> CameraPropertiesDialog -> CameraDataManager.add_camera(layout_id)
+-- Edit device -> CameraPropertiesDialog -> CameraDataManager.update_camera_details()
+-- Delete device -> CameraDataManager.delete_camera()
+-- Drag device row -> MapCanvas.dropEvent()
    +-- CameraPlacementController.handle_camera_dropped()
        +-- assign active layer
        +-- CameraDataManager.update_camera_position()
        +-- CameraDataManager.update_camera_layer()
        +-- MapCanvas.add_camera_item()
```

Placed device edit flow:

```text
CameraItem
+-- moved -> MapCanvas.camera_moved -> CameraPlacementController.update_camera_position()
+-- rotated -> MapCanvas.camera_rotated -> CameraDataManager.update_camera_rotation()
+-- resized -> MapCanvas.camera_resized -> CameraDataManager.update_camera_scale()
+-- deleted/unbound -> MapCanvas.camera_deleted -> CameraPlacementController.unplace_camera()
+-- edit requested -> CameraPlacementController.edit_camera()
+-- link mode click -> MapCanvas.device_link_created -> CameraPlacementController.add_device_link()
+-- selection changed -> MapCanvas.refresh_device_links()
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

Text edit flow
+-- MainWindow.add_text_annotation()
+-- TextAnnotationDialog
+-- MapCanvas.update_selected_text_annotation()
+-- drawing_updated(shape)
    +-- CameraPlacementController.update_drawing_shape()
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
        +-- add PNG annotation assets when present
        +-- write manifest.json
```

```text
Import diagram
+-- MainWindow.import_map_package_file()
    +-- services.map_package_service.import_map_package()
        +-- read manifest.json
        +-- create new layout
        +-- import/remap layers
        +-- extract assets to assets/maps/package_<layout_id>/
        +-- import devices
        +-- import device_links with remapped ids
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
        +-- Canvas tab
        |   +-- width
        |   +-- height
        |   +-- grid size
        |   +-- background scale
        +-- Appearance tab
            +-- theme dropdown
                +-- apply_theme_choice(light_theme)
                    +-- settings["light_theme"] = value
                    +-- apply_theme()
```

Saving settings:

```text
SettingsDialog.accepted
+-- MainWindow.settings.update(dialog.values())
+-- PingService.update_settings()
+-- MapCanvas.resize_canvas()
+-- MapCanvas.redraw_grid()
+-- MapCanvas.set_background_scale()
+-- save_current_layout_state()
+-- apply_theme()
```

## Ping Status Flow

```text
PingService
+-- status_updated(camera_id, is_online, latency_ms)
    +-- CameraPlacementController.handle_camera_status_updated()
        +-- CameraDataManager.update_camera_status()
        |   +-- update cameras.status/last_check
        |   +-- insert ping_history row
        +-- MapCanvas.update_camera_status()
        +-- devices with ping disabled or blank IP are excluded from monitoring
        +-- StatusDashboard.update_counts()
        +-- status bar message
```
