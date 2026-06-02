"""Dock construction helpers for the main application window."""

from PyQt6.QtCore import QPoint, QTimer, Qt
from PyQt6.QtWidgets import QDockWidget, QHBoxLayout, QLabel, QToolButton, QWidget

from views.control_layout_panel import ControlLayoutPanel
from views.drawing_tools_panel import DrawingToolsPanel
from views.layers_panel import LayersPanel


class AppDocks:
    """Create and attach dock widgets used by MainWindow."""

    def init_camera_dock(self) -> None:
        """Create the fixed sidebar dock that hosts layout and camera controls."""
        self.dock = QDockWidget(self)
        self.dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        self.dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.control_dock_title = DockTitleBar(self.dock)
        self.dock.setTitleBarWidget(self.control_dock_title)
        self.dock.visibilityChanged.connect(lambda _visible: self.schedule_drawing_tools_position())
        self.control_panel = ControlLayoutPanel(self.dock)
        self.camera_panel = self.control_panel
        self.layouts_panel = self.control_panel
        self.dock.setWidget(self.control_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock)

    def init_drawing_tools_dock(self) -> None:
        """Create the fixed floating drawing tools widget."""
        mode_actions = [
            self.pan_action,
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
        self.drawing_tools_panel = DrawingToolsPanel(mode_actions, edit_actions, view_actions, self)
        self.drawing_tools_panel.show()
        self.position_drawing_tools_panel()

    def init_layers_dock(self) -> None:
        """Create the docked layers manager widget."""
        self.layers_dock = QDockWidget(self)
        self.layers_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.layers_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.layers_dock_title = DockTitleBar(self.layers_dock)
        self.layers_dock.setTitleBarWidget(self.layers_dock_title)
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
        """Layouts are managed by the combined control panel."""
        return

    def position_drawing_tools_panel(self) -> None:
        """Anchor drawing tools to the left-center of the map canvas."""
        if not hasattr(self, "drawing_tools_panel"):
            return
        panel = self.drawing_tools_panel
        panel.adjustSize()
        canvas_origin = self.map_canvas.mapTo(self, QPoint(0, 0))
        control_visible = hasattr(self, "dock") and self.dock.isVisible()
        x = max(14, canvas_origin.x() + 14) if control_visible else 14
        y = max(canvas_origin.y() + 12, canvas_origin.y() + (self.map_canvas.height() - panel.height()) // 2)
        panel.move(x, y)
        panel.raise_()

    def schedule_drawing_tools_position(self) -> None:
        """Position drawing tools after Qt finishes dock layout changes."""
        QTimer.singleShot(0, self.position_drawing_tools_panel)


class DockTitleBar(QWidget):
    """Compact dock title bar with a high-contrast red close button."""

    def __init__(self, dock: QDockWidget) -> None:
        super().__init__(dock)
        self.dock = dock
        self.label = QLabel(self)
        self.close_button = QToolButton(self)
        self.close_button.setText("X")
        self.close_button.setFixedSize(22, 22)
        self.close_button.setToolTip("Close")
        self.close_button.clicked.connect(dock.close)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 4, 2)
        layout.setSpacing(4)
        layout.addWidget(self.label, 1)
        layout.addWidget(self.close_button)
        self.setStyleSheet(
            """
            DockTitleBar {
                background: transparent;
            }
            QToolButton {
                background: #ef4444;
                color: #ffffff;
                border: 1px solid #b91c1c;
                border-radius: 4px;
                font-weight: 700;
            }
            QToolButton:hover {
                background: #dc2626;
            }
            QToolButton:pressed {
                background: #991b1b;
            }
            """
        )

    def set_title(self, title: str) -> None:
        self.label.setText(title)
