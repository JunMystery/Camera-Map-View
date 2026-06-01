# Camera Map View - Project Graph

## Runtime Entry Flow

```text
main.py
└── views.app_view_window.MainWindow
    ├── MapCanvas
    ├── CameraPanel
    ├── LayoutsPanel
    ├── DrawingToolsPanel
    ├── LayersPanel
    ├── StatusDashboard
    ├── SettingsDialog
    ├── CameraDataManager
    ├── CameraPlacementController
    └── PingService
```

## MVC Dependency Graph

```text
Views
├── app_view_window.py
│   ├── app_docks.py
│   ├── app_camera_actions.py
│   ├── app_layout_actions.py
│   └── app_settings_actions.py
├── map_view_canvas.py
│   ├── map_canvas_surface.py
│   ├── map_canvas_actions.py
│   ├── map_canvas_drawing_events.py
│   ├── bounded_graphics_scene.py
│   ├── camera_view_item.py
│   └── map_drawing_tools.py
├── camera_view_panel.py
├── camera_view_dialog.py
├── layouts_panel.py
├── layers_panel.py
├── drawing_tools_panel.py
├── settings_dialog.py
└── status_dashboard.py

Controllers
├── camera_data_manager.py
├── camera_layout_operations.py
└── camera_placement_controller.py

Models
├── camera_data_model.py
├── drawing_shape_model.py
├── map_layout_model.py
└── camera_db_manager.py

Services
├── camera_csv_service.py
└── network_ping_service.py

Utils
├── geometry.py
├── image_assets.py
└── validators.py

Config
└── i18n.py
```

## Main Window Wiring

```text
MainWindow
├── init_camera_dock()
│   └── CameraPanel
├── init_layouts_dock()
│   └── LayoutsPanel
├── init_drawing_tools_dock()
│   └── DrawingToolsPanel
├── init_layers_dock()
│   └── LayersPanel
├── init_menus_and_toolbars()
│   └── Main toolbar: map load/unload, zoom, settings
├── CameraPlacementController
│   ├── CameraPanel signals
│   ├── MapCanvas signals
│   └── CameraDataManager persistence
└── PingService
    └── status_updated -> CameraPlacementController
```

## Canvas Layer Graph

```text
MapCanvas
├── background layer
│   └── QGraphicsPixmapItem
├── grid layer
│   └── QGraphicsLineItem / border rect
├── cameras layer
│   └── CameraItem
├── drawings layer
│   └── Line / Rectangle / Polygon / Freehand
├── images layer
│   └── PNG QGraphicsPixmapItem
└── text layer
    └── QGraphicsTextItem
```

Layer control flow:

```text
LayersPanel
└── MapCanvas API
    ├── get_layer_states()
    ├── set_active_layer()
    ├── set_layer_visible()
    ├── set_layer_locked()
    ├── select_layer_items()
    ├── delete_layer_items()
    ├── rename_layer()
    └── move_layer()
```

## Multi-Layout Data Flow

```text
LayoutsPanel
└── MainWindow / AppLayoutActions
    ├── save_current_layout_state()
    ├── switch_layout(layout_id)
    ├── apply_layout_to_canvas(layout)
    └── CameraPlacementController.load_cameras(layout_id)
        ├── MapCanvas.clear_map_items()
        ├── CameraDataManager.get_placed_cameras(layout_id)
        ├── CameraDataManager.get_all_cameras(layout_id)
        └── CameraDataManager.get_drawing_shapes(layout_id)
```

SQLite layout scoping:

```text
map_layouts.id
├── cameras.layout_id
└── drawing_shapes.layout_id
```

## Camera Workflow Graph

```text
CameraPanel
├── Import CSV -> CameraDataManager.import_cameras_csv(layout_id)
├── Export CSV -> CameraDataManager.export_cameras_csv(layout_id)
├── Add -> CameraPropertiesDialog -> CameraDataManager.add_camera(layout_id)
├── Edit -> CameraPropertiesDialog -> CameraDataManager.update_camera_details()
├── Delete -> CameraDataManager.delete_camera()
└── Drag camera -> MapCanvas.dropEvent()
    └── CameraPlacementController.handle_camera_dropped()
        ├── update_camera_position()
        └── MapCanvas.add_camera_item()
```

## Settings Flow

```text
SettingsDialog
└── MainWindow / AppSettingsActions
    ├── PingService.update_settings()
    ├── MapCanvas.resize_canvas()
    ├── MapCanvas.redraw_grid()
    ├── MapCanvas.set_background_scale()
    ├── save_current_layout_state()
    └── apply_theme()
```
