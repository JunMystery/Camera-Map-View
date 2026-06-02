"""Application settings dialog with horizontal tabs."""

from collections.abc import Callable

from PyQt6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QSpinBox, QTabWidget, QVBoxLayout, QWidget

from config.i18n import t


class SettingsDialog(QDialog):
    """Edit network, canvas, and appearance settings."""

    def __init__(
        self,
        settings: dict[str, object],
        parent: QWidget | None = None,
        theme_changed: Callable[[bool], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.resize(420, 320)
        self.theme_changed = theme_changed
        self.tabs = QTabWidget(self)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.interval_input = self._spin(5, 3600, int(settings["ping_interval"]))
        self.timeout_input = self._double_spin(0.1, 30.0, float(settings["ping_timeout"]))
        self.retries_input = self._spin(1, 10, int(settings["ping_retries"]))
        self.canvas_width_input = self._spin(500, 20000, int(settings["canvas_width"]))
        self.canvas_height_input = self._spin(500, 20000, int(settings["canvas_height"]))
        self.grid_size_input = self._spin(5, 200, int(settings["grid_size"]))
        self.background_scale_input = self._double_spin(0.1, 5.0, float(settings["background_scale"]))
        self.theme_input = QComboBox(self)
        self.theme_input.addItem("", False)
        self.theme_input.addItem("", True)
        self.theme_input.setCurrentIndex(1 if bool(settings["light_theme"]) else 0)
        self.theme_input.currentIndexChanged.connect(self._handle_theme_changed)
        self._build_tabs()
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(self.button_box)
        self.retranslate()

    def values(self) -> dict[str, object]:
        """Return selected settings values."""
        return {
            "ping_interval": self.interval_input.value(),
            "ping_timeout": self.timeout_input.value(),
            "ping_retries": self.retries_input.value(),
            "canvas_width": self.canvas_width_input.value(),
            "canvas_height": self.canvas_height_input.value(),
            "grid_size": self.grid_size_input.value(),
            "background_scale": self.background_scale_input.value(),
            "light_theme": bool(self.theme_input.currentData()),
        }

    def retranslate(self) -> None:
        """Refresh dialog labels."""
        self.setWindowTitle(t("settings.title"))
        self.tabs.setTabText(0, t("settings.network"))
        self.tabs.setTabText(1, t("settings.canvas"))
        self.tabs.setTabText(2, t("settings.appearance"))
        self.theme_input.setItemText(0, t("settings.theme_dark"))
        self.theme_input.setItemText(1, t("settings.theme_light"))

    def _build_tabs(self) -> None:
        network = QWidget(self)
        network_form = QFormLayout(network)
        network_form.addRow(t("settings.ping_interval"), self.interval_input)
        network_form.addRow(t("settings.timeout"), self.timeout_input)
        network_form.addRow(t("settings.retries"), self.retries_input)
        canvas = QWidget(self)
        canvas_form = QFormLayout(canvas)
        canvas_form.addRow(t("settings.canvas_width"), self.canvas_width_input)
        canvas_form.addRow(t("settings.canvas_height"), self.canvas_height_input)
        canvas_form.addRow(t("settings.grid_size"), self.grid_size_input)
        canvas_form.addRow(t("settings.background_scale"), self.background_scale_input)
        appearance = QWidget(self)
        appearance_form = QFormLayout(appearance)
        appearance_form.addRow(t("settings.theme"), self.theme_input)
        self.tabs.addTab(network, "")
        self.tabs.addTab(canvas, "")
        self.tabs.addTab(appearance, "")

    def _handle_theme_changed(self) -> None:
        if self.theme_changed is not None:
            self.theme_changed(bool(self.theme_input.currentData()))

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
