"""Graphics item used to render a camera on the map canvas."""

from collections.abc import Callable
import math
from typing import Any

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QAction, QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QGraphicsItem, QMenu, QStyleOptionGraphicsItem, QWidget

from config.i18n import t
from models.camera_data_model import Camera
from models.device_catalog import DEVICE_KIND_CAMERA, device_kind_label, device_variant_label
from views.map_drawing_tools import DrawingMode
from views.tool_icons import device_pixmap
from views.ui_theme import (
    DANGER,
    DARK_SURFACE_ALT,
    LIGHT_TEXT,
    SUCCESS,
    TEXT_MUTED,
    TEXT_ON_DARK,
    TEXT_WHITE,
    WARNING,
)


class CameraItem(QGraphicsItem):
    """Display and synchronize a camera model on a QGraphicsScene."""

    def __init__(self, camera: Camera) -> None:
        super().__init__()
        self.camera = camera
        self.edit_callback: Callable[[str], None] | None = None
        self.location_image_callback: Callable[[str], None] | None = None
        self.ping_callback: Callable[[str], None] | None = None
        self.move_callback: Callable[[str, float, float], None] | None = None
        self.rotation_callback: Callable[[str, float], None] | None = None
        self.scale_callback: Callable[[str, float], None] | None = None
        self.snap_callback: Callable[[float, float], tuple[float, float]] | None = None
        self.info_visibility = {"name": True, "zone": False, "ip": False, "dvr": False}
        self.is_rotating = False
        self.is_resizing = False
        self.resize_start_distance = 1.0
        self.resize_start_scale = 1.0
        self.rotation_start_value = camera.rotation
        self.min_scale = 0.5
        self.max_scale = 3.0
        self.light_theme = False

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setPos(camera.position_x, camera.position_y)
        self.setScale(camera.display_scale)
        self.update_tooltip()

    def update_tooltip(self) -> None:
        """Refresh the hover tooltip from the device model."""
        if not self.camera.ping_enabled or not self.camera.ip_address:
            status_text = t("device.status.unknown")
        else:
            status_key = "camera.status.online" if self.camera.status else "camera.status.offline"
            status_text = t(status_key)
        tooltip_key = "device.tooltip" if self.camera.device_kind == DEVICE_KIND_CAMERA else "device.tooltip.generic"
        self.setToolTip(
            t(
                tooltip_key,
                name=self.camera.name,
                device_kind=device_kind_label(self.camera.device_kind),
                variant=device_variant_label(self.camera.effective_variant()),
                ip_address=self.camera.ip_address or t("device.ip_empty"),
                port=self.camera.port,
                zone=self.camera.zone or t("camera.notes.empty"),
                dvr_origin=self.camera.dvr_origin or t("camera.notes.empty"),
                rotation=int(self.camera.rotation) % 360,
                fov_degrees=int(self.camera.fov_degrees),
                status=status_text,
                ping=t("device.ping.enabled") if self.camera.ping_enabled else t("device.ping.disabled"),
                notes=self.camera.notes or t("camera.notes.empty"),
            )
        )

    def set_info_visibility(self, visibility: dict[str, bool]) -> None:
        """Update which metadata fields are drawn below the marker."""
        self.info_visibility = visibility.copy()
        self.update()

    def set_light_theme(self, enabled: bool) -> None:
        """Use camera colors that contrast with the active canvas theme."""
        self.light_theme = enabled
        self.update()

    def update_status(self, is_online: bool) -> None:
        """Update the visual status indicator."""
        self.camera.status = is_online
        self.update_tooltip()
        self.update()

    def set_edit_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback for edit requests."""
        self.edit_callback = callback

    def set_location_image_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback for location image requests."""
        self.location_image_callback = callback

    def set_ping_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback for active ping requests."""
        self.ping_callback = callback

    def set_move_callback(self, callback: Callable[[str, float, float], None]) -> None:
        """Register a callback for persisted position updates."""
        self.move_callback = callback

    def set_rotation_callback(self, callback: Callable[[str, float], None]) -> None:
        """Register a callback for persisted rotation updates."""
        self.rotation_callback = callback

    def set_scale_callback(self, callback: Callable[[str, float], None]) -> None:
        """Register a callback for persisted scale updates."""
        self.scale_callback = callback

    def set_snap_callback(self, callback: Callable[[float, float], tuple[float, float]]) -> None:
        """Register a callback that snaps coordinates before movement."""
        self.snap_callback = callback

    def boundingRect(self) -> QRectF:
        """Return the drawable area for icon, field-of-view wedge, and label."""
        return QRectF(-64, -64, 136, 136)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """Paint the camera marker."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_selected = self.isSelected()
        is_camera = self.camera.device_kind == DEVICE_KIND_CAMERA
        fov_color = QColor(DANGER)
        fov_color.setAlpha(110 if is_selected else 55)

        if is_camera:
            painter.save()
            painter.rotate(self.camera.rotation)

            fov_pen = QPen(fov_color, 2.5 if is_selected else 1.5, Qt.PenStyle.DashLine)
            painter.setPen(fov_pen)
            if self.camera.fov_degrees >= 360:
                painter.setBrush(QBrush(fov_color))
                painter.drawEllipse(QPointF(0, 0), 50, 50)
            else:
                fov_span = max(1, min(int(self.camera.fov_degrees), 360))
                fov_path = QPainterPath()
                fov_path.moveTo(0, 0)
                fov_path.arcTo(QRectF(-50, -50, 100, 100), -fov_span / 2, fov_span)
                fov_path.closeSubpath()
                painter.fillPath(fov_path, QBrush(fov_color))
                painter.drawPath(fov_path)

            painter.restore()

        self._paint_device_body(painter, is_selected)

        if is_selected and is_camera:
            painter.save()
            painter.rotate(self.camera.rotation)
            painter.setPen(QPen(QColor(WARNING), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(0, 0), 46, 46)
            painter.setPen(QPen(QColor(WARNING), 2, Qt.PenStyle.SolidLine))
            painter.drawLine(0, 0, 46, 0)
            painter.setBrush(QBrush(QColor(WARNING)))
            painter.drawEllipse(41, -5, 10, 10)
            painter.restore()

            painter.save()
            painter.setPen(QPen(QColor(WARNING), 1.5, Qt.PenStyle.SolidLine))
            painter.setBrush(QBrush(QColor(WARNING)))
            painter.drawRect(self._resize_handle_rect())
            painter.restore()

        if not self.camera.ping_enabled or not self.camera.ip_address:
            status_color = QColor(TEXT_MUTED)
        else:
            status_color = QColor(SUCCESS) if self.camera.status else QColor(DANGER)
        painter.setPen(QPen(QColor(TEXT_WHITE), 1))
        painter.setBrush(QBrush(status_color))
        painter.drawEllipse(-16, -14, 8, 8)

        label_color = QColor(LIGHT_TEXT) if self.light_theme else QColor(TEXT_ON_DARK)
        painter.setPen(QPen(label_color if is_selected else QColor(TEXT_MUTED), 1))
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
            self._notify_canvas_layers_changed()
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
        """Start direct rotation or resizing when selected handles are grabbed."""
        if not self._canvas_allows_handle_edit():
            super().mousePressEvent(event)
            return
        if self.camera.device_kind != DEVICE_KIND_CAMERA:
            super().mousePressEvent(event)
            return
        if event.button() == Qt.MouseButton.LeftButton and self.isSelected() and self._is_on_resize_handle(event.pos()):
            self.is_resizing = True
            self.resize_start_distance = max(self._scene_distance_from_center(event), 1.0)
            self.resize_start_scale = self.scale()
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton and self.isSelected() and self._is_on_rotation_ring(event.pos()):
            self.is_rotating = True
            self.rotation_start_value = self.camera.rotation
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            self._apply_rotation_from_point(event.pos())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Any) -> None:
        """Rotate or resize in real time while a selected handle is dragged."""
        if self.is_resizing:
            self._apply_resize_from_distance(self._scene_distance_from_center(event))
            event.accept()
            return
        if self.is_rotating:
            self._apply_rotation_from_point(event.pos())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        """Finish direct rotation or resizing."""
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

    def contextMenuEvent(self, event: Any) -> None:
        """Show quick actions for a placed camera."""
        menu = QMenu()
        location_image_action = QAction(t("camera.context.location_image"), menu)
        location_image_action.triggered.connect(self._request_location_image)
        ping_action = QAction(t("camera.context.ping"), menu)
        ping_action.triggered.connect(self._request_ping)
        edit_action = QAction(t("camera.context.edit"), menu)
        edit_action.triggered.connect(self._request_edit)
        menu.addAction(location_image_action)
        menu.addAction(ping_action)
        menu.addAction(edit_action)
        menu.exec(event.screenPos())

    def _request_edit(self) -> None:
        if self.edit_callback is not None:
            self.edit_callback(self.camera.id)

    def _request_location_image(self) -> None:
        if self.location_image_callback is not None:
            self.location_image_callback(self.camera.id)

    def _request_ping(self) -> None:
        if self.ping_callback is not None:
            self.ping_callback(self.camera.id)

    def cancel_interaction(self) -> bool:
        """Cancel an in-progress camera handle edit and restore the original value."""
        if self.is_resizing:
            self.is_resizing = False
            self._set_camera_scale(self.resize_start_scale)
            self.unsetCursor()
            return True
        if self.is_rotating:
            self.is_rotating = False
            self.camera.rotation = self.rotation_start_value
            self.update_tooltip()
            self.update()
            if self.rotation_callback is not None:
                self.rotation_callback(self.camera.id, self.camera.rotation)
            self.unsetCursor()
            return True
        return False

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

    def _resize_handle_rect(self) -> QRectF:
        return QRectF(48, 48, 12, 12)

    def _is_on_resize_handle(self, point: QPointF) -> bool:
        return self._resize_handle_rect().contains(point)

    def _scene_distance_from_center(self, event: Any) -> float:
        scene_pos = event.scenePos() if hasattr(event, "scenePos") else self.mapToScene(event.pos())
        center = self.scenePos()
        return math.hypot(scene_pos.x() - center.x(), scene_pos.y() - center.y())

    def _apply_resize_from_distance(self, distance: float) -> None:
        ratio = max(distance, 1.0) / self.resize_start_distance
        self._set_camera_scale(self.resize_start_scale * ratio)

    def _set_camera_scale(self, scale: float) -> None:
        self.camera.display_scale = min(max(scale, self.min_scale), self.max_scale)
        self.setScale(self.camera.display_scale)
        if self.scale_callback is not None:
            self.scale_callback(self.camera.id, self.camera.display_scale)
        self._notify_canvas_layers_changed()

    def _apply_rotation_from_point(self, point: QPointF) -> None:
        angle = math.degrees(math.atan2(point.y(), point.x())) % 360
        self.camera.rotation = angle
        self.update_tooltip()
        self.update()
        if self.rotation_callback is not None:
            self.rotation_callback(self.camera.id, self.camera.rotation)
        self._notify_canvas_layers_changed()

    def _canvas_allows_handle_edit(self) -> bool:
        if self.scene() is None or not self.scene().views():
            return True
        view = self.scene().views()[0]
        return getattr(view, "drawing_mode", DrawingMode.SELECT) == DrawingMode.SELECT

    def _notify_canvas_layers_changed(self) -> None:
        if self.scene() is None or not self.scene().views():
            return
        view = self.scene().views()[0]
        signal = getattr(view, "layers_changed", None)
        if signal is not None:
            signal.emit()
        refresh_links = getattr(view, "refresh_device_links", None)
        if callable(refresh_links):
            refresh_links()

    def _paint_device_body(self, painter: QPainter, is_selected: bool) -> None:
        outline_color = QColor(WARNING if is_selected else TEXT_ON_DARK)
        painter.setPen(QPen(outline_color, 2 if is_selected else 1.5))
        painter.setBrush(QBrush(QColor("#f8fafc" if self.light_theme else "#1e293b")))
        painter.drawRoundedRect(QRectF(-20, -18, 40, 36), 5, 5)

        pixmap = device_pixmap(self.camera.device_kind, 28)
        if pixmap.isNull():
            font = QFont("Inter", 8)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QPen(QColor(TEXT_WHITE if not self.light_theme else LIGHT_TEXT), 1))
            initials = self.camera.device_kind[:2].upper()
            painter.drawText(QRectF(-16, -12, 32, 24), Qt.AlignmentFlag.AlignCenter, initials)
            return
        painter.drawPixmap(-14, -14, 28, 28, pixmap)
