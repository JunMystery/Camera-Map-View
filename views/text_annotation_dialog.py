"""Dialog for creating and editing text annotations."""

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config.i18n import t
from views.ui_theme import DANGER, color_swatch_stylesheet


class TextAnnotationDialog(QDialog):
    """Collect text annotation content, font size, and color."""

    def __init__(
        self,
        text: str = "",
        font_size: int = 18,
        color: str = DANGER,
        editing: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._color = QColor(color if QColor(color).isValid() else DANGER)
        self.setWindowTitle(t("dialog.edit_text.title") if editing else t("dialog.add_text.title"))
        self.setMinimumWidth(280)

        self.text_input = QLineEdit(text, self)
        self.size_input = QSpinBox(self)
        self.size_input.setRange(8, 96)
        self.size_input.setValue(max(8, min(96, font_size)))

        self.color_button = QPushButton(self)
        self.color_button.clicked.connect(self._choose_color)
        self.color_swatch = QLabel(self)
        self.color_swatch.setFixedSize(28, 20)
        self._refresh_color_preview()

        color_row = QHBoxLayout()
        color_row.setContentsMargins(0, 0, 0, 0)
        color_row.addWidget(self.color_swatch)
        color_row.addWidget(self.color_button, 1)

        form = QFormLayout()
        form.addRow(t("dialog.add_text.label"), self.text_input)
        form.addRow(t("dialog.add_text.size"), self.size_input)
        form.addRow(t("dialog.add_text.color"), color_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_values(self) -> tuple[str, int, str]:
        """Return trimmed text, font size, and color name."""
        return self.text_input.text().strip(), self.size_input.value(), self._color.name()

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(self._color, self, t("dialog.choose_color.title"))
        if color.isValid():
            self._color = color
            self._refresh_color_preview()

    def _refresh_color_preview(self) -> None:
        color_name = self._color.name()
        self.color_button.setText(color_name)
        self.color_button.setToolTip(t("dialog.add_text.color"))
        self.color_swatch.setStyleSheet(color_swatch_stylesheet(color_name))
