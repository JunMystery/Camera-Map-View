"""Background, grid, and canvas-size helpers for the map canvas."""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPen, QPixmap
from PyQt6.QtWidgets import QGraphicsPixmapItem

from views.layer_state import BACKGROUND_LAYER, GRID_LAYER


class MapCanvasSurface:
    """Manage canvas bounds, background image, and grid layer."""

    def draw_default_grid(self, width: int = 4000, height: int = 3000, grid_size: int = 20) -> None:
        """Draw a default coordinate grid when no map image is loaded."""
        self.grid_size = grid_size
        self.remove_background_item()
        self.remove_grid_items()
        self.background_item = None
        self.background_source_pixmap = None
        self.scene.setSceneRect(0, 0, width, height)
        self._add_grid_items(width, height, grid_size)

    def redraw_grid(self, grid_size: int | None = None) -> None:
        """Redraw the grid layer while preserving all other scene items."""
        self.grid_size = grid_size or self.grid_size
        self.remove_grid_items()
        rect = self.scene.sceneRect()
        self._add_grid_items(int(rect.width()), int(rect.height()), self.grid_size)

    def resize_canvas(self, width: int, height: int) -> None:
        """Resize the usable canvas area."""
        self.scene.setSceneRect(0, 0, width, height)
        self.redraw_grid()

    def set_background_scale(self, scale: float) -> None:
        """Scale the background image layer while preserving annotations."""
        self.background_scale = max(0.1, scale)
        if self.background_item is None or self.background_source_pixmap is None:
            return
        pixmap = self.background_source_pixmap.scaled(
            int(self.background_source_pixmap.width() * self.background_scale),
            int(self.background_source_pixmap.height() * self.background_scale),
        )
        self.background_item.setPixmap(pixmap)
        self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        self.redraw_grid()

    def load_background_image(self, file_path: str) -> bool:
        """Load an image file as the map background."""
        if not os.path.exists(file_path):
            return False
        try:
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                return False
            self.remove_background_item()
            self.background_source_pixmap = pixmap
            scaled = pixmap.scaled(int(pixmap.width() * self.background_scale), int(pixmap.height() * self.background_scale))
            self.background_item = QGraphicsPixmapItem(scaled)
            self.background_item.setData(2, BACKGROUND_LAYER)
            self.background_item.setVisible(self.layer_visibility.get(BACKGROUND_LAYER, True))
            self.scene.addItem(self.background_item)
            self.scene.setSceneRect(0, 0, scaled.width(), scaled.height())
            self.redraw_grid()
            self.apply_layer_z_values()
            self.fit_in_view()
            return True
        except Exception:
            return False

    def _add_grid_items(self, width: int, height: int, grid_size: int) -> None:
        grid_color = QColor("#475569") if self.light_theme else QColor("#94a3b8")
        pen = QPen(grid_color, 1, Qt.PenStyle.DotLine)
        for x in range(0, width, grid_size):
            self.grid_items.append(self.scene.addLine(x, 0, x, height, pen))
        for y in range(0, height, grid_size):
            self.grid_items.append(self.scene.addLine(0, y, width, y, pen))
        border_pen = QPen(QColor("#3b82f6"), 2, Qt.PenStyle.SolidLine)
        self.grid_items.append(self.scene.addRect(0, 0, width, height, border_pen))
        for item in self.grid_items:
            item.setData(2, GRID_LAYER)
        self.set_grid_visible(self.grid_visible)
        self.apply_layer_z_values()
