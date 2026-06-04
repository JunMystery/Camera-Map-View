"""Drawing mode helpers for map annotations."""

import uuid
from enum import Enum
import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QPainterPath, QPainterPathStroker, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
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
STROKE_HIT_PADDING = 8.0
TRANSFORM_HANDLE_COLOR = "#facc15"
TRANSFORM_MIN_SIZE = 16.0


def _stroke_shape(path: QPainterPath, pen: QPen) -> QPainterPath:
    stroker = QPainterPathStroker()
    stroker.setWidth(max(float(pen.widthF()), float(pen.width())) + STROKE_HIT_PADDING)
    return stroker.createStroke(path)


class SelectableLineItem(QGraphicsLineItem):
    """Line item selected only through its visible stroke."""

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.moveTo(self.line().p1())
        path.lineTo(self.line().p2())
        return _stroke_shape(path, self.pen())


class SelectablePathItem(QGraphicsPathItem):
    """Path item selected only through its visible stroke."""

    def shape(self) -> QPainterPath:
        return _stroke_shape(self.path(), self.pen())


class SelectableRectItem(QGraphicsRectItem):
    """Rectangle item selected only through its border."""

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRect(self.rect())
        return _stroke_shape(path, self.pen())


class SelectablePolygonItem(QGraphicsPolygonItem):
    """Polygon item selected only through its border."""

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addPolygon(self.polygon())
        path.closeSubpath()
        return _stroke_shape(path, self.pen())


class TransformHandleMixin:
    """Shared resize and rotation handles for drawable annotations."""

    handle_size = 10.0

    def _content_rect(self) -> QRectF:
        raise NotImplementedError

    def _set_content_rect(self, rect: QRectF, keep_aspect: bool = False) -> None:
        raise NotImplementedError

    def _extra_bounds(self) -> QRectF:
        return self._content_rect().adjusted(-18, -38, 18, 18)

    def _transform_shape(self, base_shape: QPainterPath) -> QPainterPath:
        if self.isSelected():
            for handle_name in self._resize_handle_names():
                base_shape.addRect(self._resize_handle_rect(handle_name))
            base_shape.addEllipse(self._rotation_handle_rect())
        return base_shape

    def _paint_transform_handles(self, painter) -> None:
        if not self.isSelected():
            return
        rect = self._content_rect()
        rotate_handle = self._rotation_handle_rect()
        painter.setPen(QPen(QColor(TRANSFORM_HANDLE_COLOR), 1.5))
        painter.setBrush(QBrush(QColor(TRANSFORM_HANDLE_COLOR)))
        painter.drawLine(rect.center(), rotate_handle.center())
        painter.drawEllipse(rotate_handle)
        for handle_name in self._resize_handle_names():
            painter.drawRect(self._resize_handle_rect(handle_name))

    def _handle_mouse_press(self, event) -> bool:
        if not self._allows_transform() or event.button() != Qt.MouseButton.LeftButton or not self.isSelected():
            return False
        handle_name = self._handle_at(event.pos())
        if handle_name:
            self.is_resizing = True
            self.resize_handle = handle_name
            self.resize_start_rect = QRectF(self._content_rect())
            self.resize_start_scene_transform_inverted = self.sceneTransform().inverted()[0]
            self.resize_start_pos = self.resize_start_scene_transform_inverted.map(event.scenePos())
            self.resize_start_size = (self.resize_start_rect.width(), self.resize_start_rect.height())
            self.setCursor(self._cursor_for_handle(handle_name))
            event.accept()
            return True
        if self._rotation_handle_rect().contains(event.pos()):
            self.is_rotating = True
            self.rotation_start_value = self.rotation()
            self.rotation_start_center = self.mapToScene(self._content_rect().center())
            start_angle = self._scene_angle(event.scenePos(), self.rotation_start_center)
            self.rotation_start_offset = self.rotation_start_value - start_angle
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            event.accept()
            return True
        return False

    def _handle_mouse_move(self, event, keep_corner_ratio: bool = False) -> bool:
        if getattr(self, "is_resizing", False):
            self._resize_from_event(event, keep_corner_ratio)
            event.accept()
            return True
        if getattr(self, "is_rotating", False):
            center = getattr(self, "rotation_start_center", self.mapToScene(self._content_rect().center()))
            angle = (self._scene_angle(event.scenePos(), center) + getattr(self, "rotation_start_offset", 0.0)) % 360
            self.setTransformOriginPoint(self._content_rect().center())
            self.setRotation(angle)
            event.accept()
            return True
        return False

    def _handle_mouse_release(self, event) -> bool:
        if getattr(self, "is_resizing", False) and event.button() == Qt.MouseButton.LeftButton:
            self.is_resizing = False
            self.unsetCursor()
            event.accept()
            return True
        if getattr(self, "is_rotating", False) and event.button() == Qt.MouseButton.LeftButton:
            self.is_rotating = False
            self.unsetCursor()
            event.accept()
            return True
        return False

    def cancel_interaction(self) -> bool:
        """Cancel a shape transform."""
        if getattr(self, "is_resizing", False):
            self.is_resizing = False
            self._set_content_rect(QRectF(self.resize_start_rect))
            self.unsetCursor()
            return True
        if getattr(self, "is_rotating", False):
            self.is_rotating = False
            self.setRotation(self.rotation_start_value)
            self.unsetCursor()
            return True
        return False

    def _resize_from_event(self, event, keep_corner_ratio: bool) -> None:
        current = self._snap_local_pos(event.scenePos())
        delta = current - self.resize_start_pos
        rect = QRectF(self.resize_start_rect)
        handle = self.resize_handle
        if "w" in handle:
            rect.setLeft(rect.left() + delta.x())
        if "e" in handle:
            rect.setRight(rect.right() + delta.x())
        if "n" in handle:
            rect.setTop(rect.top() + delta.y())
        if "s" in handle:
            rect.setBottom(rect.bottom() + delta.y())
        rect = rect.normalized()
        if keep_corner_ratio and len(handle) == 2:
            rect = self._ratio_rect(rect, handle)
        if rect.width() < TRANSFORM_MIN_SIZE:
            rect.setWidth(TRANSFORM_MIN_SIZE)
        if rect.height() < TRANSFORM_MIN_SIZE:
            rect.setHeight(TRANSFORM_MIN_SIZE)
        self._set_content_rect(rect, keep_corner_ratio and len(handle) == 2)

    def _ratio_rect(self, rect: QRectF, handle: str) -> QRectF:
        start_width, start_height = self.resize_start_size
        ratio = start_width / start_height if start_height else 1.0
        width = rect.width()
        height = width / ratio if ratio else rect.height()
        if height < TRANSFORM_MIN_SIZE:
            height = TRANSFORM_MIN_SIZE
            width = height * ratio
        adjusted = QRectF(rect)
        if "n" in handle:
            adjusted.setTop(adjusted.bottom() - height)
        else:
            adjusted.setBottom(adjusted.top() + height)
        if "w" in handle:
            adjusted.setLeft(adjusted.right() - width)
        else:
            adjusted.setRight(adjusted.left() + width)
        return adjusted.normalized()

    def _resize_handle_names(self) -> tuple[str, ...]:
        return ("nw", "n", "ne", "e", "se", "s", "sw", "w")

    def _resize_handle_rect(self, name: str) -> QRectF:
        rect = self._content_rect()
        points = {
            "nw": rect.topLeft(),
            "n": QPointF(rect.center().x(), rect.top()),
            "ne": rect.topRight(),
            "e": QPointF(rect.right(), rect.center().y()),
            "se": rect.bottomRight(),
            "s": QPointF(rect.center().x(), rect.bottom()),
            "sw": rect.bottomLeft(),
            "w": QPointF(rect.left(), rect.center().y()),
        }
        return self._handle_rect(points[name])

    def _rotation_handle_rect(self) -> QRectF:
        rect = self._content_rect()
        return self._handle_rect(QPointF(rect.center().x(), rect.top() - 26))

    def _handle_rect(self, center: QPointF) -> QRectF:
        half = self.handle_size / 2
        return QRectF(center.x() - half, center.y() - half, self.handle_size, self.handle_size)

    def _handle_at(self, point: QPointF) -> str:
        for handle_name in self._resize_handle_names():
            if self._resize_handle_rect(handle_name).contains(point):
                return handle_name
        return ""

    def _cursor_for_handle(self, handle: str) -> Qt.CursorShape:
        if handle in {"n", "s"}:
            return Qt.CursorShape.SizeVerCursor
        if handle in {"e", "w"}:
            return Qt.CursorShape.SizeHorCursor
        if handle in {"nw", "se"}:
            return Qt.CursorShape.SizeFDiagCursor
        return Qt.CursorShape.SizeBDiagCursor

    def _snap_local_pos(self, scene_pos: QPointF) -> QPointF:
        snapped = scene_pos
        if self.scene() is not None and self.scene().views():
            view = self.scene().views()[0]
            snap = getattr(view, "snap_point", None)
            active = getattr(view, "is_snap_modifier_active", None)
            if callable(snap) and callable(active) and active():
                x, y = snap(scene_pos.x(), scene_pos.y(), force=True)
                snapped = QPointF(x, y)
        start_transform = getattr(self, "resize_start_scene_transform_inverted", None)
        if start_transform is not None:
            return start_transform.map(snapped)
        return self.mapFromScene(snapped)

    def _scene_angle(self, scene_pos: QPointF, center: QPointF) -> float:
        return math.degrees(math.atan2(scene_pos.y() - center.y(), scene_pos.x() - center.x())) % 360

    def _allows_transform(self) -> bool:
        if self.scene() is None or not self.scene().views():
            return True
        view = self.scene().views()[0]
        return getattr(view, "drawing_mode", DrawingMode.SELECT) == DrawingMode.SELECT


class TransformableRectItem(TransformHandleMixin, SelectableRectItem):
    """Rectangle item with resize/rotation handles."""

    def __init__(self, rect: QRectF) -> None:
        super().__init__(rect)
        self.is_resizing = False
        self.is_rotating = False

    def boundingRect(self) -> QRectF:
        return self._extra_bounds()

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRect(self.rect())
        return self._transform_shape(_stroke_shape(path, self.pen()))

    def paint(self, painter, option, widget=None) -> None:
        super().paint(painter, option, widget)
        self._paint_transform_handles(painter)

    def mousePressEvent(self, event) -> None:
        if self._handle_mouse_press(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._handle_mouse_move(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._handle_mouse_release(event):
            return
        super().mouseReleaseEvent(event)

    def _content_rect(self) -> QRectF:
        return self.rect()

    def _set_content_rect(self, rect: QRectF, keep_aspect: bool = False) -> None:
        self.prepareGeometryChange()
        self.setRect(rect)
        self.setTransformOriginPoint(rect.center())


class TransformableRoundedRectItem(TransformableRectItem):
    """Rounded rectangle item with resize/rotation handles."""

    def paint(self, painter, option, widget=None) -> None:
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawRoundedRect(self.rect(), 10, 10)
        self._paint_transform_handles(painter)


class TransformableEllipseItem(TransformHandleMixin, QGraphicsEllipseItem):
    """Ellipse item with resize/rotation handles."""

    def __init__(self, rect: QRectF) -> None:
        super().__init__(rect)
        self.is_resizing = False
        self.is_rotating = False

    def boundingRect(self) -> QRectF:
        return self._extra_bounds()

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addEllipse(self.rect())
        return self._transform_shape(_stroke_shape(path, self.pen()))

    def paint(self, painter, option, widget=None) -> None:
        super().paint(painter, option, widget)
        self._paint_transform_handles(painter)

    def mousePressEvent(self, event) -> None:
        if self._handle_mouse_press(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._handle_mouse_move(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._handle_mouse_release(event):
            return
        super().mouseReleaseEvent(event)

    def _content_rect(self) -> QRectF:
        return self.rect()

    def _set_content_rect(self, rect: QRectF, keep_aspect: bool = False) -> None:
        self.prepareGeometryChange()
        self.setRect(rect)
        self.setTransformOriginPoint(rect.center())


class TransformablePolygonItem(TransformHandleMixin, SelectablePolygonItem):
    """Polygon item with resize/rotation handles."""

    def __init__(self, polygon: QPolygonF) -> None:
        super().__init__(polygon)
        self.is_resizing = False
        self.is_rotating = False
        self.resize_start_polygon = QPolygonF(polygon)

    def boundingRect(self) -> QRectF:
        return self._extra_bounds()

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addPolygon(self.polygon())
        path.closeSubpath()
        return self._transform_shape(_stroke_shape(path, self.pen()))

    def paint(self, painter, option, widget=None) -> None:
        super().paint(painter, option, widget)
        self._paint_transform_handles(painter)

    def mousePressEvent(self, event) -> None:
        self.resize_start_polygon = QPolygonF(self.polygon())
        if self._handle_mouse_press(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._handle_mouse_move(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._handle_mouse_release(event):
            return
        super().mouseReleaseEvent(event)

    def cancel_interaction(self) -> bool:
        if getattr(self, "is_resizing", False):
            self.is_resizing = False
            self.setPolygon(QPolygonF(self.resize_start_polygon))
            self.unsetCursor()
            return True
        return TransformHandleMixin.cancel_interaction(self)

    def _content_rect(self) -> QRectF:
        return self.polygon().boundingRect()

    def _set_content_rect(self, rect: QRectF, keep_aspect: bool = False) -> None:
        self.prepareGeometryChange()
        start_rect = self.resize_start_rect
        if start_rect.width() == 0 or start_rect.height() == 0:
            return
        scaled = QPolygonF()
        for point in self.resize_start_polygon:
            nx = (point.x() - start_rect.left()) / start_rect.width()
            ny = (point.y() - start_rect.top()) / start_rect.height()
            scaled.append(QPointF(rect.left() + nx * rect.width(), rect.top() + ny * rect.height()))
        self.setPolygon(scaled)
        self.setTransformOriginPoint(rect.center())


class TransformableTextItem(QGraphicsTextItem):
    """Text annotation with simple resize and rotation handles."""

    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.is_resizing = False
        self.is_rotating = False
        self.resize_start_distance = 1.0
        self.resize_start_font_size = TEXT_DEFAULT_FONT_SIZE
        self.rotation_start_value = 0.0
        self.min_font_size = 8
        self.max_font_size = 96

    def boundingRect(self):
        return super().boundingRect().adjusted(-16, -34, 16, 16)

    def shape(self) -> QPainterPath:
        path = super().shape()
        if self.isSelected():
            path.addRect(self._resize_handle_rect())
            path.addEllipse(self._rotation_handle_rect())
        return path

    def paint(self, painter, option, widget=None) -> None:
        super().paint(painter, option, widget)
        if not self.isSelected():
            return
        rect = self._content_rect()
        painter.setPen(QPen(QColor(TRANSFORM_HANDLE_COLOR), 1.5))
        painter.setBrush(QBrush(QColor(TRANSFORM_HANDLE_COLOR)))
        handle = self._rotation_handle_rect()
        painter.drawLine(rect.center(), handle.center())
        painter.drawEllipse(handle)
        painter.drawRect(self._resize_handle_rect())

    def mousePressEvent(self, event) -> None:
        if not self._allows_transform() or event.button() != Qt.MouseButton.LeftButton or not self.isSelected():
            super().mousePressEvent(event)
            return
        if self._resize_handle_rect().contains(event.pos()):
            self.is_resizing = True
            self.resize_start_distance = max(self._scene_distance_from_center(event), 1.0)
            self.resize_start_font_size = self._font_size()
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            event.accept()
            return
        if self._rotation_handle_rect().contains(event.pos()):
            self.is_rotating = True
            self.rotation_start_value = self.rotation()
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            self._apply_rotation_from_point(event.pos())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self.is_resizing:
            ratio = max(self._scene_distance_from_center(event), 1.0) / self.resize_start_distance
            self._set_font_size(round(self.resize_start_font_size * ratio))
            event.accept()
            return
        if self.is_rotating:
            self._apply_rotation_from_point(event.pos())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self.is_resizing and event.button() == Qt.MouseButton.LeftButton:
            self.is_resizing = False
            self.unsetCursor()
            event.accept()
            return
        if self.is_rotating and event.button() == Qt.MouseButton.LeftButton:
            self.is_rotating = False
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def cancel_interaction(self) -> bool:
        """Cancel an in-progress text transform."""
        if self.is_resizing:
            self.is_resizing = False
            self._set_font_size(self.resize_start_font_size)
            self.unsetCursor()
            return True
        if self.is_rotating:
            self.is_rotating = False
            self.setRotation(self.rotation_start_value)
            self.unsetCursor()
            return True
        return False

    def _content_rect(self):
        return super().boundingRect()

    def _resize_handle_rect(self):
        rect = self._content_rect()
        return rect.adjusted(rect.width() - 10, rect.height() - 10, 0, 0)

    def _rotation_handle_rect(self):
        center = self._content_rect().center()
        return self._handle_rect(QPointF(center.x(), self._content_rect().top() - 24))

    def _handle_rect(self, center: QPointF):
        return self._content_rect().__class__(center.x() - 6, center.y() - 6, 12, 12)

    def _font_size(self) -> int:
        size = self.font().pointSize()
        return TEXT_DEFAULT_FONT_SIZE if size <= 0 else size

    def _set_font_size(self, size: int) -> None:
        font = self.font()
        font.setPointSize(max(self.min_font_size, min(int(size), self.max_font_size)))
        self.setFont(font)
        self.setTransformOriginPoint(self._content_rect().center())

    def _apply_rotation_from_point(self, point: QPointF) -> None:
        center = self._content_rect().center()
        angle = (math.degrees(math.atan2(point.y() - center.y(), point.x() - center.x())) + 90) % 360
        self.setTransformOriginPoint(center)
        self.setRotation(angle)

    def _scene_distance_from_center(self, event) -> float:
        center = self.mapToScene(self._content_rect().center())
        scene_pos = event.scenePos()
        return math.hypot(scene_pos.x() - center.x(), scene_pos.y() - center.y())

    def _allows_transform(self) -> bool:
        if self.scene() is None or not self.scene().views():
            return True
        view = self.scene().views()[0]
        return getattr(view, "drawing_mode", DrawingMode.SELECT) == DrawingMode.SELECT


class TransformableImageItem(TransformHandleMixin, QGraphicsPixmapItem):
    """Image annotation with aspect-ratio resize and rotation handles."""

    def __init__(self, pixmap: QPixmap, width: float, height: float) -> None:
        super().__init__()
        self.source_pixmap = pixmap
        self.is_resizing = False
        self.is_rotating = False
        self.resize_start_size = (max(float(width), TRANSFORM_MIN_SIZE), max(float(height), TRANSFORM_MIN_SIZE))
        self.resize_handle = ""
        self.rotation_start_value = 0.0
        self._set_display_size(width, height)

    def boundingRect(self) -> QRectF:
        return self._extra_bounds()

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRect(self._content_rect())
        return self._transform_shape(path)

    def paint(self, painter, option, widget=None) -> None:
        super().paint(painter, option, widget)
        self._paint_transform_handles(painter)

    def mousePressEvent(self, event) -> None:
        if self._handle_mouse_press(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._handle_mouse_move(event, keep_corner_ratio=True):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._handle_mouse_release(event):
            return
        super().mouseReleaseEvent(event)

    def cancel_interaction(self) -> bool:
        """Cancel an image resize/rotation and restore the starting visual state."""
        if self.is_resizing and not hasattr(self, "resize_start_rect"):
            self.is_resizing = False
            self._set_display_size(*self.resize_start_size, QPointF(0, 0))
            self.unsetCursor()
            return True
        return TransformHandleMixin.cancel_interaction(self)

    def _set_display_size(
        self,
        width: float,
        height: float,
        offset: QPointF | None = None,
        keep_aspect: bool = True,
    ) -> None:
        width = max(float(width), TRANSFORM_MIN_SIZE)
        height = max(float(height), TRANSFORM_MIN_SIZE)
        self.setPixmap(
            self.source_pixmap.scaled(
                int(width),
                int(height),
                Qt.AspectRatioMode.KeepAspectRatio if keep_aspect else Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        if offset is not None:
            self.setOffset(offset)
        self.setTransformOriginPoint(self._content_rect().center())

    def _content_rect(self) -> QRectF:
        pixmap = self.pixmap()
        offset = self.offset()
        return QRectF(offset.x(), offset.y(), pixmap.width(), pixmap.height())

    def _set_content_rect(self, rect: QRectF, keep_aspect: bool = False) -> None:
        self.prepareGeometryChange()
        current = self._content_rect()
        delta = self.mapToParent(rect.topLeft()) - self.mapToParent(current.topLeft())
        self.setPos(self.pos() + delta)
        self._set_display_size(rect.width(), rect.height(), QPointF(0, 0), keep_aspect)


class DrawingMode(str, Enum):
    """Available canvas interaction modes."""

    PAN = "pan"
    SELECT = "select"
    LINE = "line"
    RECTANGLE = "rectangle"
    ROUNDED_RECTANGLE = "rounded_rectangle"
    ELLIPSE = "ellipse"
    TRIANGLE = "triangle"
    ZONE = "zone"
    FREEHAND = "freehand"
    LINK = "link"


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
        fill_color: str = "",
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
            return DrawingShape(shape_id, "Rectangle", [start_x, start_y, end_x, end_y, 0.0], color=color, fill_color=fill_color)

        if mode == DrawingMode.ROUNDED_RECTANGLE:
            return DrawingShape(
                shape_id,
                "RoundedRectangle",
                [start_x, start_y, end_x, end_y, 0.0],
                color=color,
                fill_color=fill_color,
            )

        if mode == DrawingMode.ELLIPSE:
            return DrawingShape(shape_id, "Ellipse", [start_x, start_y, end_x, end_y, 0.0], color=color, fill_color=fill_color)

        if mode == DrawingMode.TRIANGLE:
            points = [(start_x + end_x) / 2, start_y, end_x, end_y, start_x, end_y]
            return DrawingShape(shape_id, "Triangle", points, color=color, fill_color=fill_color)

        if mode == DrawingMode.ZONE:
            points = [start_x, start_y, end_x, start_y, end_x, end_y, start_x, end_y]
            return DrawingShape(shape_id, "Polygon", points, color=color, fill_color=fill_color)

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
        return DrawingShape(f"shape_{uuid.uuid4().hex}", "Text", [x, y, 0.0], color=color, line_thickness=font_size, label=text)

    def image_shape(self, position: QPointF, image_path: str, width: float, height: float) -> DrawingShape:
        """Create an image annotation at a scene position."""
        x, y = self.snap_callback(position.x(), position.y())
        return DrawingShape(f"shape_{uuid.uuid4().hex}", "Image", [x, y, width, height, 0.0], image_path=image_path)

    def item_from_shape(self, shape: DrawingShape | None) -> QGraphicsItem | None:
        """Create a graphics item from a drawing shape."""
        if shape is None:
            return None

        pen = QPen(QColor(shape.color), shape.line_thickness, Qt.PenStyle.SolidLine)
        brush = self._fill_brush(shape.fill_color)
        if shape.shape_type == "Line" and len(shape.points) >= 4:
            item = SelectableLineItem(shape.points[0], shape.points[1], shape.points[2], shape.points[3])
            item.setPen(pen)
            return item

        if shape.shape_type == "Rectangle" and len(shape.points) >= 4:
            x1, y1, x2, y2 = shape.points[:4]
            item = TransformableRectItem(QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)))
            item.setPen(pen)
            item.setBrush(brush)
            item.setTransformOriginPoint(item._content_rect().center())
            item.setRotation(float(shape.points[4]) if len(shape.points) >= 5 else 0.0)
            return item

        if shape.shape_type == "RoundedRectangle" and len(shape.points) >= 4:
            x1, y1, x2, y2 = shape.points[:4]
            item = TransformableRoundedRectItem(QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)))
            item.setPen(pen)
            item.setBrush(brush)
            item.setTransformOriginPoint(item._content_rect().center())
            item.setRotation(float(shape.points[4]) if len(shape.points) >= 5 else 0.0)
            return item

        if shape.shape_type == "Ellipse" and len(shape.points) >= 4:
            x1, y1, x2, y2 = shape.points[:4]
            item = TransformableEllipseItem(QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)))
            item.setPen(pen)
            item.setBrush(brush)
            item.setTransformOriginPoint(item._content_rect().center())
            item.setRotation(float(shape.points[4]) if len(shape.points) >= 5 else 0.0)
            return item

        if shape.shape_type in {"Polygon", "Triangle"} and len(shape.points) >= 6:
            polygon = QPolygonF(
                [
                    QPointF(shape.points[index], shape.points[index + 1])
                    for index in range(0, len(shape.points), 2)
                ]
            )
            item = TransformablePolygonItem(polygon)
            item.setPen(pen)
            item.setBrush(brush)
            return item

        if shape.shape_type == "Freehand" and len(shape.points) >= 4:
            path = QPainterPath(QPointF(shape.points[0], shape.points[1]))
            for index in range(2, len(shape.points), 2):
                path.lineTo(shape.points[index], shape.points[index + 1])
            item = SelectablePathItem(path)
            item.setPen(pen)
            return item

        if shape.shape_type == "Text" and len(shape.points) >= 2:
            item = TransformableTextItem(shape.label)
            font = item.font()
            font.setPointSize(self._text_font_size(shape.line_thickness))
            item.setFont(font)
            item.setDefaultTextColor(QColor(shape.color))
            item.setPos(shape.points[0], shape.points[1])
            item.setTransformOriginPoint(item._content_rect().center())
            item.setRotation(float(shape.points[2]) if len(shape.points) >= 3 else 0.0)
            return item

        if shape.shape_type == "Image" and len(shape.points) >= 4 and shape.image_path:
            pixmap = QPixmap(shape.image_path)
            if pixmap.isNull():
                return None
            item = TransformableImageItem(pixmap, float(shape.points[2]), float(shape.points[3]))
            item.setPos(shape.points[0], shape.points[1])
            item.setRotation(float(shape.points[4]) if len(shape.points) >= 5 else 0.0)
            return item

        return None

    def _text_font_size(self, line_thickness: int) -> int:
        return TEXT_DEFAULT_FONT_SIZE if line_thickness <= 2 else line_thickness

    def _fill_brush(self, fill_color: str) -> QBrush:
        color = QColor(fill_color)
        if not fill_color or not color.isValid():
            return QBrush(Qt.BrushStyle.NoBrush)
        return QBrush(color)
