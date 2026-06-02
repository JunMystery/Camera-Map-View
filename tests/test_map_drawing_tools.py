"""Tests for map drawing item creation."""

from PyQt6.QtWidgets import QApplication, QGraphicsTextItem

from models.drawing_shape_model import DrawingShape
from views.map_drawing_tools import TEXT_DEFAULT_FONT_SIZE, DrawingTool
from views.tool_icons import tool_icon

APP = QApplication.instance() or QApplication([])


def test_text_shape_uses_line_thickness_as_font_size() -> None:
    tool = DrawingTool(lambda x, y: (x, y))

    item = tool.item_from_shape(DrawingShape("shape_text", "Text", [0.0, 0.0], line_thickness=28, label="Note"))

    assert isinstance(item, QGraphicsTextItem)
    assert item.font().pointSize() == 28


def test_legacy_text_shape_uses_default_font_size() -> None:
    tool = DrawingTool(lambda x, y: (x, y))

    item = tool.item_from_shape(DrawingShape("shape_text", "Text", [0.0, 0.0], line_thickness=2, label="Note"))

    assert isinstance(item, QGraphicsTextItem)
    assert item.font().pointSize() == TEXT_DEFAULT_FONT_SIZE


def test_light_theme_tool_icon_uses_dark_pixels() -> None:
    pixmap = tool_icon("pan", color="#111827").pixmap(32, 32)
    image = pixmap.toImage()

    dark_pixels = 0
    for x in range(image.width()):
        for y in range(image.height()):
            color = image.pixelColor(x, y)
            if color.alpha() and color.red() < 80 and color.green() < 100 and color.blue() < 130:
                dark_pixels += 1

    assert dark_pixels > 20
