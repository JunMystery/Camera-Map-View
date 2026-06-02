"""Floating icon panel for map drawing and display tools."""

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QFrame, QMenu, QToolButton, QVBoxLayout, QWidget

from config.i18n import t
from views.tool_icons import tool_icon
from views.ui_theme import DARK_BORDER, drawing_tools_stylesheet


class DrawingToolsPanel(QWidget):
    """Render drawing, edit, and map display actions as a fixed floating toolbar."""

    def __init__(
        self,
        mode_actions: list[QAction],
        edit_actions: list[QAction],
        view_actions: list[QAction],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("drawingToolsPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowFlags(Qt.WindowType.Widget)
        self.mode_actions = mode_actions
        self.edit_actions = edit_actions
        self.view_actions = view_actions
        self._buttons: list[QToolButton] = []
        self._collapsed = False

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(7, 7, 7, 7)
        self.root_layout.setSpacing(6)

        self.collapse_button = self._base_button("collapse")
        self.collapse_button.clicked.connect(self.toggle_collapsed)
        self.root_layout.addWidget(self.collapse_button)

        self.content = QWidget(self)
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(6)
        content_layout.addWidget(self._action_button(mode_actions[0]))
        content_layout.addWidget(self._menu_button("Draw", mode_actions[1:], "draw_line"))
        content_layout.addWidget(self._separator())
        for action in edit_actions:
            content_layout.addWidget(self._action_button(action))
        content_layout.addWidget(self._separator())
        content_layout.addWidget(self._action_button(view_actions[0], "grid"))
        content_layout.addWidget(self._menu_button("Info", view_actions[1:], "info"))
        self.root_layout.addWidget(self.content)

        self.setStyleSheet(drawing_tools_stylesheet())
        self.retranslate()

    def retranslate(self) -> None:
        """Refresh panel tooltips after language changes."""
        self.collapse_button.setToolTip(t("dock.drawing_tools"))
        for action in [*self.mode_actions, *self.edit_actions, *self.view_actions]:
            action.setIcon(tool_icon(action.objectName() or "grid"))
        for button in self._buttons:
            action = button.defaultAction()
            if action is not None:
                button.setToolTip(action.text())

    def toggle_collapsed(self) -> None:
        """Collapse or expand the floating tool panel."""
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        """Apply the collapsed state."""
        self._collapsed = collapsed
        self.content.setVisible(not collapsed)
        self.collapse_button.setIcon(tool_icon("expand" if collapsed else "collapse"))
        self.adjustSize()

    def _action_button(self, action: QAction, icon_key: str | None = None) -> QToolButton:
        button = self._base_button(icon_key or action.objectName())
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setIcon(tool_icon(icon_key or action.objectName()))
        button.setToolTip(action.text())
        action.changed.connect(lambda item=action, target=button: self._sync_action_button(item, target))
        return button

    def _menu_button(self, label: str, actions: list[QAction], icon_key: str) -> QToolButton:
        button = self._base_button(icon_key)
        button.setText(label)
        button.setCheckable(True)
        button.setToolTip(label)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(button)
        for action in actions:
            action.setIcon(tool_icon(action.objectName()))
            menu.addAction(action)
            action.changed.connect(lambda target=button, items=actions: self._sync_menu_button(target, items))
        button.setMenu(menu)
        self._sync_menu_button(button, actions)
        return button

    def _base_button(self, icon_key: str) -> QToolButton:
        button = QToolButton(self)
        button.setAutoRaise(False)
        button.setIcon(tool_icon(icon_key))
        button.setIconSize(QSize(24, 24))
        button.setFixedSize(40, 38)
        self._buttons.append(button)
        return button

    def _separator(self) -> QFrame:
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setStyleSheet(f"color: {DARK_BORDER};")
        return line

    def _sync_action_button(self, action: QAction, button: QToolButton) -> None:
        button.setIcon(tool_icon(action.objectName() or "grid"))
        button.setToolTip(action.text())

    def _sync_menu_button(self, button: QToolButton, actions: list[QAction]) -> None:
        checked = next((action for action in actions if action.isChecked()), None)
        button.setChecked(checked is not None)
        if checked is not None:
            button.setIcon(tool_icon(checked.objectName()))
            button.setToolTip(checked.text())
