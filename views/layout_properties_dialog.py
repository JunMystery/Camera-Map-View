"""Dialog for creating or editing a map layout and its canvas settings."""

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config.i18n import t
from models.map_layout_model import MapLayout
from views.ui_theme import DANGER


class LayoutPropertiesDialog(QDialog):
    """Edit layout name, canvas size, grid size, and background scale."""

    def __init__(self, layout: MapLayout, editing: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.layout_model = layout
        self.editing = editing
        self.setModal(True)
        self.resize(420, 260)

        self.name_input = QLineEdit(layout.name, self)
        self.name_input.textChanged.connect(self._update_save_state)
        self.canvas_width_input = self._spin(500, 20000, layout.canvas_width)
        self.canvas_height_input = self._spin(500, 20000, layout.canvas_height)
        self.grid_size_input = self._spin(5, 200, layout.grid_size)
        self.background_scale_input = self._double_spin(0.1, 5.0, layout.background_scale)
        self.error_label = QLabel("", self)
        self.error_label.setStyleSheet(f"color: {DANGER};")
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self._build_layout()
        self.retranslate()
        self._update_save_state()

    def get_layout(self) -> MapLayout:
        """Return the edited layout values."""
        return MapLayout(
            id=self.layout_model.id,
            name=self.name_input.text().strip(),
            background_path=self.layout_model.background_path,
            grid_size=self.grid_size_input.value(),
            canvas_width=self.canvas_width_input.value(),
            canvas_height=self.canvas_height_input.value(),
            background_scale=self.background_scale_input.value(),
        )

    def retranslate(self) -> None:
        """Refresh dialog labels."""
        self.setWindowTitle(t("layout.edit_title") if self.editing else t("layout.create_title"))
        save_button = self.button_box.button(QDialogButtonBox.StandardButton.Save)
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if save_button is not None:
            save_button.setText(t("camera_dialog.save"))
        if cancel_button is not None:
            cancel_button.setText(t("camera_dialog.cancel"))

    def _build_layout(self) -> None:
        form = QFormLayout()
        form.addRow(t("layout.name"), self.name_input)
        form.addRow(t("settings.canvas_width"), self.canvas_width_input)
        form.addRow(t("settings.canvas_height"), self.canvas_height_input)
        form.addRow(t("settings.grid_size"), self.grid_size_input)
        form.addRow(t("settings.background_scale"), self.background_scale_input)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)

    def _update_save_state(self) -> None:
        valid = bool(self.name_input.text().strip())
        self.error_label.setText("" if valid else t("validation.layout_name_required"))
        save_button = self.button_box.button(QDialogButtonBox.StandardButton.Save)
        if save_button is not None:
            save_button.setEnabled(valid)

    def _spin(self, minimum: int, maximum: int, value: int) -> QSpinBox:
        spin = QSpinBox(self)
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        return spin

    def _double_spin(self, minimum: float, maximum: float, value: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox(self)
        spin.setRange(minimum, maximum)
        spin.setSingleStep(0.1)
        spin.setValue(value)
        return spin
