"""Small vector icons rendered with Qt for tool panels."""

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

from views.ui_theme import PRIMARY_SOFT, SUCCESS, TEXT_ON_DARK


def tool_icon(name: str, color: str = TEXT_ON_DARK, accent: str = PRIMARY_SOFT) -> QIcon:
    """Create a simple high-contrast icon for a named UI action."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if name in {"pan", "hand"}:
        path = QPainterPath(QPointF(10, 15))
        path.lineTo(10, 23)
        path.cubicTo(10, 27, 13, 29, 17, 29)
        path.lineTo(21, 29)
        path.cubicTo(25, 29, 27, 26, 27, 22)
        path.lineTo(27, 15)
        path.cubicTo(27, 13, 24, 13, 24, 15)
        path.lineTo(24, 19)
        path.lineTo(24, 12)
        path.cubicTo(24, 10, 21, 10, 21, 12)
        path.lineTo(21, 18)
        path.lineTo(21, 10)
        path.cubicTo(21, 8, 18, 8, 18, 10)
        path.lineTo(18, 18)
        path.lineTo(18, 8)
        path.cubicTo(18, 6, 15, 6, 15, 8)
        path.lineTo(15, 19)
        path.lineTo(13, 15)
        path.cubicTo(12, 13, 10, 13, 10, 15)
        painter.drawPath(path)
    elif name in {"select", "cursor"}:
        path = QPainterPath(QPointF(9, 5))
        path.lineTo(23, 18)
        path.lineTo(16, 19)
        path.lineTo(20, 28)
        path.lineTo(16, 29)
        path.lineTo(12, 20)
        path.lineTo(7, 25)
        path.closeSubpath()
        painter.setBrush(QColor(color))
        painter.drawPath(path)
    elif name in {"draw_line", "line"}:
        painter.drawLine(7, 24, 25, 8)
    elif name in {"draw_rectangle", "rectangle"}:
        painter.drawRect(QRectF(7, 8, 18, 16))
    elif name in {"draw_zone", "zone"}:
        points = QPolygonF([QPointF(8, 20), QPointF(13, 8), QPointF(25, 11), QPointF(23, 24)])
        painter.drawPolygon(points)
    elif name in {"draw_freehand", "freehand"}:
        path = QPainterPath(QPointF(6, 21))
        path.cubicTo(10, 5, 15, 29, 20, 13)
        path.cubicTo(22, 7, 25, 10, 27, 17)
        painter.drawPath(path)
    elif name in {"add_text", "text"}:
        font = painter.font()
        font.setBold(True)
        font.setPointSize(19)
        painter.setFont(font)
        painter.drawText(QRectF(5, 4, 24, 25), Qt.AlignmentFlag.AlignCenter, "T")
    elif name in {"insert_png", "image"}:
        painter.drawRect(QRectF(7, 8, 18, 17))
        painter.drawLine(9, 22, 14, 16)
        painter.drawLine(14, 16, 18, 20)
        painter.drawLine(18, 20, 24, 13)
        painter.drawEllipse(QRectF(19, 10, 3, 3))
    elif name in {"choose_color", "color"}:
        painter.setBrush(QColor(accent))
        painter.drawEllipse(QRectF(7, 7, 18, 18))
        painter.setBrush(QColor(SUCCESS))
        painter.drawEllipse(QRectF(12, 12, 8, 8))
    elif name in {"delete_selected", "delete", "trash"}:
        painter.drawLine(10, 11, 23, 11)
        painter.drawLine(13, 8, 20, 8)
        painter.drawRect(QRectF(11, 13, 11, 14))
        painter.drawLine(15, 16, 15, 25)
        painter.drawLine(19, 16, 19, 25)
    elif name in {"rotate_camera", "rotate"}:
        painter.drawArc(QRectF(7, 8, 18, 18), 35 * 16, 285 * 16)
        painter.drawLine(23, 8, 26, 8)
        painter.drawLine(23, 8, 23, 11)
    elif name == "grid":
        for value in (9, 16, 23):
            painter.drawLine(value, 6, value, 26)
            painter.drawLine(6, value, 26, value)
    elif name in {"info", "show_name", "show_zone", "show_ip", "show_dvr"}:
        painter.drawEllipse(QRectF(8, 8, 16, 16))
        painter.drawLine(16, 15, 16, 22)
        painter.drawPoint(16, 11)
    elif name in {"collapse", "expand"}:
        painter.drawLine(10, 11, 16, 17)
        painter.drawLine(22, 11, 16, 17)
        if name == "expand":
            painter.drawLine(10, 21, 16, 15)
            painter.drawLine(22, 21, 16, 15)
    elif name in {"visible", "eye"}:
        path = QPainterPath(QPointF(5, 16))
        path.cubicTo(10, 8, 22, 8, 27, 16)
        path.cubicTo(22, 24, 10, 24, 5, 16)
        painter.drawPath(path)
        painter.drawEllipse(QRectF(13, 13, 6, 6))
    elif name in {"locked", "lock"}:
        painter.drawRect(QRectF(9, 14, 14, 11))
        painter.drawArc(QRectF(11, 7, 10, 12), 0, 180 * 16)
    elif name in {"add_layer", "add"}:
        painter.drawRect(QRectF(7, 9, 15, 16))
        painter.drawLine(24, 18, 30, 18)
        painter.drawLine(27, 15, 27, 21)
    elif name == "up":
        painter.drawLine(16, 8, 8, 19)
        painter.drawLine(16, 8, 24, 19)
    elif name == "down":
        painter.drawLine(16, 24, 8, 13)
        painter.drawLine(16, 24, 24, 13)
    elif name in {"select_contents", "check"}:
        painter.drawLine(7, 17, 13, 23)
        painter.drawLine(13, 23, 25, 9)
    elif name in {"move", "move_selected"}:
        painter.drawLine(7, 16, 25, 16)
        painter.drawLine(19, 10, 25, 16)
        painter.drawLine(19, 22, 25, 16)
    elif name in {"camera", "add_camera"}:
        painter.drawRect(QRectF(7, 11, 14, 11))
        painter.drawLine(21, 14, 27, 10)
        painter.drawLine(21, 19, 27, 23)
        if name == "add_camera":
            painter.drawLine(25, 5, 31, 5)
            painter.drawLine(28, 2, 28, 8)
    elif name in {"layout", "add_layout"}:
        painter.drawRect(QRectF(7, 8, 18, 18))
        painter.drawLine(7, 15, 25, 15)
        painter.drawLine(15, 8, 15, 26)
        if name == "add_layout":
            painter.drawLine(24, 6, 30, 6)
            painter.drawLine(27, 3, 27, 9)
    elif name in {"edit", "rename"}:
        painter.drawLine(9, 23, 14, 22)
        painter.drawLine(14, 22, 25, 11)
        painter.drawLine(21, 7, 25, 11)
        painter.drawLine(18, 10, 22, 14)
    elif name in {"cog", "settings"}:
        painter.drawEllipse(QRectF(11, 11, 10, 10))
        for angle in range(0, 360, 45):
            painter.save()
            painter.translate(16, 16)
            painter.rotate(angle)
            painter.drawLine(0, -13, 0, -10)
            painter.restore()
        painter.drawEllipse(QRectF(14, 14, 4, 4))
    elif name == "import":
        painter.drawRect(QRectF(8, 8, 16, 18))
        painter.drawLine(16, 5, 16, 18)
        painter.drawLine(11, 13, 16, 18)
        painter.drawLine(21, 13, 16, 18)
    elif name == "export":
        painter.drawRect(QRectF(8, 8, 16, 18))
        painter.drawLine(16, 20, 16, 6)
        painter.drawLine(11, 11, 16, 6)
        painter.drawLine(21, 11, 16, 6)
    else:
        painter.drawRect(QRectF(8, 8, 16, 16))

    painter.end()
    return QIcon(pixmap)
