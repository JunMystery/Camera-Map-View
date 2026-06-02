"""Combined layout and camera control panel."""

from PyQt6.QtCore import QMimeData, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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

    def startDrag(self, supported_actions: Qt.DropAction) -> None:
        item = self.currentItem()
        if item is None:
            return
        if item.data(0, Qt.ItemDataRole.UserRole + 1) != "camera":
            return
        camera_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not camera_id:
            return
        mime_data = QMimeData()
        encoded_id = str(camera_id).encode("utf-8")
        mime_data.setData("application/x-device-id", encoded_id)
        mime_data.setData("application/x-camera-id", encoded_id)
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.setPixmap(self._drag_pixmap(item.text(0), str(item.data(0, Qt.ItemDataRole.UserRole + 2) or "")))
        drag.exec(Qt.DropAction.MoveAction)

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
        self._icon_color = TEXT_ON_DARK
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
        self.refresh_list()

    def add_camera_to_list(self, camera: Camera) -> None:
        """Add a camera to the panel snapshot."""
        self.cameras[camera.id] = camera
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
        expanded_groups = self._expanded_group_keys()
        self.tree_widget.clear()
        visible_devices: dict[str, Camera] = {}
        for camera in self.cameras.values():
            if (camera.id in self.placed_ids) != self.show_placed:
                continue
            if not self._matches_status(camera) or not self._matches(camera, query):
                continue
            visible_devices[camera.id] = camera

        incoming, linked_ids, outgoing_sources = self._incoming_tree(visible_devices)
        root_ids = sorted(
            [device_id for device_id in linked_ids if device_id not in outgoing_sources],
            key=lambda device_id: visible_devices[device_id].name if device_id in visible_devices else device_id,
        )
        for root_id in root_ids:
            if root_id in visible_devices:
                self.tree_widget.addTopLevelItem(self._device_tree_item(root_id, visible_devices, incoming, expanded_groups, set()))

        unlinked_ids = sorted(
            [device_id for device_id in visible_devices if device_id not in linked_ids],
            key=lambda device_id: visible_devices[device_id].name,
        )
        if unlinked_ids:
            group_item = QTreeWidgetItem([f"{t('camera_panel.unlinked_group')} ({len(unlinked_ids)})"])
            group_item.setData(0, Qt.ItemDataRole.UserRole, "group:unlinked")
            self.tree_widget.addTopLevelItem(group_item)
            for device_id in unlinked_ids:
                group_item.addChild(self._device_tree_item(device_id, visible_devices, incoming, expanded_groups, set()))
            group_item.setExpanded("group:unlinked" in expanded_groups or not expanded_groups)

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
        self.tree_widget.setDragEnabled(True)
        self.tree_widget.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
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
        haystack = f"{camera.name} {camera.ip_address} {camera.dvr_origin} {camera.zone} {camera.device_kind} {camera.variant}".lower()
        return not query or query in haystack

    def _matches_status(self, camera: Camera) -> bool:
        bucket = self._status_filter_key(camera)
        return self.status_filter == "all" or self.status_filter == bucket

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

    def _incoming_tree(self, devices: dict[str, Camera]) -> tuple[dict[str, list[str]], set[str], set[str]]:
        incoming: dict[str, list[str]] = {}
        linked_ids: set[str] = set()
        outgoing_sources: set[str] = set()
        for link in self.device_links:
            if link.source_device_id not in devices or link.target_device_id not in devices:
                continue
            incoming.setdefault(link.target_device_id, []).append(link.source_device_id)
            linked_ids.update({link.source_device_id, link.target_device_id})
            outgoing_sources.add(link.source_device_id)
        for sources in incoming.values():
            sources.sort(key=lambda device_id: devices[device_id].name)
        return incoming, linked_ids, outgoing_sources

    def _device_tree_item(
        self,
        device_id: str,
        devices: dict[str, Camera],
        incoming: dict[str, list[str]],
        expanded_groups: set[str],
        visited: set[str],
    ) -> QTreeWidgetItem:
        camera = devices[device_id]
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
            if child_id in devices:
                item.addChild(self._device_tree_item(child_id, devices, incoming, expanded_groups, next_visited))
        item.setExpanded(device_id in expanded_groups or not expanded_groups)
        return item

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
