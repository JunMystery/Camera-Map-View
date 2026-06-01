"""Graphics scene that keeps movable items inside the canvas bounds."""

from typing import Any

from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QGraphicsScene


class BoundedGraphicsScene(QGraphicsScene):
    """Clamp selected movable items to the scene rectangle during mouse drags."""

    def mouseMoveEvent(self, event: Any) -> None:
        """Clamp selected items after normal movement."""
        super().mouseMoveEvent(event)
        self.clamp_selected_items()

    def mouseReleaseEvent(self, event: Any) -> None:
        """Clamp selected items at drag end."""
        super().mouseReleaseEvent(event)
        self.clamp_selected_items()

    def clamp_selected_items(self) -> None:
        """Move selected items back inside scene bounds."""
        bounds = self.sceneRect()
        for item in self.selectedItems():
            rect = item.sceneBoundingRect()
            dx = self._axis_delta(rect.left(), rect.right(), bounds.left(), bounds.right())
            dy = self._axis_delta(rect.top(), rect.bottom(), bounds.top(), bounds.bottom())
            if dx or dy:
                item.setPos(item.pos() + QPointF(dx, dy))

    def _axis_delta(self, item_min: float, item_max: float, limit_min: float, limit_max: float) -> float:
        if item_min < limit_min:
            return limit_min - item_min
        if item_max > limit_max:
            return limit_max - item_max
        return 0.0
