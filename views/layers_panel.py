"""Photoshop-like layer panel for canvas layer and object management."""

from collections.abc import Callable

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QBrush, QColor, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.i18n import t
from controllers.camera_data_manager import CameraDataManager
from views.map_view_canvas import MapCanvas
from views.tool_icons import tool_icon
from views.ui_theme import DARK_ACTIVE_ROW, layers_panel_stylesheet

ROLE_TYPE = Qt.ItemDataRole.UserRole
ROLE_ID = Qt.ItemDataRole.UserRole + 1
ROLE_LAYER_ID = Qt.ItemDataRole.UserRole + 2


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
            layer_item = QTreeWidgetItem(["", state.display_name, str(state.item_count)])
            layer_item.setData(0, ROLE_TYPE, "layer")
            layer_item.setData(0, ROLE_LAYER_ID, state.layer_id)
            layer_item.setFlags(layer_item.flags() | Qt.ItemFlag.ItemIsEditable)
            layer_item.setSelected(state.active)
            if state.active:
                for column in range(3):
                    layer_item.setBackground(column, QBrush(QColor(DARK_ACTIVE_ROW)))
            self.tree.addTopLevelItem(layer_item)
            self.tree.setItemWidget(layer_item, 0, self._layer_checkbox(state.layer_id, state.visible, self._set_layer_visible))
            for object_state in self.canvas.get_layer_object_states(state.layer_id):
                child = QTreeWidgetItem(["", object_state.label, object_state.object_type])
                child.setData(0, ROLE_TYPE, "object")
                child.setData(0, ROLE_LAYER_ID, object_state.layer_id)
                child.setData(0, ROLE_ID, object_state.object_id)
                child.setData(1, ROLE_TYPE, object_state.object_type)
                layer_item.addChild(child)
            layer_item.setExpanded(True)
        self._refreshing = False

    def retranslate(self) -> None:
        """Refresh button and header text."""
        self.title_label.setText(t("dock.layers"))
        self.tree.setHeaderLabels(["", t("layer.name"), "#"])
        self.add_button.setToolTip(t("layer.add"))
        self.delete_button.setToolTip(t("layer.delete"))
        self.up_button.setToolTip(t("layer.up"))
        self.down_button.setToolTip(t("layer.down"))
        self.select_button.setToolTip(t("layer.select"))
        self.move_button.setToolTip(t("layer.move_selected"))

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        self.setObjectName("layersPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(240)
        self.setMaximumWidth(340)

        self.title_label = QLabel(self)
        self.title_label.setObjectName("sectionTitle")
        layout.addWidget(self.title_label)
        layout.addWidget(self._separator())

        self.tree = QTreeWidget(self)
        self.tree.setObjectName("layersTree")
        self.tree.setColumnCount(3)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setRootIsDecorated(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(0, 36)
        self.tree.setColumnWidth(2, 56)
        self.tree.itemSelectionChanged.connect(self._handle_selection)
        self.tree.itemClicked.connect(self._handle_click)
        self.tree.itemChanged.connect(self._handle_item_changed)
        layout.addWidget(self.tree)

        row = QHBoxLayout()
        row.setSpacing(4)
        self.add_button = self._tool_button("add_layer")
        self.delete_button = self._tool_button("delete")
        self.up_button = self._tool_button("up")
        self.down_button = self._tool_button("down")
        self.select_button = self._tool_button("select_contents")
        self.move_button = self._tool_button("move_selected")
        self.add_button.clicked.connect(self._add_layer)
        self.delete_button.clicked.connect(self._delete_selected)
        self.up_button.clicked.connect(lambda: self._move_layer(1))
        self.down_button.clicked.connect(lambda: self._move_layer(-1))
        self.select_button.clicked.connect(self._select_contents)
        self.move_button.clicked.connect(self._move_selected_objects)
        for button in [self.add_button, self.delete_button, self.up_button, self.down_button, self.select_button, self.move_button]:
            row.addWidget(button)
        layout.addLayout(row)
        self.setStyleSheet(layers_panel_stylesheet())
        self.retranslate()

    def _handle_selection(self) -> None:
        item = self.tree.currentItem()
        if item is None:
            return
        row_type = item.data(0, ROLE_TYPE)
        if row_type == "layer":
            layer_id = str(item.data(0, ROLE_LAYER_ID))
            self.canvas.set_active_layer(layer_id)
        elif row_type == "object":
            self.canvas.select_layer_object(str(item.data(1, ROLE_TYPE)), str(item.data(0, ROLE_ID)))

    def _handle_click(self, item: QTreeWidgetItem, column: int) -> None:
        if item.data(0, ROLE_TYPE) != "layer":
            return
        layer_id = str(item.data(0, ROLE_LAYER_ID))
        if column == 0:
            return

    def _handle_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._refreshing or item.data(0, ROLE_TYPE) != "layer":
            return
        layer_id = str(item.data(0, ROLE_LAYER_ID))
        if column == 1:
            self.canvas.rename_layer(layer_id, item.text(1))
            self.camera_manager.rename_layer(layer_id, item.text(1))
            self._reload_layers()

    def _add_layer(self) -> None:
        layout_id = self.layout_id_callback()
        layer = self.camera_manager.create_layer(f"{t('layer.new')} {len(self.canvas.get_layer_states()) + 1}", layout_id)
        self._reload_layers()
        self.canvas.set_active_layer(layer.id)
        self.refresh()

    def _delete_selected(self) -> None:
        item = self.tree.currentItem()
        if item is not None and item.data(0, ROLE_TYPE) == "object":
            self._delete_selected_object(item)
            return
        self._delete_selected_layer()

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

    def _delete_selected_object(self, item: QTreeWidgetItem) -> None:
        object_type = str(item.data(1, ROLE_TYPE))
        object_id = str(item.data(0, ROLE_ID))
        if not self.canvas.select_layer_object(object_type, object_id):
            return
        count = self.canvas.delete_selected_drawings()
        self.refresh()
        if count:
            self._show_status(t("status.drawing_deleted", count=count), 5000)

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
        if item.data(0, ROLE_TYPE) == "object":
            item = item.parent()
        return str(item.data(0, ROLE_LAYER_ID)) if item is not None else ""

    def _reload_layers(self) -> None:
        layout_id = self.layout_id_callback()
        self.canvas.set_canvas_layers(self.camera_manager.get_layers(layout_id), layout_id)
        self.refresh()

    def _show_status(self, message: str, timeout_ms: int) -> None:
        if self.status_callback is not None:
            self.status_callback(message, timeout_ms)

    def _layer_checkbox(self, layer_id: str, checked: bool, callback: Callable[[str, bool], None]) -> QCheckBox:
        checkbox = QCheckBox(self.tree)
        checkbox.setChecked(checked)
        checkbox.setToolTip(layer_id)
        checkbox.stateChanged.connect(lambda state, item=layer_id: callback(item, state == Qt.CheckState.Checked.value))
        return checkbox

    def _set_layer_visible(self, layer_id: str, visible: bool) -> None:
        if self._refreshing:
            return
        self.canvas.set_layer_visible(layer_id, visible)
        self.camera_manager.set_layer_visible(layer_id, visible)
        self.refresh()

    def _set_layer_locked(self, layer_id: str, locked: bool) -> None:
        if self._refreshing:
            return
        self.canvas.set_layer_locked(layer_id, locked)
        self.camera_manager.set_layer_locked(layer_id, locked)
        self.refresh()

    def _tool_button(self, icon_name: str) -> QToolButton:
        button = QToolButton(self)
        button.setAutoRaise(False)
        button.setIcon(self._icon(icon_name))
        button.setIconSize(QSize(22, 22))
        button.setFixedSize(32, 30)
        return button

    def _icon(self, icon_name: str) -> QIcon:
        return tool_icon(icon_name)

    def _separator(self) -> QFrame:
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        return line
