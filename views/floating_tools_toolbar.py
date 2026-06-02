"""Floating horizontal toolbar for quick canvas tools and panel toggles."""

from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QDockWidget, QFrame, QHBoxLayout, QMenu, QToolButton, QWidget

from config.i18n import t


COMPACT_LABELS = {
    "select": "Sel",
    "draw_line": "Line",
    "draw_rectangle": "Rect",
    "draw_zone": "Zone",
    "draw_freehand": "Free",
    "add_text": "Text",
    "insert_png": "PNG",
    "choose_color": "Color",
    "delete_selected": "Del",
    "rotate_camera": "Rot",
}


@dataclass
class FloatingDockEntry:
    """Pair a translated label key with a dock widget."""

    label_key: str
    dock: QDockWidget


class FloatingToolsToolbar(QWidget):
    """Pill-shaped floating toolbar for the most common canvas tools."""

    def __init__(
        self,
        tool_actions: list[QAction],
        panel_entries: list[FloatingDockEntry],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("floatingToolsToolbar")
        self.tool_actions = tool_actions
        self.panel_entries = panel_entries
        self.action_buttons: dict[QAction, QToolButton] = {}
        self.panel_menu = QMenu(self)
        self.panel_button = self._button()
        self.panel_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.panel_button.setMenu(self.panel_menu)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(3)
        for action in self.tool_actions:
            layout.addWidget(self._action_button(action))
        layout.addWidget(self._separator())
        layout.addWidget(self.panel_button)

        self.setStyleSheet(
            """
            QWidget#floatingToolsToolbar {
                background: rgba(255, 255, 255, 235);
                border: 1px solid #94a3b8;
                border-radius: 12px;
            }
            QToolButton {
                background: transparent;
                border: 0;
                border-radius: 6px;
                color: #111827;
                font-size: 10px;
                min-height: 20px;
                min-width: 24px;
                padding: 2px 5px;
            }
            QToolButton:hover {
                background: #f3f4f6;
            }
            QToolButton:checked {
                background: #7c3aed;
                color: #ffffff;
            }
            """
        )
        self.retranslate()

    def retranslate(self) -> None:
        """Refresh translated labels for panel menu actions."""
        self.panel_button.setText("+")
        self.panel_button.setToolTip(t("widgets.panels"))
        for action, button in self.action_buttons.items():
            button.setText(self._compact_text(action))
            button.setToolTip(action.text())
        self.panel_menu.clear()
        for entry in self.panel_entries:
            action = self.panel_menu.addAction(t(entry.label_key))
            action.setCheckable(True)
            action.setChecked(entry.dock.isVisible())
            action.triggered.connect(lambda checked=False, item=entry.dock: self._set_dock_visible(item, checked))

    def _action_button(self, action: QAction) -> QToolButton:
        button = self._button()
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setText(self._compact_text(action))
        button.setToolTip(action.text())
        self.action_buttons[action] = button
        return button

    def _button(self) -> QToolButton:
        button = QToolButton(self)
        button.setAutoRaise(True)
        return button

    def _separator(self) -> QFrame:
        separator = QFrame(self)
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setFixedWidth(6)
        return separator

    def _set_dock_visible(self, dock: QDockWidget, visible: bool) -> None:
        if visible:
            dock.show()
            dock.raise_()
            return
        dock.hide()

    def _compact_text(self, action: QAction) -> str:
        key = action.objectName()
        return COMPACT_LABELS.get(key, action.text()[:4])
