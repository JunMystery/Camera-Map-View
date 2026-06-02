"""Sidebar camera manager with search, placed toggle, and DVR grouping."""

from PyQt6.QtCore import QMimeData, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.i18n import t
from models.camera_data_model import Camera


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
        pixmap = QPixmap(140, 30)
        pixmap.fill(QColor(59, 130, 246, 180))
        painter = QPainter(pixmap)
        painter.setPen(QColor("white"))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, label)
        painter.end()
        return pixmap


class CameraPanel(QWidget):
    """Show and manage placed or unplaced cameras grouped by DVR."""

    camera_add_requested = pyqtSignal()
    camera_edit_requested = pyqtSignal(str)
    camera_delete_requested = pyqtSignal(str)
    camera_import_requested = pyqtSignal()
    camera_export_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cameras: dict[str, Camera] = {}
        self.placed_ids: set[str] = set()
        self.show_placed = False
        self._build_ui()
        self.retranslate()

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
        """Rebuild tree groups from search and placement filters."""
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
        """Refresh visible text for the active language."""
        self.title_label.setText(t("camera_panel.title_placed" if self.show_placed else "camera_panel.title_unplaced"))
        self.search_input.setPlaceholderText(t("camera_panel.search"))
        self.unplaced_button.setText(t("camera_panel.unplaced"))
        self.placed_button.setText(t("camera_panel.placed"))
        self.add_button.setText(t("camera_panel.add"))
        self.edit_button.setText(t("camera_panel.edit"))
        self.delete_button.setText(t("camera_panel.delete"))
        self.import_button.setText(t("camera_panel.import"))
        self.export_button.setText(t("camera_panel.export"))
        self.refresh_list()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        self.title_label = QLabel(self)
        layout.addWidget(self.title_label)
        self.search_input = QLineEdit(self)
        self.search_input.textChanged.connect(self.refresh_list)
        layout.addWidget(self.search_input)
        mode_row = QHBoxLayout()
        self.unplaced_button = QPushButton(self)
        self.placed_button = QPushButton(self)
        self.unplaced_button.clicked.connect(lambda: self._set_mode(False))
        self.placed_button.clicked.connect(lambda: self._set_mode(True))
        mode_row.addWidget(self.unplaced_button)
        mode_row.addWidget(self.placed_button)
        layout.addLayout(mode_row)
        self.tree_widget = CameraTreeWidget(self)
        self.tree_widget.setDragEnabled(True)
        self.tree_widget.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        layout.addWidget(self.tree_widget)
        self._add_action_buttons(layout)

    def _add_action_buttons(self, layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        self.add_button = QPushButton(self)
        self.edit_button = QPushButton(self)
        self.delete_button = QPushButton(self)
        self.import_button = QPushButton(self)
        self.export_button = QPushButton(self)
        self.add_button.clicked.connect(self.camera_add_requested.emit)
        self.edit_button.clicked.connect(lambda: self._emit_selected(self.camera_edit_requested))
        self.delete_button.clicked.connect(lambda: self._emit_selected(self.camera_delete_requested))
        self.import_button.clicked.connect(self.camera_import_requested.emit)
        self.export_button.clicked.connect(self.camera_export_requested.emit)
        for button in [self.add_button, self.edit_button, self.delete_button, self.import_button, self.export_button]:
            row.addWidget(button)
        layout.addLayout(row)

    def _emit_selected(self, signal) -> None:
        item = self.tree_widget.currentItem()
        if item is not None and item.childCount() == 0:
            signal.emit(item.data(0, Qt.ItemDataRole.UserRole))

    def _set_mode(self, show_placed: bool) -> None:
        self.show_placed = show_placed
        self.retranslate()

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
