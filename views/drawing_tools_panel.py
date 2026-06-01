"""Dockable widget that presents map drawing and display tools."""

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QFrame, QGridLayout, QToolButton, QVBoxLayout, QWidget


class DrawingToolsPanel(QWidget):
    """Render drawing, edit, and map display actions as docked Qt widgets."""

    def __init__(
        self,
        mode_actions: list[QAction],
        edit_actions: list[QAction],
        view_actions: list[QAction],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self._button_grid(mode_actions, 2))
        layout.addWidget(self._separator())
        layout.addWidget(self._button_grid(edit_actions, 1))
        layout.addWidget(self._separator())
        layout.addWidget(self._button_grid(view_actions, 2))
        layout.addStretch(1)

    def _button_grid(self, actions: list[QAction], columns: int) -> QWidget:
        container = QWidget(self)
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)
        for index, action in enumerate(actions):
            button = QToolButton(container)
            button.setDefaultAction(action)
            button.setToolButtonStyle(button.toolButtonStyle().ToolButtonTextBesideIcon)
            button.setMinimumHeight(30)
            grid.addWidget(button, index // columns, index % columns)
        return container

    def _separator(self) -> QFrame:
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line
