"""Combined layout and camera control panel."""

from PyQt6.QtCore import QMimeData, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.i18n import t
from models.camera_data_model import Camera
from models.map_layout_model import MapLayout
from views.tool_icons import tool_icon
from views.ui_theme import PRIMARY, TEXT_WHITE, control_panel_stylesheet


class CameraTreeWidget(QTreeWidget):
    """Tree widget that drags child camera ids onto the map canvas."""

    def startDrag(self, supported_actions: Qt.DropAction) -> None:
        item = self.currentItem()
        if item is None or item.childCount() > 0:
            return
        camera_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not camera_id:
            return
        mime_data = QMimeData()
        mime_data.setData("application/x-camera-id", str(camera_id).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.setPixmap(self._drag_pixmap(item.text(0)))
        drag.exec(Qt.DropAction.MoveAction)

    def _drag_pixmap(self, label: str) -> QPixmap:
        pixmap = QPixmap(150, 32)
        pixmap.fill(QColor(PRIMARY))
        painter = QPainter(pixmap)
        painter.setPen(QColor(TEXT_WHITE))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, label)
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

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("controlLayoutPanel")
        self.cameras: dict[str, Camera] = {}
        self.placed_ids: set[str] = set()
        self.show_placed = False
        self.layouts: list[MapLayout] = []
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
        return str(self.layout_combo.currentData() or "default")

    def set_cameras(self, cameras: list[Camera], placed_ids: set[str]) -> None:
        """Replace the camera snapshot and refresh the tree."""
        self.cameras = {camera.id: camera for camera in cameras}
        self.placed_ids = placed_ids
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
        groups: dict[str, list[Camera]] = {}
        for camera in self.cameras.values():
            if (camera.id in self.placed_ids) != self.show_placed or not self._matches(camera, query):
                continue
            group_key = camera.dvr_origin or t("camera_panel.no_dvr")
            groups.setdefault(group_key, []).append(camera)
        for dvr_name, cameras in sorted(groups.items()):
            group_item = QTreeWidgetItem([f"{dvr_name} ({len(cameras)})"])
            group_item.setData(0, Qt.ItemDataRole.UserRole, dvr_name)
            self.tree_widget.addTopLevelItem(group_item)
            for camera in sorted(cameras, key=lambda item: item.name):
                child = QTreeWidgetItem([self._camera_item_text(camera)])
                child.setData(0, Qt.ItemDataRole.UserRole, camera.id)
                group_item.addChild(child)
            group_item.setExpanded(dvr_name in expanded_groups)

    def retranslate(self) -> None:
        """Refresh labels and tooltips."""
        self.layout_title.setText(t("dock.layouts"))
        self.camera_title.setText(t("dock.control_panel"))
        self.search_input.setPlaceholderText(t("camera_panel.search"))
        self.unplaced_button.setToolTip(t("camera_panel.unplaced"))
        self.placed_button.setToolTip(t("camera_panel.placed"))
        self.add_layout_button.setToolTip(t("layout.add"))
        self.rename_layout_button.setToolTip(t("layout.rename"))
        self.delete_layout_button.setToolTip(t("layout.delete"))
        self.add_button.setToolTip(t("camera_panel.add"))
        self.edit_button.setToolTip(t("camera_panel.edit"))
        self.delete_button.setToolTip(t("camera_panel.delete"))
        self.import_button.setToolTip(t("camera_panel.import"))
        self.export_button.setToolTip(t("camera_panel.export"))
        self._sync_mode_buttons()
        self.refresh_list()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.layout_title = QLabel(self)
        self.layout_title.setObjectName("sectionTitle")
        layout.addWidget(self.layout_title)

        layout_row = QHBoxLayout()
        self.layout_combo = QComboBox(self)
        self.layout_combo.currentIndexChanged.connect(self._emit_selected_layout)
        layout_row.addWidget(self.layout_combo, 1)
        self.add_layout_button = self._tool_button("add_layout")
        self.rename_layout_button = self._tool_button("rename")
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

        mode_row = QHBoxLayout()
        self.unplaced_button = self._mode_button("camera")
        self.placed_button = self._mode_button("check")
        self.unplaced_button.clicked.connect(lambda: self._set_mode(False))
        self.placed_button.clicked.connect(lambda: self._set_mode(True))
        mode_row.addWidget(self.unplaced_button)
        mode_row.addWidget(self.placed_button)
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
        self.edit_button = self._tool_button("edit")
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
        button.setIcon(tool_icon(icon_name))
        button.setIconSize(QSize(22, 22))
        button.setFixedSize(32, 30)
        return button

    def _mode_button(self, icon_name: str) -> QToolButton:
        button = self._tool_button(icon_name)
        button.setCheckable(True)
        button.setFixedHeight(34)
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
        if item is not None and item.childCount() == 0:
            signal.emit(item.data(0, Qt.ItemDataRole.UserRole))

    def _set_mode(self, show_placed: bool) -> None:
        self.show_placed = show_placed
        self._sync_mode_buttons()
        self.refresh_list()

    def _sync_mode_buttons(self) -> None:
        self.unplaced_button.setChecked(not self.show_placed)
        self.placed_button.setChecked(self.show_placed)

    def _matches(self, camera: Camera, query: str) -> bool:
        haystack = f"{camera.name} {camera.ip_address} {camera.dvr_origin} {camera.zone}".lower()
        return not query or query in haystack

    def _camera_item_text(self, camera: Camera) -> str:
        return t("camera_panel.item", name=camera.name, ip_address=camera.ip_address)

    def _expanded_group_keys(self) -> set[str]:
        groups: set[str] = set()
        for index in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(index)
            if item.isExpanded():
                groups.add(str(item.data(0, Qt.ItemDataRole.UserRole)))
        return groups

    def _apply_style(self) -> None:
        self.setStyleSheet(control_panel_stylesheet())
