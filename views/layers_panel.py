"""Photoshop-like layer panel for canvas layer and object management."""

from collections.abc import Callable

from PyQt6.QtCore import QEvent, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.i18n import t
from controllers.camera_data_manager import CameraDataManager
from views import confirm_dialog
from views.map_view_canvas import MapCanvas
from views.tool_icons import tool_icon
from views.ui_theme import DARK_ACTIVE_ROW, LIGHT_ACTIVE_ROW, LIGHT_TEXT, TEXT_ON_DARK, layers_panel_stylesheet

ROLE_TYPE = Qt.ItemDataRole.UserRole
ROLE_ID = Qt.ItemDataRole.UserRole + 1
ROLE_LAYER_ID = Qt.ItemDataRole.UserRole + 2
ROLE_OBJECT_TYPE = Qt.ItemDataRole.UserRole + 3
ROLE_Z_INDEX = Qt.ItemDataRole.UserRole + 4
ROLE_GROUP_ID = Qt.ItemDataRole.UserRole + 5


class LayersTreeWidget(QTreeWidget):
    """Tree widget that allows moving layer objects between layers."""

    object_dropped = pyqtSignal(str, str, str)
    object_reordered = pyqtSignal(str, str, str, int)
    layer_grouped = pyqtSignal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._drag_in_progress = False
        self.installEventFilter(self)
        self.viewport().installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        if getattr(self, "_drag_in_progress", False) and event.type() == QEvent.Type.Wheel:
            if self._handle_drag_wheel_event(event):
                return True
        return super().eventFilter(watched, event)

    def dropEvent(self, event) -> None:
        source = self.currentItem()
        if source is None or source.data(0, ROLE_TYPE) not in {"object", "layer"}:
            super().dropEvent(event)
            return
        target = self.itemAt(event.position().toPoint()) if hasattr(event, "position") else self.itemAt(event.pos())
        if target is None:
            event.ignore()
            return
        source_type = source.data(0, ROLE_TYPE)
        target_type = target.data(0, ROLE_TYPE)
        if source_type == "layer":
            group_id = str(target.data(0, ROLE_LAYER_ID) or "") if target_type == "group" else ""
            if not group_id and target_type == "layer" and target.parent() is not None and target.parent().data(0, ROLE_TYPE) == "group":
                group_id = str(target.parent().data(0, ROLE_LAYER_ID) or "")
            self.layer_grouped.emit(str(source.data(0, ROLE_LAYER_ID)), group_id)
            self._accept_copy_drop(event)
            return
        if target_type == "object":
            parent = target.parent()
            if parent is None:
                event.ignore()
                return
            layer_id = str(parent.data(0, ROLE_LAYER_ID))
            if source.parent() is not parent:
                self.object_dropped.emit(
                    str(source.data(0, ROLE_OBJECT_TYPE)),
                    str(source.data(0, ROLE_ID)),
                    layer_id,
                )
                self._accept_copy_drop(event)
                return
            target_index = self._target_z_index_after_visual_drop(parent, source, target)
            if target_index is None:
                event.ignore()
                return
            self.object_reordered.emit(
                str(source.data(0, ROLE_OBJECT_TYPE)),
                str(source.data(0, ROLE_ID)),
                layer_id,
                target_index,
            )
            self._accept_copy_drop(event)
            return
        if target_type == "layer":
            self.object_dropped.emit(
                str(source.data(0, ROLE_OBJECT_TYPE)),
                str(source.data(0, ROLE_ID)),
                str(target.data(0, ROLE_LAYER_ID)),
            )
            self._accept_copy_drop(event)
            return
        if target_type == "group":
            event.ignore()
            return
        event.ignore()

    def startDrag(self, supported_actions: Qt.DropAction) -> None:
        self._drag_in_progress = True
        try:
            super().startDrag(Qt.DropAction.CopyAction)
        finally:
            self._drag_in_progress = False

    def dragMoveEvent(self, event) -> None:
        self._auto_scroll_for_drag(event)
        super().dragMoveEvent(event)

    def wheelEvent(self, event) -> None:
        if self._handle_drag_wheel_event(event):
            return
        super().wheelEvent(event)

    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.CopyAction

    def _accept_copy_drop(self, event) -> None:
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()

    def _auto_scroll_for_drag(self, event) -> None:
        point = event.position().toPoint() if hasattr(event, "position") else event.pos()
        margin = max(12, self.autoScrollMargin())
        viewport_height = self.viewport().height()
        if point.y() < margin:
            self._scroll_by_steps(-1)
        elif point.y() > viewport_height - margin:
            self._scroll_by_steps(1)

    def _handle_drag_wheel_event(self, event) -> bool:
        if not getattr(self, "_drag_in_progress", False):
            return False
        delta = event.angleDelta().y()
        if not delta:
            return False
        self._scroll_by_delta(delta)
        event.accept()
        return True

    def _scroll_by_delta(self, delta: int) -> None:
        steps = max(1, abs(delta) // 120)
        self._scroll_by_steps(-steps if delta > 0 else steps)

    def _scroll_by_steps(self, steps: int) -> None:
        scroll_bar = self.verticalScrollBar()
        step_size = max(1, scroll_bar.singleStep())
        scroll_bar.setValue(scroll_bar.value() + steps * step_size)

    def _drop_after_target(self) -> bool:
        if hasattr(self, "dropIndicatorPosition"):
            return self.dropIndicatorPosition() == QAbstractItemView.DropIndicatorPosition.BelowItem
        return False

    def _target_z_index_after_visual_drop(
        self,
        parent: QTreeWidgetItem,
        source: QTreeWidgetItem,
        target: QTreeWidgetItem,
    ) -> int | None:
        visual_items = [parent.child(index) for index in range(parent.childCount())]
        source_visual_index = parent.indexOfChild(source)
        target_visual_index = parent.indexOfChild(target)
        if source_visual_index < 0 or target_visual_index < 0 or source is target:
            return None
        visual_items.remove(source)
        if target not in visual_items:
            return None
        target_visual_index = visual_items.index(target)
        insert_visual_index = target_visual_index + (1 if self._drop_after_target() else 0)
        visual_items.insert(insert_visual_index, source)
        final_visual_index = visual_items.index(source)
        return len(visual_items) - 1 - final_visual_index


class LayersPanel(QWidget):
    """Manage persistent canvas layers and nested layer objects."""

    close_requested = pyqtSignal()

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
        self._renaming = False
        self._expanded_layer_ids: set[str] = set()
        self._expanded_group_ids: set[str] = set()
        self._seen_layer_ids: set[str] = set()
        self._layer_toggle_buttons: dict[str, QToolButton] = {}
        self._icon_color = TEXT_ON_DARK
        self._active_row_color = DARK_ACTIVE_ROW
        self._build_ui()
        self.canvas.layers_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        """Rebuild layer and object rows from canvas state."""
        if self._seen_layer_ids:
            self._expanded_layer_ids = self._current_expanded_layer_ids()
        self._refreshing = True
        self.tree.clear()
        self._layer_toggle_buttons.clear()
        visible_layer_ids: set[str] = set()
        states = list(reversed(self.canvas.get_layer_states()))
        group_items: dict[str, QTreeWidgetItem] = {}
        for state in states:
            if not state.is_group:
                continue
            visible_layer_ids.add(state.layer_id)
            group_item = QTreeWidgetItem(["", state.display_name])
            group_item.setData(0, ROLE_TYPE, "group")
            group_item.setData(0, ROLE_LAYER_ID, state.layer_id)
            group_item.setFlags(group_item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDropEnabled)
            self.tree.addTopLevelItem(group_item)
            self.tree.setItemWidget(group_item, 0, self._layer_controls(group_item, state.layer_id, state.visible))
            group_item.setExpanded(state.layer_id not in self._seen_layer_ids or state.layer_id in self._expanded_layer_ids)
            group_items[state.layer_id] = group_item
            self._sync_layer_toggle_icon(group_item)
        for state in states:
            if state.is_group:
                continue
            visible_layer_ids.add(state.layer_id)
            layer_item = QTreeWidgetItem(["", state.display_name])
            layer_item.setData(0, ROLE_TYPE, "layer")
            layer_item.setData(0, ROLE_LAYER_ID, state.layer_id)
            layer_item.setData(0, ROLE_GROUP_ID, state.group_id)
            layer_item.setFlags(layer_item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsDragEnabled)
            if state.active:
                for column in range(2):
                    layer_item.setBackground(column, QBrush(QColor(self._active_row_color)))
            parent_group = group_items.get(state.group_id)
            if parent_group is not None:
                parent_group.addChild(layer_item)
            else:
                self.tree.addTopLevelItem(layer_item)
            if state.active:
                self.tree.setCurrentItem(layer_item)
                layer_item.setSelected(True)
            self.tree.setItemWidget(layer_item, 0, self._layer_controls(layer_item, state.layer_id, state.visible))
            for object_state in self.canvas.get_layer_object_states(state.layer_id):
                child = QTreeWidgetItem(["", object_state.label])
                child.setData(0, ROLE_TYPE, "object")
                child.setData(0, ROLE_LAYER_ID, object_state.layer_id)
                child.setData(0, ROLE_ID, object_state.object_id)
                child.setData(0, ROLE_OBJECT_TYPE, object_state.object_type)
                child.setData(0, ROLE_Z_INDEX, object_state.z_index)
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled)
                layer_item.addChild(child)
                self.tree.setItemWidget(child, 0, self._object_controls(child, object_state.visible, object_state.locked))
            layer_item.setExpanded(state.layer_id not in self._seen_layer_ids or state.layer_id in self._expanded_layer_ids)
            self._sync_layer_toggle_icon(layer_item)
        self._seen_layer_ids = visible_layer_ids
        self._refreshing = False

    def retranslate(self) -> None:
        """Refresh button and header text."""
        self.title_label.setText(t("dock.layers"))
        self.tree.setHeaderLabels(["", t("layer.name")])
        self.add_button.setToolTip(t("layer.add"))
        self.add_group_button.setToolTip(t("layer.group_add"))
        self.delete_button.setToolTip(t("layer.delete"))
        self.up_button.setToolTip(t("layer.bring_forward"))
        self.down_button.setToolTip(t("layer.send_backward"))
        self.close_button.setToolTip(t("button.close"))

    def clear_selection_silently(self) -> None:
        """Clear tree selection without changing the active canvas layer."""
        previous_refreshing = self._refreshing
        self._refreshing = True
        self.tree.blockSignals(True)
        self.tree.clearSelection()
        self.tree.setCurrentItem(None)
        self.tree.blockSignals(False)
        self._refreshing = previous_refreshing

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        self.setObjectName("layersPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(240)
        self.setMaximumWidth(340)

        header_row = QHBoxLayout()
        header_row.setSpacing(6)
        self.title_label = QLabel(self)
        self.title_label.setObjectName("sectionTitle")
        self.close_button = self._tool_button("close")
        self.close_button.clicked.connect(self.close_requested.emit)
        header_row.addWidget(self.title_label, 1)
        header_row.addWidget(self.close_button)
        layout.addLayout(header_row)
        layout.addWidget(self._separator())

        self.tree = LayersTreeWidget(self)
        self.tree.setObjectName("layersTree")
        self.tree.setColumnCount(2)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setAutoScroll(True)
        self.tree.setAutoScrollMargin(28)
        self.tree.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.tree.setRootIsDecorated(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.setColumnWidth(0, 82)
        self.tree.object_dropped.connect(self._move_dropped_object)
        self.tree.object_reordered.connect(self._reorder_dropped_object)
        self.tree.layer_grouped.connect(self._set_layer_group)
        self.tree.itemExpanded.connect(self._handle_item_expanded)
        self.tree.itemCollapsed.connect(self._handle_item_collapsed)
        self.tree.itemSelectionChanged.connect(self._handle_selection)
        self.tree.itemClicked.connect(self._handle_click)
        self.tree.itemChanged.connect(self._handle_item_changed)
        layout.addWidget(self.tree)

        row = QHBoxLayout()
        row.setSpacing(4)
        self.add_button = self._tool_button("add_layer")
        self.add_group_button = self._tool_button("add_group")
        self.delete_button = self._tool_button("delete")
        self.up_button = self._tool_button("up")
        self.down_button = self._tool_button("down")
        self.add_button.clicked.connect(self._add_layer)
        self.add_group_button.clicked.connect(self._add_group)
        self.delete_button.clicked.connect(self._delete_selected)
        self.up_button.clicked.connect(lambda: self._move_selected_index(1))
        self.down_button.clicked.connect(lambda: self._move_selected_index(-1))
        for button in [self.add_button, self.add_group_button, self.delete_button, self.up_button, self.down_button]:
            row.addWidget(button)
        layout.addLayout(row)
        self.apply_theme(False)
        self.retranslate()

    def apply_theme(self, light_theme: bool) -> None:
        """Apply the shared application palette to the panel."""
        self._icon_color = LIGHT_TEXT if light_theme else TEXT_ON_DARK
        self._active_row_color = LIGHT_ACTIVE_ROW if light_theme else DARK_ACTIVE_ROW
        self.setStyleSheet(layers_panel_stylesheet(light_theme))
        self._refresh_icons()
        self.refresh()

    def _handle_selection(self) -> None:
        if self._refreshing:
            return
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return
        
        layer_ids_to_activate: set[str] = set()
        objects_to_select: list[tuple[str, str]] = []
        
        self._refreshing = True
        try:
            self.tree.blockSignals(True)
            
            for item in selected_items:
                row_type = item.data(0, ROLE_TYPE)
                
                if row_type == "group":
                    continue
                elif row_type == "layer":
                    layer_id = str(item.data(0, ROLE_LAYER_ID))
                    layer_ids_to_activate.add(layer_id)
                    
                    # Auto-select all objects in this layer
                    for child_index in range(item.childCount()):
                        child = item.child(child_index)
                        if child.data(0, ROLE_TYPE) == "object":
                            child.setSelected(True)
                            obj_type = str(child.data(0, ROLE_OBJECT_TYPE))
                            obj_id = str(child.data(0, ROLE_ID))
                            objects_to_select.append((obj_type, obj_id))
                            
                elif row_type == "object":
                    obj_type = str(item.data(0, ROLE_OBJECT_TYPE))
                    obj_id = str(item.data(0, ROLE_ID))
                    objects_to_select.append((obj_type, obj_id))
            
            self.tree.blockSignals(False)
            
            # Set active layer (use last selected layer)
            if layer_ids_to_activate:
                self.canvas.set_active_layer(list(layer_ids_to_activate)[-1])
            
            # Select all objects on canvas
            for obj_type, obj_id in objects_to_select:
                self.canvas.select_layer_object(obj_type, obj_id)
        finally:
            self._refreshing = False

    def _handle_click(self, item: QTreeWidgetItem, column: int) -> None:
        if item.data(0, ROLE_TYPE) != "layer":
            return
        layer_id = str(item.data(0, ROLE_LAYER_ID))
        if column == 0:
            return

    def _handle_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._refreshing or self._renaming or column != 1:
            return
        row_type = item.data(0, ROLE_TYPE)
        self._renaming = True
        try:
            if row_type in {"layer", "group"}:
                layer_id = str(item.data(0, ROLE_LAYER_ID))
                display_name = item.text(1).strip()
                if not display_name:
                    self.refresh()
                    return
                self._begin_history("layer_rename")
                self.canvas.rename_layer(layer_id, display_name)
                if not self.camera_manager.rename_layer(layer_id, display_name):
                    self.refresh()
                    self._commit_history("layer_rename")
                    return
                self._reload_layers()
                self._commit_history("layer_rename")
            elif row_type == "object":
                if not self.canvas.rename_layer_object(
                    str(item.data(0, ROLE_OBJECT_TYPE)),
                    str(item.data(0, ROLE_ID)),
                    item.text(1),
                ):
                    self.refresh()
        finally:
            self._renaming = False

    def _add_layer(self) -> None:
        layout_id = self.layout_id_callback()
        self._begin_history("layer_add")
        layer = self.camera_manager.create_layer(f"{t('layer.new')} {len(self.canvas.get_layer_states()) + 1}", layout_id)
        self._reload_layers()
        self.canvas.set_active_layer(layer.id)
        self.refresh()
        self._commit_history("layer_add")

    def _add_group(self) -> None:
        layout_id = self.layout_id_callback()
        self._begin_history("layer_group_add")
        self.camera_manager.create_layer_group(f"{t('layer.group')} {len(self.canvas.get_layer_states()) + 1}", layout_id)
        self._reload_layers()
        self._commit_history("layer_group_add")

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
        item = self.tree.currentItem()
        is_group = item is not None and item.data(0, ROLE_TYPE) == "group"
        if not is_group and self.canvas.get_layer_object_states(layer_id):
            if not confirm_dialog.confirm(self, t("layer.delete"), t("layer.delete_confirm")):
                return
        self._begin_history("layer_delete")
        self.canvas.delete_layer_items(layer_id)
        self.camera_manager.delete_layer(layer_id)
        self._reload_layers()
        self._commit_history("layer_delete")
        self._show_status(t("status.layer_deleted", count=1), 5000)

    def _delete_selected_object(self, item: QTreeWidgetItem) -> None:
        object_type = str(item.data(0, ROLE_OBJECT_TYPE))
        object_id = str(item.data(0, ROLE_ID))
        if not self.canvas.select_layer_object(object_type, object_id):
            return
        count = self.canvas.delete_selected_drawings()
        self.refresh()
        if count:
            self._show_status(t("status.drawing_deleted", count=count), 5000)

    def _move_selected_index(self, direction: int) -> None:
        item = self.tree.currentItem()
        if item is None:
            return
        row_type = item.data(0, ROLE_TYPE)
        if row_type in {"group", "layer"}:
            layer_id = str(item.data(0, ROLE_LAYER_ID))
            self._begin_history("layer_move")
            if self.camera_manager.move_layer(layer_id, direction, self.layout_id_callback()):
                self._reload_layers()
            self._commit_history("layer_move")
            return
        if row_type == "object":
            object_type = str(item.data(0, ROLE_OBJECT_TYPE))
            object_id = str(item.data(0, ROLE_ID))
            selected_keys = self._selected_object_keys()
            if self.canvas.move_layer_object(object_type, object_id, direction):
                self.refresh()
                self._restore_object_selection(selected_keys, (object_type, object_id))
            return

    def _move_dropped_object(self, object_type: str, object_id: str, layer_id: str) -> None:
        if self.canvas.move_layer_object_to_layer(object_type, object_id, layer_id):
            self.refresh()
            self._show_status(t("status.layer_moved", count=1), 3000)

    def _reorder_dropped_object(self, object_type: str, object_id: str, layer_id: str, target_index: int) -> None:
        if self.canvas.move_layer_object_to_index(object_type, object_id, layer_id, target_index):
            self.refresh()
            self._restore_object_selection([(object_type, object_id)], (object_type, object_id))

    def _set_layer_group(self, layer_id: str, group_id: str) -> None:
        if not layer_id or layer_id == group_id:
            return
        self._begin_history("layer_group")
        if self.camera_manager.set_layer_group(layer_id, group_id, self.layout_id_callback()):
            self._reload_layers()
        self._commit_history("layer_group")

    def _selected_layer_id(self) -> str:
        item = self.tree.currentItem()
        if item is None:
            return ""
        if item.data(0, ROLE_TYPE) == "object":
            item = item.parent()
        if item is not None and item.data(0, ROLE_TYPE) == "group":
            return str(item.data(0, ROLE_LAYER_ID))
        return str(item.data(0, ROLE_LAYER_ID)) if item is not None else ""

    def _selected_object_keys(self) -> list[tuple[str, str]]:
        keys: list[tuple[str, str]] = []
        for item in self.tree.selectedItems():
            if item.data(0, ROLE_TYPE) == "object":
                keys.append((str(item.data(0, ROLE_OBJECT_TYPE)), str(item.data(0, ROLE_ID))))
        return keys

    def _restore_object_selection(
        self,
        selected_keys: list[tuple[str, str]],
        current_key: tuple[str, str],
    ) -> None:
        self._refreshing = True
        self.tree.blockSignals(True)
        self.tree.clearSelection()
        current_item: QTreeWidgetItem | None = None
        selected_set = set(selected_keys)
        selected_set.add(current_key)
        for object_type, object_id in selected_set:
            target = self._find_object_tree_item(object_type, object_id)
            if target is None:
                continue
            target.setSelected(True)
            if (object_type, object_id) == current_key:
                current_item = target
        if current_item is not None:
            self.tree.setCurrentItem(current_item)
        self.tree.blockSignals(False)
        self._refreshing = False

    def _find_object_tree_item(self, object_type: str, object_id: str) -> QTreeWidgetItem | None:
        for index in range(self.tree.topLevelItemCount()):
            found = self._find_object_tree_item_in_branch(self.tree.topLevelItem(index), object_type, object_id)
            if found is not None:
                return found
        return None

    def _find_object_tree_item_in_branch(
        self,
        item: QTreeWidgetItem,
        object_type: str,
        object_id: str,
    ) -> QTreeWidgetItem | None:
        if (
            item.data(0, ROLE_TYPE) == "object"
            and str(item.data(0, ROLE_OBJECT_TYPE)) == object_type
            and str(item.data(0, ROLE_ID)) == object_id
        ):
            return item
        for child_index in range(item.childCount()):
            found = self._find_object_tree_item_in_branch(item.child(child_index), object_type, object_id)
            if found is not None:
                return found
        return None

    def _reload_layers(self) -> None:
        layout_id = self.layout_id_callback()
        self.canvas.set_canvas_layers(self.camera_manager.get_layers(layout_id), layout_id)
        self.refresh()

    def _show_status(self, message: str, timeout_ms: int) -> None:
        if self.status_callback is not None:
            self.status_callback(message, timeout_ms)

    def _layer_controls(self, item: QTreeWidgetItem, layer_id: str, checked: bool) -> QWidget:
        controls = QWidget(self.tree)
        controls.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        layout = QHBoxLayout(controls)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        toggle = QToolButton(controls)
        toggle.setProperty("icon_name", "collapse" if item.isExpanded() else "expand")
        toggle.setAutoRaise(True)
        toggle.setIconSize(QSize(14, 14))
        toggle.setFixedSize(20, 22)
        toggle.setToolTip(t("layer.collapse") if item.isExpanded() else t("layer.expand"))
        toggle.clicked.connect(lambda _checked=False, target=item: self._toggle_layer_item(target))
        visibility = QToolButton(controls)
        visibility.setCheckable(True)
        visibility.setChecked(checked)
        visibility.setProperty("icon_name", "show" if checked else "hide")
        visibility.setIcon(self._icon("show" if checked else "hide"))
        visibility.setIconSize(QSize(14, 14))
        visibility.setFixedSize(20, 22)
        visibility.setToolTip(t("layer.visible"))
        visibility.clicked.connect(lambda visible=False, target=layer_id, button=visibility: self._set_layer_visible(target, visible, button))
        lock = QToolButton(controls)
        lock.setCheckable(True)
        lock.setChecked(self.canvas.layer_locked.get(layer_id, False))
        lock.setIcon(self._icon("lock" if lock.isChecked() else "unlock"))
        lock.setIconSize(QSize(14, 14))
        lock.setFixedSize(20, 22)
        lock.setToolTip(t("layer.locked"))
        lock.clicked.connect(lambda checked=False, target=layer_id: self._set_layer_locked(target, checked))
        layout.addWidget(toggle)
        layout.addWidget(visibility)
        layout.addWidget(lock)
        layout.addStretch(1)
        self._layer_toggle_buttons[layer_id] = toggle
        return controls

    def _object_controls(self, item: QTreeWidgetItem, visible: bool, locked: bool) -> QWidget:
        controls = QWidget(self.tree)
        layout = QHBoxLayout(controls)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        visibility = QToolButton(controls)
        visibility.setCheckable(True)
        visibility.setChecked(visible)
        visibility.setProperty("icon_name", "show" if visible else "hide")
        visibility.setIcon(self._icon("show" if visible else "hide"))
        visibility.setIconSize(QSize(14, 14))
        visibility.setFixedSize(24, 22)
        visibility.setToolTip(t("layer.visible"))
        visibility.clicked.connect(
            lambda checked=False, target=item, button=visibility: self._set_object_visible(
                str(target.data(0, ROLE_OBJECT_TYPE)),
                str(target.data(0, ROLE_ID)),
                checked,
                button,
            )
        )
        lock = QToolButton(controls)
        lock.setCheckable(True)
        lock.setChecked(locked)
        lock.setProperty("icon_name", "lock" if locked else "unlock")
        lock.setIcon(self._icon("lock" if locked else "unlock"))
        lock.setIconSize(QSize(14, 14))
        lock.setFixedSize(24, 22)
        lock.setToolTip(t("layer.locked"))
        lock.clicked.connect(
            lambda checked=False, target=item: self._set_object_locked(
                str(target.data(0, ROLE_OBJECT_TYPE)),
                str(target.data(0, ROLE_ID)),
                checked,
            )
        )
        layout.addWidget(visibility)
        layout.addWidget(lock)
        layout.addStretch(1)
        return controls

    def _toggle_layer_item(self, item: QTreeWidgetItem) -> None:
        item.setExpanded(not item.isExpanded())

    def _handle_item_expanded(self, item: QTreeWidgetItem) -> None:
        if item.data(0, ROLE_TYPE) != "layer":
            if item.data(0, ROLE_TYPE) != "group":
                return
        layer_id = str(item.data(0, ROLE_LAYER_ID))
        self._expanded_layer_ids.add(layer_id)
        self._sync_layer_toggle_icon(item)

    def _handle_item_collapsed(self, item: QTreeWidgetItem) -> None:
        if item.data(0, ROLE_TYPE) != "layer":
            if item.data(0, ROLE_TYPE) != "group":
                return
        layer_id = str(item.data(0, ROLE_LAYER_ID))
        self._expanded_layer_ids.discard(layer_id)
        self._sync_layer_toggle_icon(item)

    def _sync_layer_toggle_icon(self, item: QTreeWidgetItem) -> None:
        layer_id = str(item.data(0, ROLE_LAYER_ID))
        button = self._layer_toggle_buttons.get(layer_id)
        if button is None:
            return
        icon_name = "collapse" if item.isExpanded() else "expand"
        button.setProperty("icon_name", icon_name)
        button.setIcon(self._icon(icon_name))
        button.setToolTip(t("layer.collapse") if item.isExpanded() else t("layer.expand"))

    def _current_expanded_layer_ids(self) -> set[str]:
        expanded: set[str] = set()
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            if item.isExpanded():
                expanded.add(str(item.data(0, ROLE_LAYER_ID)))
            for child_index in range(item.childCount()):
                child = item.child(child_index)
                if child.isExpanded():
                    expanded.add(str(child.data(0, ROLE_LAYER_ID)))
        return expanded

    def _set_layer_visible(self, layer_id: str, visible: bool, button: QToolButton | None = None) -> None:
        if self._refreshing:
            return
        if button is not None:
            button.setProperty("icon_name", "show" if visible else "hide")
            button.setIcon(self._icon("show" if visible else "hide"))
        self._begin_history("layer_visible")
        self.canvas.set_layer_visible(layer_id, visible)
        self.camera_manager.set_layer_visible(layer_id, visible)
        self.refresh()
        self._commit_history("layer_visible")

    def _set_layer_locked(self, layer_id: str, locked: bool) -> None:
        if self._refreshing:
            return
        self._begin_history("layer_lock")
        self.canvas.set_layer_locked(layer_id, locked)
        self.camera_manager.set_layer_locked(layer_id, locked)
        self.refresh()
        self._commit_history("layer_lock")

    def _set_object_locked(self, object_type: str, object_id: str, locked: bool) -> None:
        if self._refreshing:
            return
        self.canvas.set_layer_object_locked(object_type, object_id, locked)

    def _set_object_visible(
        self,
        object_type: str,
        object_id: str,
        visible: bool,
        button: QToolButton | None = None,
    ) -> None:
        if self._refreshing:
            return
        if button is not None:
            button.setProperty("icon_name", "show" if visible else "hide")
            button.setIcon(self._icon("show" if visible else "hide"))
        self.canvas.set_layer_object_visible(object_type, object_id, visible)

    def _tool_button(self, icon_name: str) -> QToolButton:
        button = QToolButton(self)
        button.setAutoRaise(False)
        button.setProperty("icon_name", icon_name)
        button.setIcon(self._icon(icon_name))
        button.setIconSize(QSize(22, 22))
        button.setFixedSize(32, 30)
        return button

    def _icon(self, icon_name: str) -> QIcon:
        return tool_icon(icon_name, color=self._icon_color)

    def _refresh_icons(self) -> None:
        for button in self.findChildren(QToolButton):
            icon_name = button.property("icon_name")
            if icon_name:
                button.setIcon(self._icon(str(icon_name)))

    def _separator(self) -> QFrame:
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        return line

    def _begin_history(self, label: str) -> None:
        self.canvas._begin_history_step(label)

    def _commit_history(self, label: str) -> None:
        self.canvas._commit_history_step(label)
