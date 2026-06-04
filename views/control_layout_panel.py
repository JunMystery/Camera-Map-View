"""Combined layout and camera control panel."""

from collections.abc import Callable

from PyQt6.QtCore import QEvent, QMimeData, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QDrag, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QSizePolicy,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.i18n import t
from models.camera_data_model import Camera
from models.device_catalog import device_kind_label
from models.device_link_model import DeviceLink
from models.map_layout_model import MapLayout
from views.tool_icons import device_icon, device_pixmap, tool_icon
from views.ui_theme import DANGER, LIGHT_TEXT, PRIMARY, SUCCESS, TEXT_ON_DARK, TEXT_WHITE, control_panel_stylesheet


class CameraTreeWidget(QTreeWidget):
    """Tree widget that drags child device ids onto the map canvas."""

    device_link_requested = pyqtSignal(str, str)
    device_unlink_requested = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._known_device_ids: set[str] = set()
        self._link_pairs: set[tuple[str, str]] = set()
        self._downstream_ids: dict[str, set[str]] = {}
        self._device_link_request_handler: Callable[[str, str], bool] | None = None
        self._device_unlink_request_handler: Callable[[list[str]], bool] | None = None
        self._drag_in_progress = False
        self.installEventFilter(self)
        self.viewport().installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        if self._drag_in_progress and event.type() == QEvent.Type.Wheel:
            if self._handle_drag_wheel_event(event):
                return True
        return super().eventFilter(watched, event)

    def set_link_context(self, devices: dict[str, Camera], links: list[DeviceLink]) -> None:
        """Store topology state used to validate sidebar quick-link drops."""
        self._known_device_ids = set(devices)
        self._link_pairs = {
            (link.source_device_id, link.target_device_id)
            for link in links
            if link.source_device_id in devices and link.target_device_id in devices
        }
        incoming: dict[str, list[str]] = {}
        for source_id, target_id in self._link_pairs:
            incoming.setdefault(target_id, []).append(source_id)
        self._downstream_ids = {
            device_id: self._collect_downstream_ids(device_id, incoming, set()) for device_id in self._known_device_ids
        }

    def set_device_link_request_handler(self, handler: Callable[[str, str], bool] | None) -> None:
        """Set the callback that persists a validated quick-link drop."""
        self._device_link_request_handler = handler

    def set_device_unlink_request_handler(self, handler: Callable[[list[str]], bool] | None) -> None:
        """Set the callback that ungroups selected devices from their parent links."""
        self._device_unlink_request_handler = handler

    def startDrag(self, supported_actions: Qt.DropAction) -> None:
        item = self.currentItem()
        if item is None:
            return
        if item.data(0, Qt.ItemDataRole.UserRole + 1) != "camera":
            return
        camera_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not camera_id:
            return
        mime_data = self._drag_mime_data(self._drag_items(item))
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.setPixmap(self._drag_pixmap(item.text(0), str(item.data(0, Qt.ItemDataRole.UserRole + 2) or "")))
        self._drag_in_progress = True
        try:
            drag.exec(Qt.DropAction.CopyAction)
        finally:
            self._drag_in_progress = False

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat("application/x-device-id"):
            self._accept_copy_drop(event)
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat("application/x-device-id"):
            self._auto_scroll_for_drag(event)
            target = self._drop_target_item(event)
            if target is not None and target.data(0, Qt.ItemDataRole.UserRole + 1) == "camera":
                if self._drop_sources_and_target(event) is None:
                    event.ignore()
                    return
            elif not self._drop_source_ids(event.mimeData()):
                event.ignore()
                return
            self._accept_copy_drop(event)
            return
        super().dragMoveEvent(event)

    def wheelEvent(self, event) -> None:
        if self._handle_drag_wheel_event(event):
            return
        super().wheelEvent(event)

    def dropEvent(self, event) -> None:
        if not event.mimeData().hasFormat("application/x-device-id"):
            super().dropEvent(event)
            return
        target = self._drop_target_item(event)
        if target is None or target.data(0, Qt.ItemDataRole.UserRole + 1) != "camera":
            source_ids = self._drop_source_ids(event.mimeData())
            if not source_ids:
                event.ignore()
                return
            if not self._request_device_unlink(source_ids):
                event.ignore()
                return
            self._accept_copy_drop(event)
            return
        ids = self._drop_sources_and_target(event)
        if ids is None:
            event.ignore()
            return
        source_ids, target_id = ids
        created_any = False
        for source_id in source_ids:
            created_any = self._request_device_link(source_id, target_id) or created_any
        if not created_any:
            event.ignore()
            return
        self._accept_copy_drop(event)

    def _drag_items(self, current_item: QTreeWidgetItem) -> list[QTreeWidgetItem]:
        selected_items = [
            item for item in self.selectedItems() if item.data(0, Qt.ItemDataRole.UserRole + 1) == "camera"
        ]
        if current_item not in selected_items:
            return [current_item]
        return selected_items

    def _drag_mime_data(self, items: QTreeWidgetItem | list[QTreeWidgetItem]) -> QMimeData:
        drag_items = items if isinstance(items, list) else [items]
        source_ids = list(
            dict.fromkeys(str(item.data(0, Qt.ItemDataRole.UserRole) or "") for item in drag_items)
        )
        source_ids = [source_id for source_id in source_ids if source_id]
        source_id = source_ids[0] if source_ids else ""
        source_parent_id = self._camera_parent_id(drag_items[0]) if drag_items else ""
        branch_ids = set(source_ids)
        for item_source_id in source_ids:
            branch_ids.update(self._downstream_ids.get(item_source_id, set()))
        mime_data = QMimeData()
        encoded_id = source_id.encode("utf-8")
        mime_data.setData("application/x-device-id", encoded_id)
        mime_data.setData("application/x-camera-id", encoded_id)
        mime_data.setData("application/x-device-source-id", encoded_id)
        mime_data.setData("application/x-device-root-id", encoded_id)
        mime_data.setData("application/x-device-source-ids", "\n".join(source_ids).encode("utf-8"))
        mime_data.setData("application/x-device-parent-id", source_parent_id.encode("utf-8"))
        mime_data.setData("application/x-device-branch-ids", "\n".join(sorted(branch_ids)).encode("utf-8"))
        return mime_data

    def _drop_sources_and_target(self, event) -> tuple[list[str], str] | None:
        mime_data = event.mimeData()
        source_ids = self._drop_source_ids(mime_data)
        target = self._drop_target_item(event)
        if target is None or target.data(0, Qt.ItemDataRole.UserRole + 1) != "camera":
            return None
        target_id = str(target.data(0, Qt.ItemDataRole.UserRole) or "")
        valid_sources = [
            source_id
            for source_id in source_ids
            if self._can_create_link(source_id, target_id, {source_id, *self._downstream_ids.get(source_id, set())})
        ]
        if not valid_sources:
            return None
        return valid_sources, target_id

    def _drop_source_ids(self, mime_data: QMimeData) -> list[str]:
        source_ids = self._mime_text(mime_data, "application/x-device-source-ids").splitlines()
        if not source_ids:
            source_id = self._mime_text(mime_data, "application/x-device-root-id") or self._mime_text(mime_data, "application/x-device-id")
            source_ids = [source_id]
        return list(dict.fromkeys(source_id for source_id in source_ids if source_id))

    def _drop_target_item(self, event) -> QTreeWidgetItem | None:
        return self.itemAt(event.position().toPoint()) if hasattr(event, "position") else self.itemAt(event.pos())

    def _can_create_link(self, source_id: str, target_id: str, branch_ids: set[str]) -> bool:
        if not source_id or not target_id or source_id == target_id:
            return False
        if source_id not in self._known_device_ids or target_id not in self._known_device_ids:
            return False
        if target_id in branch_ids or (source_id, target_id) in self._link_pairs:
            return False
        return not self._would_create_cycle(source_id, target_id)

    def _would_create_cycle(self, source_id: str, target_id: str) -> bool:
        pending = [target_id]
        visited: set[str] = set()
        while pending:
            current = pending.pop()
            if current == source_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            pending.extend(target for source, target in self._link_pairs if source == current)
        return False

    def _collect_downstream_ids(self, device_id: str, incoming: dict[str, list[str]], visited: set[str]) -> set[str]:
        if device_id in visited:
            return set()
        next_visited = {*visited, device_id}
        result: set[str] = set()
        for child_id in incoming.get(device_id, []):
            result.add(child_id)
            result.update(self._collect_downstream_ids(child_id, incoming, next_visited))
        return result

    def _camera_parent_id(self, item: QTreeWidgetItem) -> str:
        parent = item.parent()
        if parent is None or parent.data(0, Qt.ItemDataRole.UserRole + 1) != "camera":
            return ""
        return str(parent.data(0, Qt.ItemDataRole.UserRole) or "")

    def _mime_text(self, mime_data: QMimeData, key: str) -> str:
        if not mime_data.hasFormat(key):
            return ""
        return bytes(mime_data.data(key)).decode("utf-8")

    def _request_device_link(self, source_id: str, target_id: str) -> bool:
        if self._device_link_request_handler is not None:
            return bool(self._device_link_request_handler(source_id, target_id))
        self.device_link_requested.emit(source_id, target_id)
        return True

    def _request_device_unlink(self, source_ids: list[str]) -> bool:
        if self._device_unlink_request_handler is not None:
            return bool(self._device_unlink_request_handler(source_ids))
        self.device_unlink_requested.emit(source_ids)
        return True

    def _accept_copy_drop(self, event) -> None:
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()

    def _auto_scroll_for_drag(self, event) -> None:
        point = event.position().toPoint() if hasattr(event, "position") else event.pos()
        margin = max(12, self.autoScrollMargin())
        viewport_height = self.viewport().height()
        if point.y() < margin:
            self._scroll_by_steps(-self._edge_scroll_steps(margin - point.y(), margin))
        elif point.y() > viewport_height - margin:
            self._scroll_by_steps(self._edge_scroll_steps(point.y() - (viewport_height - margin), margin))

    def _handle_drag_wheel_event(self, event) -> bool:
        if not self._drag_in_progress:
            return False
        pixel_delta = event.pixelDelta().y() if hasattr(event, "pixelDelta") else 0
        if pixel_delta:
            self._scroll_by_pixels(-pixel_delta)
            event.accept()
            return True
        delta = event.angleDelta().y()
        if not delta:
            return False
        self._scroll_by_delta(delta)
        event.accept()
        return True

    def _edge_scroll_steps(self, distance_into_margin: float, margin: int) -> int:
        ratio = min(1.0, max(0.0, distance_into_margin / max(1, margin)))
        return max(1, int(1 + ratio * 3))

    def _scroll_by_delta(self, delta: int) -> None:
        steps = max(1, abs(delta) // 120)
        self._scroll_by_steps((-steps if delta > 0 else steps) * 3)

    def _scroll_by_steps(self, steps: int) -> None:
        scroll_bar = self.verticalScrollBar()
        step_size = max(1, scroll_bar.singleStep())
        self._scroll_by_pixels(steps * step_size)

    def _scroll_by_pixels(self, pixels: int) -> None:
        scroll_bar = self.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.value() + pixels)

    def _drag_pixmap(self, label: str, device_kind: str) -> QPixmap:
        pixmap = QPixmap(190, 36)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(PRIMARY))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 190, 36, 5, 5)
        icon = device_pixmap(device_kind, 24)
        painter.drawPixmap(8, 6, icon)
        painter.setPen(QColor(TEXT_WHITE))
        painter.drawText(38, 0, 146, 36, Qt.AlignmentFlag.AlignVCenter, label)
        painter.end()
        return pixmap


class DeviceParentPickerDialog(QDialog):
    """Pick one parent device from the full layout device catalog."""

    def __init__(
        self,
        source_id: str,
        cameras: dict[str, Camera],
        device_links: list[DeviceLink],
        parent_ip_lookup: Callable[[str], str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.source_id = source_id
        self.cameras = cameras
        self.device_links = device_links
        self.parent_ip_lookup = parent_ip_lookup
        self.selected_parent_id = ""
        self._excluded_ids = self._excluded_parent_ids()
        self.setWindowTitle(t("dialog.parent_picker.title"))
        self.setMinimumSize(420, 500)
        self._build_ui()
        self._refresh_list()

    def selected_device_id(self) -> str:
        """Return the selected parent device id."""
        return self.selected_parent_id

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText(t("dialog.parent_picker.search"))
        self.search_input.textChanged.connect(self._refresh_list)
        layout.addWidget(self.search_input)

        self.tree_widget = QTreeWidget(self)
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setIndentation(8)
        self.tree_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree_widget.itemSelectionChanged.connect(self._sync_buttons)
        self.tree_widget.itemDoubleClicked.connect(lambda _item, _column: self._accept_current())
        layout.addWidget(self.tree_widget, 1)

        self.empty_label = QLabel(t("dialog.parent_picker.empty"), self)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_label)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.buttons.accepted.connect(self._accept_current)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        yes_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        no_button = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if yes_button is not None:
            yes_button.setText(t("button.yes"))
            yes_button.setDefault(True)
        if no_button is not None:
            no_button.setText(t("button.no"))
            no_button.setObjectName("confirmNoButton")
            no_button.setStyleSheet(
                f"""
                QPushButton#confirmNoButton {{
                    background: {DANGER};
                    color: {TEXT_WHITE};
                    border: none;
                    border-radius: 4px;
                    padding: 6px 14px;
                }}
                """
            )
        self._sync_buttons()

    def _refresh_list(self) -> None:
        query = self.search_input.text().strip().lower()
        self.tree_widget.clear()
        for camera in sorted(self.cameras.values(), key=lambda item: (item.name.lower(), item.id)):
            if camera.id in self._excluded_ids:
                continue
            if query and query not in self._search_text(camera):
                continue
            item = QTreeWidgetItem([self._device_text(camera)])
            item.setData(0, Qt.ItemDataRole.UserRole, camera.id)
            item.setIcon(0, device_icon(camera.device_kind))
            item.setToolTip(0, self._device_tooltip(camera))
            self.tree_widget.addTopLevelItem(item)
        self.empty_label.setVisible(self.tree_widget.topLevelItemCount() == 0)
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setEnabled(self.tree_widget.currentItem() is not None)

    def _accept_current(self) -> None:
        item = self.tree_widget.currentItem()
        if item is None:
            return
        self.selected_parent_id = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
        if self.selected_parent_id:
            self.accept()

    def _excluded_parent_ids(self) -> set[str]:
        incoming: dict[str, list[str]] = {}
        for link in self.device_links:
            incoming.setdefault(link.target_device_id, []).append(link.source_device_id)
        return {self.source_id, *self._descendant_ids(self.source_id, incoming, set())}

    def _descendant_ids(self, device_id: str, incoming: dict[str, list[str]], visited: set[str]) -> set[str]:
        if device_id in visited:
            return set()
        result: set[str] = set()
        for child_id in incoming.get(device_id, []):
            result.add(child_id)
            result.update(self._descendant_ids(child_id, incoming, {*visited, device_id}))
        return result

    def _search_text(self, camera: Camera) -> str:
        return (
            f"{camera.name} {camera.ip_address} {camera.device_kind} "
            f"{camera.effective_variant()} {self.parent_ip_lookup(camera.id)}"
        ).lower()

    def _device_text(self, camera: Camera) -> str:
        ip_address = camera.ip_address or t("device.ip_empty")
        return f"{camera.name} ({ip_address}) - {device_kind_label(camera.device_kind)} / {camera.effective_variant()}"

    def _device_tooltip(self, camera: Camera) -> str:
        parent_ip = self.parent_ip_lookup(camera.id) or t("camera_panel.no_dvr")
        return f"{self._device_text(camera)}\n{t('action.show_dvr')}: {parent_ip}"


class ControlLayoutPanel(QWidget):
    """Manage layouts and cameras from one fixed sidebar."""

    layout_selected = pyqtSignal(str)
    layout_add_requested = pyqtSignal()
    layout_rename_requested = pyqtSignal(str)
    layout_delete_requested = pyqtSignal(str)
    camera_add_requested = pyqtSignal()
    camera_edit_requested = pyqtSignal(str)
    camera_delete_requested = pyqtSignal(str)
    camera_import_requested = pyqtSignal()
    camera_export_requested = pyqtSignal()
    camera_focus_requested = pyqtSignal(str)
    device_link_requested = pyqtSignal(str, str)
    device_unlink_requested = pyqtSignal(object)
    device_parent_change_requested = pyqtSignal(str, str)
    close_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("controlLayoutPanel")
        self.cameras: dict[str, Camera] = {}
        self.placed_ids: set[str] = set()
        self.device_links: list[DeviceLink] = []
        self.show_placed = True
        self.status_filter = "all"
        self.layouts: list[MapLayout] = []
        self._refreshing = False
        self._icon_color = TEXT_ON_DARK
        self._device_link_request_handler: Callable[[str, str], bool] | None = None
        self._device_unlink_request_handler: Callable[[list[str]], bool] | None = None
        self._last_search_query = ""
        self._pre_search_expanded_groups: set[str] = set()
        self._build_ui()
        self.retranslate()

    def set_layouts(self, layouts: list[MapLayout], current_layout_id: str) -> None:
        """Refresh layout choices and current selection."""
        self.layouts = layouts
        self.layout_combo.blockSignals(True)
        self.layout_combo.clear()
        for layout in layouts:
            self.layout_combo.addItem(layout.name, layout.id)
            if layout.id == current_layout_id:
                self.layout_combo.setCurrentIndex(self.layout_combo.count() - 1)
        self.layout_combo.blockSignals(False)

    def current_layout_id(self) -> str:
        """Return selected layout id."""
        return str(self.layout_combo.currentData() or "")

    def set_cameras(self, cameras: list[Camera], placed_ids: set[str], device_links: list[DeviceLink] | None = None) -> None:
        """Replace the camera snapshot and refresh the tree."""
        self.cameras = {camera.id: camera for camera in cameras}
        self.placed_ids = placed_ids
        self.device_links = list(device_links or [])
        self.tree_widget.set_link_context(self.cameras, self.device_links)
        self.refresh_list()

    def set_device_link_request_handler(self, handler: Callable[[str, str], bool] | None) -> None:
        """Set callback used by quick-link drops to persist and report success."""
        self._device_link_request_handler = handler

    def set_device_unlink_request_handler(self, handler: Callable[[list[str]], bool] | None) -> None:
        """Set callback used by quick-link drops and context menu to ungroup devices."""
        self._device_unlink_request_handler = handler

    def add_camera_to_list(self, camera: Camera) -> None:
        """Add a camera to the panel snapshot."""
        self.cameras[camera.id] = camera
        self.tree_widget.set_link_context(self.cameras, self.device_links)
        self.refresh_list()

    def remove_camera_from_list(self, camera_id: str) -> Camera | None:
        """Mark a camera as placed and return it for map placement."""
        camera = self.cameras.get(camera_id)
        if camera is not None:
            self.placed_ids.add(camera_id)
            self.refresh_list()
        return camera

    def refresh_list(self) -> None:
        """Rebuild camera groups from search and placement filters."""
        query = self.search_input.text().strip().lower()
        current_expanded = self._expanded_group_keys()
        if query and not self._last_search_query:
            self._pre_search_expanded_groups = set(current_expanded)
        search_cleared = not query and bool(self._last_search_query)
        if search_cleared:
            expanded_groups = set(self._pre_search_expanded_groups)
            self._pre_search_expanded_groups.clear()
        else:
            expanded_groups = set(current_expanded)
        self._last_search_query = query
        self._refreshing = True
        if search_cleared:
            self.tree_widget.clearSelection()
            self.tree_widget.setCurrentItem(None)
        self.tree_widget.clear()
        incoming, outgoing, linked_ids, outgoing_sources = self._link_maps()
        display_ids, matched_ids = self._display_device_ids(query, incoming, outgoing)
        if query:
            expanded_groups.update(self._search_expanded_ids(matched_ids, incoming, outgoing, linked_ids))
        root_ids = sorted(
            [device_id for device_id in linked_ids if device_id not in outgoing_sources and device_id in display_ids],
            key=lambda device_id: self.cameras[device_id].name if device_id in self.cameras else device_id,
        )
        for root_id in root_ids:
            if root_id in self.cameras:
                self.tree_widget.addTopLevelItem(self._device_tree_item(root_id, incoming, display_ids, expanded_groups, set()))

        unlinked_ids = sorted(
            [device_id for device_id in matched_ids if device_id not in linked_ids],
            key=lambda device_id: self.cameras[device_id].name,
        )
        if unlinked_ids:
            group_item = QTreeWidgetItem([f"{t('camera_panel.unlinked_group')} ({len(unlinked_ids)})"])
            group_item.setData(0, Qt.ItemDataRole.UserRole, "group:unlinked")
            self.tree_widget.addTopLevelItem(group_item)
            for device_id in unlinked_ids:
                group_item.addChild(self._device_tree_item(device_id, incoming, display_ids, expanded_groups, set()))
            group_item.setExpanded("group:unlinked" in expanded_groups)
        self._restore_expanded_tree_state(expanded_groups)
        if search_cleared:
            self.tree_widget.clearSelection()
            self.tree_widget.setCurrentItem(None)
            self.tree_widget.collapseAll()
            self._set_exact_expanded_tree_state(expanded_groups)
        if query:
            self._scroll_to_first_match(matched_ids)
        self._refreshing = False

    def retranslate(self) -> None:
        """Refresh labels and tooltips."""
        self.layout_title.setText(t("dock.layouts"))
        self.camera_title.setText(t("dock.control_panel"))
        self.search_input.setPlaceholderText(t("camera_panel.search"))
        self.status_filter_input.setItemText(0, t("camera_panel.status_all"))
        self.status_filter_input.setItemText(1, t("camera_panel.online_group"))
        self.status_filter_input.setItemText(2, t("camera_panel.offline_group"))
        self.status_filter_input.setItemText(3, t("camera_panel.unknown_group"))
        self.unplaced_button.setToolTip(t("camera_panel.unplaced"))
        self.placed_button.setToolTip(t("camera_panel.placed"))
        self.unplaced_button.setText(t("camera_panel.unplaced"))
        self.placed_button.setText(t("camera_panel.placed"))
        self.add_layout_button.setToolTip(t("layout.add"))
        self.rename_layout_button.setToolTip(t("layout.edit"))
        self.delete_layout_button.setToolTip(t("layout.delete"))
        self.add_button.setToolTip(t("camera_panel.add_device"))
        self.edit_button.setToolTip(t("camera_panel.edit"))
        self.delete_button.setToolTip(t("camera_panel.delete"))
        self.import_button.setToolTip(t("camera_panel.import"))
        self.export_button.setToolTip(t("camera_panel.export"))
        self.close_button.setToolTip(t("button.close"))
        self._sync_mode_buttons()
        self.refresh_list()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(6)
        self.layout_title = QLabel(self)
        self.layout_title.setObjectName("sectionTitle")
        self.close_button = self._tool_button("close")
        self.close_button.clicked.connect(self.close_requested.emit)
        header_row.addWidget(self.layout_title, 1)
        header_row.addWidget(self.close_button)
        layout.addLayout(header_row)

        layout_row = QHBoxLayout()
        self.layout_combo = QComboBox(self)
        self.layout_combo.currentIndexChanged.connect(self._emit_selected_layout)
        layout_row.addWidget(self.layout_combo, 1)
        self.add_layout_button = self._tool_button("add_layout")
        self.rename_layout_button = self._tool_button("cog")
        self.delete_layout_button = self._tool_button("delete")
        self.add_layout_button.clicked.connect(self.layout_add_requested.emit)
        self.rename_layout_button.clicked.connect(lambda: self.layout_rename_requested.emit(self.current_layout_id()))
        self.delete_layout_button.clicked.connect(lambda: self.layout_delete_requested.emit(self.current_layout_id()))
        for button in [self.add_layout_button, self.rename_layout_button, self.delete_layout_button]:
            layout_row.addWidget(button)
        layout.addLayout(layout_row)
        layout.addWidget(self._separator())

        self.camera_title = QLabel(self)
        self.camera_title.setObjectName("sectionTitle")
        layout.addWidget(self.camera_title)
        self.search_input = QLineEdit(self)
        self.search_input.textChanged.connect(self.refresh_list)
        layout.addWidget(self.search_input)
        self.status_filter_input = QComboBox(self)
        for value in ("all", "online", "offline", "unknown"):
            self.status_filter_input.addItem(value, value)
        self.status_filter_input.currentIndexChanged.connect(self._set_status_filter)
        layout.addWidget(self.status_filter_input)

        mode_row = QHBoxLayout()
        self.unplaced_button = self._mode_button()
        self.placed_button = self._mode_button()
        self.unplaced_button.clicked.connect(lambda: self._set_mode(False))
        self.placed_button.clicked.connect(lambda: self._set_mode(True))
        mode_row.addWidget(self.placed_button)
        mode_row.addWidget(self.unplaced_button)
        layout.addLayout(mode_row)

        self.tree_widget = CameraTreeWidget(self)
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setIndentation(10)
        self.tree_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree_widget.setDragEnabled(True)
        self.tree_widget.setAcceptDrops(True)
        self.tree_widget.setDropIndicatorShown(True)
        self.tree_widget.setAutoScroll(True)
        self.tree_widget.setAutoScrollMargin(28)
        self.tree_widget.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.tree_widget.set_device_link_request_handler(self._request_device_link_from_tree)
        self.tree_widget.set_device_unlink_request_handler(self._request_device_unlink_from_tree)
        self.tree_widget.itemSelectionChanged.connect(self._emit_focused_camera)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self._show_tree_context_menu)
        layout.addWidget(self.tree_widget, 1)

        action_row = QHBoxLayout()
        action_row.setSpacing(5)
        self.add_button = self._tool_button("add_camera")
        self.edit_button = self._tool_button("cog")
        self.delete_button = self._tool_button("delete")
        self.import_button = self._tool_button("import")
        self.export_button = self._tool_button("export")
        self.add_button.clicked.connect(self.camera_add_requested.emit)
        self.edit_button.clicked.connect(lambda: self._emit_selected_camera(self.camera_edit_requested))
        self.delete_button.clicked.connect(lambda: self._emit_selected_camera(self.camera_delete_requested))
        self.import_button.clicked.connect(self.camera_import_requested.emit)
        self.export_button.clicked.connect(self.camera_export_requested.emit)
        for button in [self.add_button, self.edit_button, self.delete_button, self.import_button, self.export_button]:
            action_row.addWidget(button)
        layout.addLayout(action_row)
        self._apply_style()

    def _tool_button(self, icon_name: str) -> QToolButton:
        button = QToolButton(self)
        button.setProperty("icon_name", icon_name)
        button.setIcon(self._icon(icon_name))
        button.setIconSize(QSize(22, 22))
        button.setFixedSize(32, 30)
        return button

    def _mode_button(self) -> QToolButton:
        button = QToolButton(self)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setCheckable(True)
        button.setMinimumHeight(34)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return button

    def _separator(self) -> QFrame:
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        return line

    def _emit_selected_layout(self) -> None:
        if self.layout_combo.currentData():
            self.layout_selected.emit(str(self.layout_combo.currentData()))

    def _emit_selected_camera(self, signal) -> None:
        item = self.tree_widget.currentItem()
        if item is not None and item.data(0, Qt.ItemDataRole.UserRole + 1) == "camera":
            signal.emit(item.data(0, Qt.ItemDataRole.UserRole))

    def _selected_device_ids(self) -> list[str]:
        ids = [
            str(item.data(0, Qt.ItemDataRole.UserRole) or "")
            for item in self.tree_widget.selectedItems()
            if item.data(0, Qt.ItemDataRole.UserRole + 1) == "camera"
        ]
        return list(dict.fromkeys(device_id for device_id in ids if device_id))

    def _show_tree_context_menu(self, pos) -> None:
        item = self.tree_widget.itemAt(pos)
        if item is None or item.data(0, Qt.ItemDataRole.UserRole + 1) != "camera":
            return
        if item not in self.tree_widget.selectedItems():
            self.tree_widget.clearSelection()
            item.setSelected(True)
            self.tree_widget.setCurrentItem(item)
        selected_ids = self._selected_device_ids()
        if not selected_ids:
            return

        menu = QMenu(self.tree_widget)
        if len(selected_ids) == 1:
            edit_action = QAction(t("camera.context.edit"), menu)
            edit_action.triggered.connect(lambda: self.camera_edit_requested.emit(selected_ids[0]))
            delete_action = QAction(t("camera_panel.delete"), menu)
            delete_action.triggered.connect(lambda: self.camera_delete_requested.emit(selected_ids[0]))
            change_parent_action = QAction(t("camera_panel.change_parent"), menu)
            change_parent_action.triggered.connect(lambda: self._show_parent_picker(selected_ids[0]))
            menu.addAction(edit_action)
            menu.addAction(delete_action)
            menu.addAction(change_parent_action)
            menu.addSeparator()
        ungroup_action = QAction(t("camera_panel.ungroup"), menu)
        ungroup_action.setEnabled(self._has_parent_link(selected_ids))
        ungroup_action.triggered.connect(lambda: self._request_device_unlink_from_tree(selected_ids))
        menu.addAction(ungroup_action)
        menu.exec(self.tree_widget.viewport().mapToGlobal(pos))

    def _show_parent_picker(self, source_device_id: str) -> None:
        dialog = DeviceParentPickerDialog(
            source_device_id,
            self.cameras,
            self.device_links,
            self._parent_ip_for_device,
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        target_parent_id = dialog.selected_device_id()
        if target_parent_id:
            self.device_parent_change_requested.emit(source_device_id, target_parent_id)

    def _emit_focused_camera(self) -> None:
        if self._refreshing:
            return
        item = self.tree_widget.currentItem()
        if item is None or item.data(0, Qt.ItemDataRole.UserRole + 1) != "camera":
            return
        camera_id = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
        if camera_id in self.placed_ids:
            self.camera_focus_requested.emit(camera_id)

    def _set_mode(self, show_placed: bool) -> None:
        self.show_placed = show_placed
        self._sync_mode_buttons()
        self.refresh_list()

    def _set_status_filter(self, _index: int | None = None) -> None:
        self.status_filter = str(self.status_filter_input.currentData() or "all")
        self.refresh_list()

    def _sync_mode_buttons(self) -> None:
        self.unplaced_button.setChecked(not self.show_placed)
        self.placed_button.setChecked(self.show_placed)

    def _matches(self, camera: Camera, query: str) -> bool:
        haystack = (
            f"{camera.name} {camera.ip_address} {self._parent_ip_for_device(camera.id)} "
            f"{camera.zone} {camera.device_kind} {camera.variant}"
        ).lower()
        return not query or query in haystack

    def _parent_ip_for_device(self, device_id: str) -> str:
        target_ids = sorted(
            {link.target_device_id for link in self.device_links if link.source_device_id == device_id},
            key=lambda item: (
                self.cameras[item].name if item in self.cameras else item,
                self.cameras[item].ip_address if item in self.cameras else "",
                item,
            ),
        )
        ips = [
            self.cameras[target_id].ip_address
            for target_id in target_ids
            if target_id in self.cameras and self.cameras[target_id].ip_address
        ]
        return ", ".join(dict.fromkeys(ips))

    def _matches_status(self, camera: Camera) -> bool:
        bucket = self._status_filter_key(camera)
        return self.status_filter == "all" or self.status_filter == bucket

    def _matches_scope(self, camera: Camera) -> bool:
        return (camera.id in self.placed_ids) == self.show_placed and self._matches_status(camera)

    def _camera_item_text(self, camera: Camera) -> str:
        return t(
            "camera_panel.item",
            name=camera.name,
            ip_address=camera.ip_address or t("device.ip_empty"),
            device_kind=device_kind_label(camera.device_kind),
            variant=camera.effective_variant(),
        )

    def _expanded_group_keys(self) -> set[str]:
        groups: set[str] = set()
        for index in range(self.tree_widget.topLevelItemCount()):
            self._collect_expanded_group_keys(self.tree_widget.topLevelItem(index), groups)
        return groups

    def _collect_expanded_group_keys(self, item: QTreeWidgetItem, groups: set[str]) -> None:
        if item.childCount() > 0 and item.isExpanded():
            groups.add(str(item.data(0, Qt.ItemDataRole.UserRole)))
        for child_index in range(item.childCount()):
            self._collect_expanded_group_keys(item.child(child_index), groups)

    def _restore_expanded_tree_state(self, expanded_groups: set[str]) -> None:
        for index in range(self.tree_widget.topLevelItemCount()):
            self._restore_expanded_item_state(self.tree_widget.topLevelItem(index), expanded_groups)

    def _restore_expanded_item_state(self, item: QTreeWidgetItem, expanded_groups: set[str]) -> None:
        if item.childCount() > 0:
            item.setExpanded(str(item.data(0, Qt.ItemDataRole.UserRole)) in expanded_groups)
        for child_index in range(item.childCount()):
            self._restore_expanded_item_state(item.child(child_index), expanded_groups)

    def _set_exact_expanded_tree_state(self, expanded_groups: set[str]) -> None:
        for index in range(self.tree_widget.topLevelItemCount()):
            self._set_exact_expanded_item_state(self.tree_widget.topLevelItem(index), expanded_groups)

    def _set_exact_expanded_item_state(self, item: QTreeWidgetItem, expanded_groups: set[str]) -> None:
        for child_index in range(item.childCount()):
            self._set_exact_expanded_item_state(item.child(child_index), expanded_groups)
        item.setExpanded(str(item.data(0, Qt.ItemDataRole.UserRole)) in expanded_groups)

    def _search_expanded_ids(
        self,
        matched_ids: set[str],
        incoming: dict[str, list[str]],
        outgoing: dict[str, list[str]],
        linked_ids: set[str],
    ) -> set[str]:
        expanded: set[str] = set()
        for device_id in matched_ids:
            expanded.update(self._ancestor_ids(device_id, outgoing, set()))
            expanded.update(self._descendant_ids(device_id, incoming, set()))
            if device_id not in linked_ids:
                expanded.add("group:unlinked")
            if incoming.get(device_id):
                expanded.add(device_id)
        return expanded

    def _scroll_to_first_match(self, matched_ids: set[str]) -> None:
        for index in range(self.tree_widget.topLevelItemCount()):
            item = self._first_matching_tree_item(self.tree_widget.topLevelItem(index), matched_ids)
            if item is not None:
                self.tree_widget.setCurrentItem(item)
                self.tree_widget.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
                return

    def _first_matching_tree_item(self, item: QTreeWidgetItem, matched_ids: set[str]) -> QTreeWidgetItem | None:
        if item.data(0, Qt.ItemDataRole.UserRole + 1) == "camera":
            device_id = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
            if device_id in matched_ids:
                return item
        for child_index in range(item.childCount()):
            found = self._first_matching_tree_item(item.child(child_index), matched_ids)
            if found is not None:
                return found
        return None

    def _link_maps(self) -> tuple[dict[str, list[str]], dict[str, list[str]], set[str], set[str]]:
        incoming: dict[str, list[str]] = {}
        outgoing: dict[str, list[str]] = {}
        linked_ids: set[str] = set()
        outgoing_sources: set[str] = set()
        for link in self.device_links:
            if link.source_device_id not in self.cameras or link.target_device_id not in self.cameras:
                continue
            incoming.setdefault(link.target_device_id, []).append(link.source_device_id)
            outgoing.setdefault(link.source_device_id, []).append(link.target_device_id)
            linked_ids.update({link.source_device_id, link.target_device_id})
            outgoing_sources.add(link.source_device_id)
        for sources in incoming.values():
            sources.sort(key=lambda device_id: self.cameras[device_id].name)
        for targets in outgoing.values():
            targets.sort(key=lambda device_id: self.cameras[device_id].name)
        return incoming, outgoing, linked_ids, outgoing_sources

    def _display_device_ids(
        self,
        query: str,
        incoming: dict[str, list[str]],
        outgoing: dict[str, list[str]],
    ) -> tuple[set[str], set[str]]:
        scope_ids = {device_id for device_id, camera in self.cameras.items() if self._matches_scope(camera)}
        matched_ids = {device_id for device_id in scope_ids if self._matches(self.cameras[device_id], query)}
        seeds = matched_ids if query else scope_ids
        display_ids = set(seeds)
        for device_id in list(seeds):
            display_ids.update(self._ancestor_ids(device_id, outgoing, set()))
        for device_id in list(matched_ids):
            display_ids.update(child_id for child_id in self._descendant_ids(device_id, incoming, set()) if child_id in scope_ids)
        return display_ids, matched_ids

    def _ancestor_ids(self, device_id: str, outgoing: dict[str, list[str]], visited: set[str]) -> set[str]:
        if device_id in visited:
            return set()
        result: set[str] = set()
        for parent_id in outgoing.get(device_id, []):
            result.add(parent_id)
            result.update(self._ancestor_ids(parent_id, outgoing, {*visited, device_id}))
        return result

    def _descendant_ids(self, device_id: str, incoming: dict[str, list[str]], visited: set[str]) -> set[str]:
        if device_id in visited:
            return set()
        result: set[str] = set()
        for child_id in incoming.get(device_id, []):
            result.add(child_id)
            result.update(self._descendant_ids(child_id, incoming, {*visited, device_id}))
        return result

    def _device_tree_item(
        self,
        device_id: str,
        incoming: dict[str, list[str]],
        display_ids: set[str],
        expanded_groups: set[str],
        visited: set[str],
    ) -> QTreeWidgetItem:
        camera = self.cameras[device_id]
        item = QTreeWidgetItem([self._camera_item_text(camera)])
        item.setData(0, Qt.ItemDataRole.UserRole, camera.id)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, "camera")
        item.setData(0, Qt.ItemDataRole.UserRole + 2, camera.device_kind)
        item.setIcon(0, device_icon(camera.device_kind))
        item.setToolTip(0, self._status_label(self._status_bucket(camera)))
        if device_id in visited:
            return item
        next_visited = {*visited, device_id}
        for child_id in incoming.get(device_id, []):
            if child_id in display_ids:
                item.addChild(self._device_tree_item(child_id, incoming, display_ids, expanded_groups, next_visited))
        item.setExpanded(device_id in expanded_groups)
        return item

    def _request_device_link_from_tree(self, source_device_id: str, target_device_id: str) -> bool:
        if self._device_link_request_handler is not None:
            return bool(self._device_link_request_handler(source_device_id, target_device_id))
        self.device_link_requested.emit(source_device_id, target_device_id)
        return True

    def _request_device_unlink_from_tree(self, source_device_ids: list[str]) -> bool:
        if self._device_unlink_request_handler is not None:
            return bool(self._device_unlink_request_handler(source_device_ids))
        self.device_unlink_requested.emit(source_device_ids)
        return True

    def _has_parent_link(self, device_ids: list[str]) -> bool:
        device_id_set = set(device_ids)
        return any(link.source_device_id in device_id_set for link in self.device_links)

    def _status_bucket(self, camera: Camera) -> bool | None:
        if not camera.ping_enabled or not camera.ip_address:
            return None
        return camera.status

    def _status_group_key(self, status: bool | None) -> str:
        if status is True:
            return "status:online"
        if status is False:
            return "status:offline"
        return "status:unknown"

    def _status_label(self, status: bool | None) -> str:
        if status is True:
            return t("camera_panel.online_group")
        if status is False:
            return t("camera_panel.offline_group")
        return t("camera_panel.unknown_group")

    def _status_filter_key(self, camera: Camera) -> str:
        status = self._status_bucket(camera)
        if status is True:
            return "online"
        if status is False:
            return "offline"
        return "unknown"

    def _status_icon(self, status: bool | None) -> QIcon:
        pixmap = QPixmap(12, 12)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = SUCCESS if status is True else DANGER if status is False else LIGHT_TEXT
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(1, 1, 10, 10)
        painter.end()
        return QIcon(pixmap)

    def _apply_style(self) -> None:
        self.apply_theme(False)

    def apply_theme(self, light_theme: bool) -> None:
        """Apply the shared application palette to the panel."""
        self._icon_color = LIGHT_TEXT if light_theme else TEXT_ON_DARK
        self.setStyleSheet(control_panel_stylesheet(light_theme))
        self._refresh_icons()

    def _icon(self, icon_name: str):
        return tool_icon(icon_name, color=self._icon_color)

    def _refresh_icons(self) -> None:
        for button in self.findChildren(QToolButton):
            icon_name = button.property("icon_name")
            if icon_name:
                button.setIcon(self._icon(str(icon_name)))
