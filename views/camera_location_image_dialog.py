"""Dialog for viewing a camera location photo with pan and zoom controls."""

from pathlib import Path
from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config.i18n import t


class CameraLocationImageView(QGraphicsView):
    """Image viewport that zooms with the mouse wheel and pans with left drag."""

    def __init__(self, scene: QGraphicsScene, zoom_callback: Callable[[float], None], parent: QWidget | None = None) -> None:
        super().__init__(scene, parent)
        self.zoom_callback = zoom_callback
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def wheelEvent(self, event: Any) -> None:
        """Zoom in or out around the cursor position."""
        delta = event.angleDelta().y()
        if delta == 0:
            event.accept()
            return
        self.zoom_callback(1.25 if delta > 0 else 0.8)
        event.accept()


class CameraLocationImageDialog(QDialog):
    """Show one persisted camera location photo with basic viewport controls."""

    def __init__(self, image_path: str, camera_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.image_path = image_path
        self.camera_name = camera_name
        self.zoom_factor = 1.0

        self.setModal(True)
        self.resize(720, 520)
        self.setWindowTitle(t("camera_location_image.title", name=camera_name))

        self.scene = QGraphicsScene(self)
        self.view = CameraLocationImageView(self.scene, self._scale_view, self)
        self.view.setRenderHints(self.view.renderHints())
        self.pixmap_item: QGraphicsPixmapItem | None = None

        self.zoom_in_button = QPushButton(t("camera_location_image.zoom_in"), self)
        self.zoom_out_button = QPushButton(t("camera_location_image.zoom_out"), self)
        self.fit_button = QPushButton(t("camera_location_image.fit"), self)
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.fit_button.clicked.connect(self.fit_to_window)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)

        controls = QHBoxLayout()
        controls.addWidget(self.zoom_in_button)
        controls.addWidget(self.zoom_out_button)
        controls.addWidget(self.fit_button)
        controls.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(controls)
        layout.addWidget(self.view)
        layout.addWidget(buttons)
        self._load_image()

    def zoom_in(self) -> None:
        """Increase the viewport zoom."""
        self._scale_view(1.25)

    def zoom_out(self) -> None:
        """Decrease the viewport zoom."""
        self._scale_view(0.8)

    def fit_to_window(self) -> None:
        """Fit the full image inside the current view."""
        if self.pixmap_item is None:
            return
        self.view.resetTransform()
        self.view.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self.zoom_factor = self.view.transform().m11()

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        self.fit_to_window()

    def _load_image(self) -> None:
        if not Path(self.image_path).exists():
            QMessageBox.warning(self, t("error.location_image_missing.title"), t("error.location_image_missing.body"))
            return
        pixmap = QPixmap(self.image_path)
        if pixmap.isNull():
            QMessageBox.warning(self, t("error.location_image_missing.title"), t("error.location_image_missing.body"))
            return
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(self.pixmap_item.boundingRect())

    def _scale_view(self, factor: float) -> None:
        next_zoom = self.zoom_factor * factor
        if not 0.1 <= next_zoom <= 8.0:
            return
        self.view.scale(factor, factor)
        self.zoom_factor = next_zoom
