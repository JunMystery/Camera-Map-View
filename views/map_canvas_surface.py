"""Background, grid, and canvas-size helpers for the map canvas."""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsRectItem

from views.layer_state import BACKGROUND_LAYER, GRID_LAYER
from views.ui_theme import CANVAS_BG_DARK, CANVAS_BG_LIGHT, GRID_DARK, GRID_LIGHT, PRIMARY


class GridLayerItem(QGraphicsRectItem):
    """Single scene item that paints the whole canvas grid."""

    def __init__(self, width: int, height: int, grid_size: int, pen: QPen, border_pen: QPen) -> None:
        super().__init__(0, 0, width, height)
        self.grid_size = max(1, int(grid_size))
        self.grid_pen = QPen(pen)
        self.border_pen = QPen(border_pen)
        self.setPen(self.grid_pen)
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))

    def paint(self, painter: QPainter, option, widget=None) -> None:
        rect = self.rect()
        painter.setPen(self.grid_pen)
        x = 0
        while x <= rect.width():
            painter.drawLine(int(x), 0, int(x), int(rect.height()))
            x += self.grid_size
        y = 0
        while y <= rect.height():
            painter.drawLine(0, int(y), int(rect.width()), int(y))
            y += self.grid_size
        painter.setPen(self.border_pen)
        painter.drawRect(rect)


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
        self._ensure_canvas_bounds(width, height)
        self._add_grid_items(width, height, grid_size)

    def show_blank_canvas(self) -> None:
        """Show an empty workspace when no layout exists."""
        self.remove_background_item()
        self.remove_grid_items()
        self.background_item = None
        self.background_source_pixmap = None
        self.remove_canvas_bounds_item()
        self.scene.setSceneRect(0, 0, 0, 0)

    def redraw_grid(self, grid_size: int | None = None) -> None:
        """Redraw the grid layer while preserving all other scene items."""
        self.grid_size = grid_size or self.grid_size
        self.remove_grid_items()
        rect = self.scene.sceneRect()
        self._ensure_canvas_bounds(int(rect.width()), int(rect.height()))
        self._add_grid_items(int(rect.width()), int(rect.height()), self.grid_size)

    def resize_canvas(self, width: int, height: int) -> None:
        """Resize the usable canvas area."""
        self.scene.setSceneRect(0, 0, width, height)
        self._ensure_canvas_bounds(width, height)
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
        self._ensure_canvas_bounds(pixmap.width(), pixmap.height())
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
            self.background_item.setVisible(self.background_map_visible and self.layer_visibility.get(BACKGROUND_LAYER, True))
            self.scene.addItem(self.background_item)
            self.scene.setSceneRect(0, 0, scaled.width(), scaled.height())
            self._ensure_canvas_bounds(scaled.width(), scaled.height())
            self.redraw_grid()
            self.apply_layer_z_values()
            self.fit_in_view()
            return True
        except Exception:
            return False

    def _add_grid_items(self, width: int, height: int, grid_size: int) -> None:
        grid_color = QColor(GRID_LIGHT) if self.light_theme else QColor(GRID_DARK)
        pen = QPen(grid_color, 1, Qt.PenStyle.DotLine)
        border_pen = QPen(QColor(PRIMARY), 2, Qt.PenStyle.SolidLine)
        self.grid_items.append(GridLayerItem(width, height, grid_size, pen, border_pen))
        for item in self.grid_items:
            item.setData(2, GRID_LAYER)
            item.setVisible(self.grid_visible)
            self.scene.addItem(item)
        self.apply_layer_z_values()

    def remove_canvas_bounds_item(self) -> None:
        """Remove the persistent canvas edit-area marker."""
        if getattr(self, "canvas_bounds_item", None) is not None:
            self.scene.removeItem(self.canvas_bounds_item)
            self.canvas_bounds_item = None

    def _ensure_canvas_bounds(self, width: int, height: int) -> None:
        """Draw a theme-aware canvas edit boundary independent from grid lines."""
        if width <= 0 or height <= 0:
            self.remove_canvas_bounds_item()
            return
        if getattr(self, "canvas_bounds_item", None) is None:
            self.canvas_bounds_item = QGraphicsRectItem()
            self.canvas_bounds_item.setData(1, "canvas_bounds")
            self.canvas_bounds_item.setZValue(-25)
            self.scene.addItem(self.canvas_bounds_item)
        fill = QColor(CANVAS_BG_LIGHT if self.light_theme else CANVAS_BG_DARK)
        fill.setAlpha(12 if self.light_theme else 16)
        border = QColor("#2563eb" if self.light_theme else "#93c5fd")
        self.canvas_bounds_item.setRect(0, 0, width, height)
        self.canvas_bounds_item.setBrush(QBrush(fill))
        self.canvas_bounds_item.setPen(QPen(border, 2.0, Qt.PenStyle.SolidLine))
        self.canvas_bounds_item.setVisible(True)
