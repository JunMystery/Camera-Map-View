"""Drawing mode helpers for map annotations."""

import uuid
from enum import Enum

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainterPath, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsTextItem,
)

from models.drawing_shape_model import DrawingShape
from views.ui_theme import DANGER

TEXT_DEFAULT_FONT_SIZE = 18


class DrawingMode(str, Enum):
    """Available canvas interaction modes."""

    PAN = "pan"
    SELECT = "select"
    LINE = "line"
    RECTANGLE = "rectangle"
    ZONE = "zone"
    FREEHAND = "freehand"


class DrawingTool:
    """Create drawing shapes and their QGraphicsItems."""

    def __init__(self, snap_callback) -> None:
        self.snap_callback = snap_callback

    def shape_from_points(
        self,
        mode: DrawingMode,
        start_pos: QPointF,
        end_pos: QPointF,
        color: str = DANGER,
    ) -> DrawingShape | None:
        """Create a shape model from two scene positions."""
        start_x, start_y = self.snap_callback(start_pos.x(), start_pos.y())
        end_x, end_y = self.snap_callback(end_pos.x(), end_pos.y())
        if start_x == end_x and start_y == end_y:
            return None

        shape_id = f"shape_{uuid.uuid4().hex}"
        if mode == DrawingMode.LINE:
            return DrawingShape(shape_id, "Line", [start_x, start_y, end_x, end_y], color=color)

        if mode == DrawingMode.RECTANGLE:
            return DrawingShape(shape_id, "Rectangle", [start_x, start_y, end_x, end_y], color=color)

        if mode == DrawingMode.ZONE:
            points = [start_x, start_y, end_x, start_y, end_x, end_y, start_x, end_y]
            return DrawingShape(shape_id, "Polygon", points, color=color)

        return None

    def freehand_shape(self, points: list[QPointF], color: str) -> DrawingShape | None:
        """Create a freehand polyline from sampled scene positions."""
        flat_points: list[float] = []
        for point in points:
            x, y = self.snap_callback(point.x(), point.y())
            if not flat_points or flat_points[-2:] != [x, y]:
                flat_points.extend([x, y])
        if len(flat_points) < 4:
            return None
        return DrawingShape(f"shape_{uuid.uuid4().hex}", "Freehand", flat_points, color=color)

    def text_shape(self, position: QPointF, text: str, color: str, font_size: int = TEXT_DEFAULT_FONT_SIZE) -> DrawingShape:
        """Create a text annotation at a scene position."""
        x, y = self.snap_callback(position.x(), position.y())
        return DrawingShape(f"shape_{uuid.uuid4().hex}", "Text", [x, y], color=color, line_thickness=font_size, label=text)

    def image_shape(self, position: QPointF, image_path: str, width: float, height: float) -> DrawingShape:
        """Create an image annotation at a scene position."""
        x, y = self.snap_callback(position.x(), position.y())
        return DrawingShape(f"shape_{uuid.uuid4().hex}", "Image", [x, y, width, height], image_path=image_path)

    def item_from_shape(self, shape: DrawingShape | None) -> QGraphicsItem | None:
        """Create a graphics item from a drawing shape."""
        if shape is None:
            return None

        pen = QPen(QColor(shape.color), shape.line_thickness, Qt.PenStyle.SolidLine)
        if shape.shape_type == "Line" and len(shape.points) >= 4:
            item = QGraphicsLineItem(shape.points[0], shape.points[1], shape.points[2], shape.points[3])
            item.setPen(pen)
            return item

        if shape.shape_type == "Rectangle" and len(shape.points) >= 4:
            x1, y1, x2, y2 = shape.points[:4]
            item = QGraphicsRectItem(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            item.setPen(pen)
            return item

        if shape.shape_type == "Polygon" and len(shape.points) >= 6:
            polygon = QPolygonF(
                [
                    QPointF(shape.points[index], shape.points[index + 1])
                    for index in range(0, len(shape.points), 2)
                ]
            )
            item = QGraphicsPolygonItem(polygon)
            item.setPen(pen)
            return item

        if shape.shape_type == "Freehand" and len(shape.points) >= 4:
            path = QPainterPath(QPointF(shape.points[0], shape.points[1]))
            for index in range(2, len(shape.points), 2):
                path.lineTo(shape.points[index], shape.points[index + 1])
            item = QGraphicsPathItem(path)
            item.setPen(pen)
            return item

        if shape.shape_type == "Text" and len(shape.points) >= 2:
            item = QGraphicsTextItem(shape.label)
            font = item.font()
            font.setPointSize(self._text_font_size(shape.line_thickness))
            item.setFont(font)
            item.setDefaultTextColor(QColor(shape.color))
            item.setPos(shape.points[0], shape.points[1])
            return item

        if shape.shape_type == "Image" and len(shape.points) >= 4 and shape.image_path:
            pixmap = QPixmap(shape.image_path)
            if pixmap.isNull():
                return None
            item = QGraphicsPixmapItem(pixmap.scaled(int(shape.points[2]), int(shape.points[3])))
            item.setPos(shape.points[0], shape.points[1])
            return item

        return None

    def _text_font_size(self, line_thickness: int) -> int:
        return TEXT_DEFAULT_FONT_SIZE if line_thickness <= 2 else line_thickness
