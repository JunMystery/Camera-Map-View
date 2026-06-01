"""Graphics item used to render a camera on the map canvas."""

from collections.abc import Callable
import math
from typing import Any

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QAction, QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QGraphicsItem, QMenu, QStyleOptionGraphicsItem, QWidget

from config.i18n import t
from models.camera_data_model import Camera


class CameraItem(QGraphicsItem):
    """Display and synchronize a camera model on a QGraphicsScene."""

    def __init__(self, camera: Camera) -> None:
        super().__init__()
        self.camera = camera
        self.edit_callback: Callable[[str], None] | None = None
        self.move_callback: Callable[[str, float, float], None] | None = None
        self.rotation_callback: Callable[[str, float], None] | None = None
        self.snap_callback: Callable[[float, float], tuple[float, float]] | None = None
        self.info_visibility = {"name": True, "zone": False, "ip": False, "dvr": False}
        self.is_rotating = False

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setPos(camera.position_x, camera.position_y)
        self.update_tooltip()

    def update_tooltip(self) -> None:
        """Refresh the hover tooltip from the camera model."""
        status_key = "camera.status.online" if self.camera.status else "camera.status.offline"
        self.setToolTip(
            t(
                "camera.tooltip",
                name=self.camera.name,
                ip_address=self.camera.ip_address,
                port=self.camera.port,
                camera_type=self.camera.camera_type,
                zone=self.camera.zone or t("camera.notes.empty"),
                dvr_origin=self.camera.dvr_origin or t("camera.notes.empty"),
                rotation=int(self.camera.rotation) % 360,
                status=t(status_key),
                notes=self.camera.notes or t("camera.notes.empty"),
            )
        )

    def set_info_visibility(self, visibility: dict[str, bool]) -> None:
        """Update which metadata fields are drawn below the marker."""
        self.info_visibility = visibility.copy()
        self.update()

    def update_status(self, is_online: bool) -> None:
        """Update the visual status indicator."""
        self.camera.status = is_online
        self.update_tooltip()
        self.update()

    def set_edit_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback for edit requests."""
        self.edit_callback = callback

    def set_move_callback(self, callback: Callable[[str, float, float], None]) -> None:
        """Register a callback for persisted position updates."""
        self.move_callback = callback

    def set_rotation_callback(self, callback: Callable[[str, float], None]) -> None:
        """Register a callback for persisted rotation updates."""
        self.rotation_callback = callback

    def set_snap_callback(self, callback: Callable[[float, float], tuple[float, float]]) -> None:
        """Register a callback that snaps coordinates before movement."""
        self.snap_callback = callback

    def boundingRect(self) -> QRectF:
        """Return the drawable area for icon, field-of-view wedge, and label."""
        return QRectF(-60, -60, 120, 120)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """Paint the camera marker."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_selected = self.isSelected()
        fov_color = QColor("#3b82f6") if is_selected else QColor("#9ca3af")
        fov_color.setAlpha(40 if is_selected else 15)

        painter.save()
        painter.rotate(self.camera.rotation)

        fov_path = QPainterPath()
        fov_path.moveTo(0, 0)
        fov_path.arcTo(QRectF(-50, -50, 100, 100), -30, 60)
        fov_path.closeSubpath()
        painter.fillPath(fov_path, QBrush(fov_color))

        fov_pen = QPen(fov_color, 1, Qt.PenStyle.DashLine)
        painter.setPen(fov_pen)
        painter.drawPath(fov_path)

        body_color = QColor("#3b82f6") if is_selected else QColor("#2d2d34")
        painter.setPen(QPen(QColor("#f3f4f6"), 1.5))
        painter.setBrush(QBrush(body_color))
        painter.drawRect(-12, -8, 20, 16)

        lens_path = QPainterPath()
        lens_path.moveTo(8, -5)
        lens_path.lineTo(15, -8)
        lens_path.lineTo(15, 8)
        lens_path.lineTo(8, 5)
        lens_path.closeSubpath()
        painter.setBrush(QBrush(QColor("#f3f4f6")))
        painter.drawPath(lens_path)

        painter.restore()

        if is_selected:
            painter.save()
            painter.rotate(self.camera.rotation)
            painter.setPen(QPen(QColor("#facc15"), 2, Qt.PenStyle.DashLine))
            painter.drawEllipse(QPointF(0, 0), 46, 46)
            painter.setPen(QPen(QColor("#facc15"), 2, Qt.PenStyle.SolidLine))
            painter.drawLine(0, 0, 46, 0)
            painter.setBrush(QBrush(QColor("#facc15")))
            painter.drawEllipse(41, -5, 10, 10)
            painter.restore()

        status_color = QColor("#10b981") if self.camera.status else QColor("#ef4444")
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.setBrush(QBrush(status_color))
        painter.drawEllipse(-16, -14, 8, 8)

        painter.setPen(QPen(QColor("#f3f4f6") if is_selected else QColor("#9ca3af"), 1))
        font = QFont("Inter", 8)
        if is_selected:
            font.setBold(True)
        painter.setFont(font)

        for index, line in enumerate(self._visible_info_lines()):
            text_rect = QRectF(-58, 18 + index * 14, 116, 14)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, line)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        """Sync model coordinates when the graphics item moves."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            value = self._clamp_to_scene(value)
            if self.snap_callback is not None:
                snapped_x, snapped_y = self.snap_callback(value.x(), value.y())
                return QPointF(snapped_x, snapped_y)

        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self.scene():
            new_pos = self.pos()
            self.camera.position_x = new_pos.x()
            self.camera.position_y = new_pos.y()
            if self.move_callback is not None:
                self.move_callback(self.camera.id, new_pos.x(), new_pos.y())
        return super().itemChange(change, value)

    def _clamp_to_scene(self, point: QPointF) -> QPointF:
        rect = self.scene().sceneRect()
        return QPointF(
            min(max(point.x(), rect.left()), rect.right()),
            min(max(point.y(), rect.top()), rect.bottom()),
        )

    def mouseDoubleClickEvent(self, event: Any) -> None:
        """Request editing when the camera item is double-clicked."""
        self._request_edit()
        event.accept()

    def mousePressEvent(self, event: Any) -> None:
        """Start direct rotation when the selected rotation ring is grabbed."""
        if event.button() == Qt.MouseButton.LeftButton and self.isSelected() and self._is_on_rotation_ring(event.pos()):
            self.is_rotating = True
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            self._apply_rotation_from_point(event.pos())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Any) -> None:
        """Rotate in real time while the ring is dragged."""
        if self.is_rotating:
            self._apply_rotation_from_point(event.pos())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        """Finish direct rotation."""
        if self.is_rotating and event.button() == Qt.MouseButton.LeftButton:
            self.is_rotating = False
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event: Any) -> None:
        """Show quick actions for a placed camera."""
        menu = QMenu()
        edit_action = QAction(t("camera.context.edit"), menu)
        edit_action.triggered.connect(self._request_edit)
        menu.addAction(edit_action)
        menu.exec(event.screenPos())

    def _request_edit(self) -> None:
        if self.edit_callback is not None:
            self.edit_callback(self.camera.id)

    def _visible_info_lines(self) -> list[str]:
        lines: list[str] = []
        if self.info_visibility.get("name", True):
            lines.append(self.camera.name)
        if self.info_visibility.get("zone") and self.camera.zone:
            lines.append(self.camera.zone)
        if self.info_visibility.get("ip"):
            lines.append(self.camera.ip_address)
        if self.info_visibility.get("dvr") and self.camera.dvr_origin:
            lines.append(self.camera.dvr_origin)
        return lines

    def _is_on_rotation_ring(self, point: QPointF) -> bool:
        distance = math.hypot(point.x(), point.y())
        return 36 <= distance <= 56

    def _apply_rotation_from_point(self, point: QPointF) -> None:
        angle = math.degrees(math.atan2(point.y(), point.x())) % 360
        self.camera.rotation = angle
        self.update_tooltip()
        self.update()
        if self.rotation_callback is not None:
            self.rotation_callback(self.camera.id, self.camera.rotation)
