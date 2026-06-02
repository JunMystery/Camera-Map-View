# Camera Map View Documentation

This folder documents the current application architecture, runtime wiring, and data flow for Camera Map View.

## Documents

- [Project Architecture](project_architectural.md): detailed explanation of modules, persistence, UI composition, workflows, settings, and verification.
- [Project Graph](project_graph.md): text diagrams for runtime dependencies, MainWindow wiring, canvas/layer flow, device workflows, package import/export, and settings.

## Current Product Shape

Camera Map View is a PyQt6 desktop diagramming tool for camera map layouts. The current UI is organized around:

- A fixed left Control Panel that combines layout management and device inventory.
- A central `MapCanvas` with pan/zoom, background map support, grid rendering, device items, topology links, and drawing annotations.
- A fixed floating Drawing Tools panel anchored near the canvas.
- A right Layers panel with Photoshop-like user layers and expandable object rows.
- A menu bar with File, View, Language, and a top-level Settings action.

The app starts in `Pan` mode to prevent accidental device or drawing edits. Object interaction happens only after switching to `Select`; topology links are created with the Link Device tool.

## Persistence Summary

Local data is stored in SQLite at `assets/data/camera_manager.db`. The core tables are:

- `map_layouts`
- `cameras`
- `device_links`
- `canvas_layers`
- `drawing_shapes`
- `ping_history`

Each layout owns its devices, topology links, drawing annotations, layer stack, background map path, grid size, canvas dimensions, and background scale.

## Portable Package Summary

Diagram export writes a `.cmvmap` file. It is a ZIP archive containing:

- `manifest.json`
- `assets/` entries for the background map and image annotations when those files exist

The manifest includes device records, placed/unplaced state, topology links, layers, and drawings. Import creates a new layout instead of overwriting the current one.
