"""Dockable widget for grouped canvas layer management."""

from collections.abc import Callable

from PyQt6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QWidget,
)

from config.i18n import t
from views.layer_state import ANNOTATION_LAYERS, CAMERAS_LAYER, LayerState
from views.map_view_canvas import MapCanvas


class LayersPanel(QWidget):
    """Manage visibility, locks, selection, deletion, names, and ordering."""

    def __init__(
        self,
        canvas: MapCanvas,
        status_callback: Callable[[str, int], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.canvas = canvas
        self.status_callback = status_callback
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(8, 8, 8, 8)
        self.grid.setHorizontalSpacing(6)
        self.grid.setVerticalSpacing(5)
        self.refresh()

    def refresh(self) -> None:
        """Rebuild rows from current canvas layer state."""
        self._clear_grid()
        headers = ["layer.active", "layer.visible", "layer.locked", "layer.name", "layer.select", "layer.delete", "layer.up", "layer.down"]
        for column, key in enumerate(headers):
            self.grid.addWidget(QPushButton(t(key), self), 0, column)
        for row, state in enumerate(self.canvas.get_layer_states(), start=1):
            self._add_row(row, state)

    def _add_row(self, row: int, state: LayerState) -> None:
        active = QRadioButton(self)
        active.setChecked(state.active)
        active.setEnabled(state.layer_id in ANNOTATION_LAYERS)
        active.toggled.connect(lambda checked, item=state.layer_id: self._set_active(item) if checked else None)
        self.grid.addWidget(active, row, 0)

        visible = QCheckBox(self)
        visible.setChecked(state.visible)
        visible.toggled.connect(lambda checked, item=state.layer_id: self._toggle_visible(item, checked))
        self.grid.addWidget(visible, row, 1)

        locked = QCheckBox(self)
        locked.setChecked(state.locked)
        locked.toggled.connect(lambda checked, item=state.layer_id: self._toggle_locked(item, checked))
        self.grid.addWidget(locked, row, 2)

        name = QLineEdit(state.display_name, self)
        name.editingFinished.connect(lambda field=name, item=state.layer_id: self.canvas.rename_layer(item, field.text()))
        self.grid.addWidget(name, row, 3)

        self.grid.addWidget(self._button("layer.select", lambda item=state.layer_id: self._select(item)), row, 4)
        self.grid.addWidget(self._button("layer.delete", lambda item=state.layer_id: self._delete(item)), row, 5)
        self.grid.addWidget(self._button("layer.up", lambda item=state.layer_id: self._move(item, -1), state.layer_id in ANNOTATION_LAYERS), row, 6)
        self.grid.addWidget(self._button("layer.down", lambda item=state.layer_id: self._move(item, 1), state.layer_id in ANNOTATION_LAYERS), row, 7)

    def _button(self, key: str, callback: Callable[[], None], enabled: bool = True) -> QPushButton:
        button = QPushButton(t(key), self)
        button.setEnabled(enabled)
        button.clicked.connect(callback)
        return button

    def _toggle_visible(self, layer_id: str, visible: bool) -> None:
        self.canvas.set_layer_visible(layer_id, visible)

    def _set_active(self, layer_id: str) -> None:
        if self.canvas.set_active_layer(layer_id):
            self.refresh()

    def _toggle_locked(self, layer_id: str, locked: bool) -> None:
        self.canvas.set_layer_locked(layer_id, locked)

    def _select(self, layer_id: str) -> None:
        count = self.canvas.select_layer_items(layer_id)
        self._show_status(t("status.layer_selected", count=count), 3000)

    def _delete(self, layer_id: str) -> None:
        count = self.canvas.delete_layer_items(layer_id)
        key = "status.layer_camera_delete_blocked" if layer_id == CAMERAS_LAYER else "status.layer_deleted"
        self._show_status(t(key, count=count), 5000)
        self.refresh()

    def _move(self, layer_id: str, direction: int) -> None:
        if self.canvas.move_layer(layer_id, direction):
            self.refresh()

    def _show_status(self, message: str, timeout_ms: int) -> None:
        if self.status_callback is not None:
            self.status_callback(message, timeout_ms)

    def _clear_grid(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
