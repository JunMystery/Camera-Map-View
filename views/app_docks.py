"""Dock construction helpers for the main application window."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDockWidget

from views.camera_view_panel import CameraPanel
from views.drawing_tools_panel import DrawingToolsPanel
from views.floating_tools_toolbar import FloatingDockEntry, FloatingToolsToolbar
from views.layers_panel import LayersPanel
from views.layouts_panel import LayoutsPanel


class AppDocks:
    """Create and attach dock widgets used by MainWindow."""

    def init_camera_dock(self) -> None:
        """Create the sidebar dock that hosts the camera panel."""
        self.dock = QDockWidget(self)
        self.dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.camera_panel = CameraPanel(self.dock)
        self.dock.setWidget(self.camera_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock)

    def init_drawing_tools_dock(self) -> None:
        """Create the docked drawing tools widget."""
        self.tools_dock = QDockWidget(self)
        self.tools_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        mode_actions = [
            self.select_action,
            self.draw_line_action,
            self.draw_rectangle_action,
            self.draw_zone_action,
            self.draw_freehand_action,
        ]
        edit_actions = [
            self.add_text_action,
            self.insert_png_action,
            self.choose_color_action,
            self.delete_selected_action,
            self.rotate_camera_action,
        ]
        view_actions = [self.grid_action, *self.info_actions.values()]
        self.drawing_tools_panel = DrawingToolsPanel(mode_actions, edit_actions, view_actions, self.tools_dock)
        self.tools_dock.setWidget(self.drawing_tools_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.tools_dock)

    def init_layers_dock(self) -> None:
        """Create the docked layers manager widget."""
        self.layers_dock = QDockWidget(self)
        self.layers_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.layers_panel = LayersPanel(
            self.map_canvas,
            self.camera_manager,
            lambda: self.current_layout_id,
            self.status_bar.showMessage,
            self.layers_dock,
        )
        self.layers_dock.setWidget(self.layers_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.layers_dock)

    def init_layouts_dock(self) -> None:
        """Create the docked layouts manager widget."""
        self.layouts_dock = QDockWidget(self)
        self.layouts_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.layouts_panel = LayoutsPanel(self.layouts_dock)
        self.layouts_dock.setWidget(self.layouts_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.layouts_dock)

    def init_floating_tools_toolbar(self) -> None:
        """Create the floating quick tools toolbar and hide dock panels."""
        tool_actions = [
            self.select_action,
            self.draw_line_action,
            self.draw_rectangle_action,
            self.draw_zone_action,
            self.draw_freehand_action,
            self.add_text_action,
            self.insert_png_action,
            self.choose_color_action,
            self.delete_selected_action,
            self.rotate_camera_action,
        ]
        panel_entries = [
            FloatingDockEntry("dock.control_panel", self.dock),
            FloatingDockEntry("dock.layouts", self.layouts_dock),
            FloatingDockEntry("dock.drawing_tools", self.tools_dock),
            FloatingDockEntry("dock.layers", self.layers_dock),
        ]
        self.floating_tools_toolbar = FloatingToolsToolbar(tool_actions, panel_entries, self)
        self.floating_tools_toolbar.show()
        self.position_floating_tools_toolbar()
        self.hide_dock_widgets()

    def position_floating_tools_toolbar(self) -> None:
        """Anchor the floating toolbar to the bottom center of the main window."""
        if not hasattr(self, "floating_tools_toolbar"):
            return
        toolbar = self.floating_tools_toolbar
        toolbar.adjustSize()
        x = max(12, (self.width() - toolbar.width()) // 2)
        y = max(12, self.height() - toolbar.height() - 56)
        toolbar.move(x, y)
        toolbar.raise_()

    def hide_dock_widgets(self) -> None:
        """Hide dock widgets until users open them from the floating toolbar."""
        for dock in [self.dock, self.layouts_dock, self.tools_dock, self.layers_dock]:
            dock.hide()
