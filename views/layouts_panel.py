"""Dockable panel for selecting and managing map layouts."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from config.i18n import t
from models.map_layout_model import MapLayout


class LayoutsPanel(QWidget):
    """Select, create, rename, and delete independent map layouts."""

    layout_selected = pyqtSignal(str)
    layout_add_requested = pyqtSignal()
    layout_rename_requested = pyqtSignal(str)
    layout_delete_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.layouts: list[MapLayout] = []
        self.combo = QComboBox(self)
        self.combo.currentIndexChanged.connect(self._emit_selected)
        self.add_button = QPushButton(self)
        self.rename_button = QPushButton(self)
        self.delete_button = QPushButton(self)
        self.add_button.clicked.connect(self.layout_add_requested.emit)
        self.rename_button.clicked.connect(lambda: self.layout_rename_requested.emit(self.current_layout_id()))
        self.delete_button.clicked.connect(lambda: self.layout_delete_requested.emit(self.current_layout_id()))
        row = QHBoxLayout()
        for button in [self.add_button, self.rename_button, self.delete_button]:
            row.addWidget(button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.combo)
        layout.addLayout(row)
        self.retranslate()

    def set_layouts(self, layouts: list[MapLayout], current_layout_id: str) -> None:
        """Refresh layout choices and current selection."""
        self.layouts = layouts
        self.combo.blockSignals(True)
        self.combo.clear()
        for layout in layouts:
            self.combo.addItem(layout.name, layout.id)
            if layout.id == current_layout_id:
                self.combo.setCurrentIndex(self.combo.count() - 1)
        self.combo.blockSignals(False)

    def current_layout_id(self) -> str:
        """Return selected layout id."""
        return str(self.combo.currentData() or "")

    def retranslate(self) -> None:
        """Refresh labels."""
        self.add_button.setText(t("layout.add"))
        self.rename_button.setText(t("layout.rename"))
        self.delete_button.setText(t("layout.delete"))

    def _emit_selected(self) -> None:
        if self.combo.currentData():
            self.layout_selected.emit(str(self.combo.currentData()))
