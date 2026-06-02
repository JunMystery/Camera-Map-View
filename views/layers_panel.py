"""Photoshop-like layer panel for canvas layer and object management."""

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.i18n import t
from controllers.camera_data_manager import CameraDataManager
from views.map_view_canvas import MapCanvas


class LayersPanel(QWidget):
    """Manage persistent canvas layers and nested layer objects."""

    def __init__(
        self,
        canvas: MapCanvas,
        camera_manager: CameraDataManager,
        layout_id_callback: Callable[[], str],
        status_callback: Callable[[str, int], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.canvas = canvas
        self.camera_manager = camera_manager
        self.layout_id_callback = layout_id_callback
        self.status_callback = status_callback
        self._refreshing = False
        self._build_ui()
        self.refresh()

    def refresh(self) -> None:
        """Rebuild layer and object rows from canvas state."""
        self._refreshing = True
        self.tree.clear()
        for state in reversed(self.canvas.get_layer_states()):
            layer_item = QTreeWidgetItem([self._eye(state.visible), self._lock(state.locked), state.display_name, str(state.item_count)])
            layer_item.setData(0, Qt.ItemDataRole.UserRole, "layer")
            layer_item.setData(1, Qt.ItemDataRole.UserRole, state.layer_id)
            layer_item.setFlags(layer_item.flags() | Qt.ItemFlag.ItemIsEditable)
            layer_item.setSelected(state.active)
            self.tree.addTopLevelItem(layer_item)
            for object_state in self.canvas.get_layer_object_states(state.layer_id):
                child = QTreeWidgetItem(["", "", object_state.label, object_state.object_type])
                child.setData(0, Qt.ItemDataRole.UserRole, "object")
                child.setData(1, Qt.ItemDataRole.UserRole, object_state.layer_id)
                child.setData(2, Qt.ItemDataRole.UserRole, object_state.object_id)
                child.setData(3, Qt.ItemDataRole.UserRole, object_state.object_type)
                layer_item.addChild(child)
            layer_item.setExpanded(True)
        self._refreshing = False

    def retranslate(self) -> None:
        """Refresh button and header text."""
        self.tree.setHeaderLabels([t("layer.visible"), t("layer.locked"), t("layer.name"), t("layer.count")])
        self.add_button.setText(t("layer.add"))
        self.delete_button.setText(t("layer.delete"))
        self.up_button.setText(t("layer.up"))
        self.down_button.setText(t("layer.down"))
        self.select_button.setText(t("layer.select"))
        self.move_button.setText(t("layer.move_selected"))

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(4)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.itemSelectionChanged.connect(self._handle_selection)
        self.tree.itemClicked.connect(self._handle_click)
        self.tree.itemChanged.connect(self._handle_item_changed)
        layout.addWidget(self.tree)

        row = QHBoxLayout()
        self.add_button = QPushButton(self)
        self.delete_button = QPushButton(self)
        self.up_button = QPushButton(self)
        self.down_button = QPushButton(self)
        self.select_button = QPushButton(self)
        self.move_button = QPushButton(self)
        self.add_button.clicked.connect(self._add_layer)
        self.delete_button.clicked.connect(self._delete_selected_layer)
        self.up_button.clicked.connect(lambda: self._move_layer(1))
        self.down_button.clicked.connect(lambda: self._move_layer(-1))
        self.select_button.clicked.connect(self._select_contents)
        self.move_button.clicked.connect(self._move_selected_objects)
        for button in [self.add_button, self.delete_button, self.up_button, self.down_button, self.select_button, self.move_button]:
            row.addWidget(button)
        layout.addLayout(row)
        self.retranslate()

    def _handle_selection(self) -> None:
        item = self.tree.currentItem()
        if item is None:
            return
        row_type = item.data(0, Qt.ItemDataRole.UserRole)
        if row_type == "layer":
            layer_id = str(item.data(1, Qt.ItemDataRole.UserRole))
            self.canvas.set_active_layer(layer_id)
        elif row_type == "object":
            self.canvas.select_layer_object(str(item.data(3, Qt.ItemDataRole.UserRole)), str(item.data(2, Qt.ItemDataRole.UserRole)))

    def _handle_click(self, item: QTreeWidgetItem, column: int) -> None:
        if item.data(0, Qt.ItemDataRole.UserRole) != "layer":
            return
        layer_id = str(item.data(1, Qt.ItemDataRole.UserRole))
        if column == 0:
            visible = not self.canvas.layer_visibility.get(layer_id, True)
            self.canvas.set_layer_visible(layer_id, visible)
            self.camera_manager.set_layer_visible(layer_id, visible)
            self.refresh()
        elif column == 1:
            locked = not self.canvas.layer_locked.get(layer_id, False)
            self.canvas.set_layer_locked(layer_id, locked)
            self.camera_manager.set_layer_locked(layer_id, locked)
            self.refresh()

    def _handle_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._refreshing or item.data(0, Qt.ItemDataRole.UserRole) != "layer":
            return
        layer_id = str(item.data(1, Qt.ItemDataRole.UserRole))
        if column == 2:
            self.canvas.rename_layer(layer_id, item.text(2))
            self.camera_manager.rename_layer(layer_id, item.text(2))
            self._reload_layers()

    def _add_layer(self) -> None:
        layout_id = self.layout_id_callback()
        layer = self.camera_manager.create_layer(f"{t('layer.new')} {len(self.canvas.get_layer_states()) + 1}", layout_id)
        self._reload_layers()
        self.canvas.set_active_layer(layer.id)
        self.refresh()

    def _delete_selected_layer(self) -> None:
        layer_id = self._selected_layer_id()
        if not layer_id:
            return
        if self.canvas.get_layer_object_states(layer_id):
            result = QMessageBox.question(self, t("layer.delete"), t("layer.delete_confirm"))
            if result != QMessageBox.StandardButton.Yes:
                return
        self.canvas.delete_layer_items(layer_id)
        self.camera_manager.delete_layer(layer_id)
        self._reload_layers()
        self._show_status(t("status.layer_deleted", count=1), 5000)

    def _move_layer(self, direction: int) -> None:
        layer_id = self._selected_layer_id()
        if layer_id and self.camera_manager.move_layer(layer_id, direction, self.layout_id_callback()):
            self._reload_layers()

    def _select_contents(self) -> None:
        layer_id = self._selected_layer_id()
        if not layer_id:
            return
        count = self.canvas.select_layer_items(layer_id)
        self._show_status(t("status.layer_selected", count=count), 3000)

    def _move_selected_objects(self) -> None:
        layer_id = self._selected_layer_id()
        if not layer_id:
            return
        count = self.canvas.move_selected_items_to_layer(layer_id)
        self.refresh()
        self._show_status(t("status.layer_moved", count=count), 3000)

    def _selected_layer_id(self) -> str:
        item = self.tree.currentItem()
        if item is None:
            return ""
        if item.data(0, Qt.ItemDataRole.UserRole) == "object":
            item = item.parent()
        return str(item.data(1, Qt.ItemDataRole.UserRole)) if item is not None else ""

    def _reload_layers(self) -> None:
        layout_id = self.layout_id_callback()
        self.canvas.set_canvas_layers(self.camera_manager.get_layers(layout_id), layout_id)
        self.refresh()

    def _show_status(self, message: str, timeout_ms: int) -> None:
        if self.status_callback is not None:
            self.status_callback(message, timeout_ms)

    def _eye(self, visible: bool) -> str:
        return "Y" if visible else "-"

    def _lock(self, locked: bool) -> str:
        return "L" if locked else ""
