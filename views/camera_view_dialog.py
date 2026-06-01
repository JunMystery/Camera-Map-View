"""Camera properties dialog for editing camera metadata."""

from PyQt6.QtCore import QRegularExpression, Qt
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config.i18n import t
from models.camera_data_model import Camera


class CameraPropertiesDialog(QDialog):
    """Edit a camera name, network settings, type, rotation, status, and notes."""

    def __init__(self, camera: Camera, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.camera = camera

        self.setModal(True)
        self.resize(420, 360)

        self.name_input = QLineEdit(camera.name, self)
        self.name_input.textChanged.connect(self._update_save_state)
        self.ip_input = QLineEdit(camera.ip_address, self)
        self.ip_input.setValidator(self._ip_validator())
        self.ip_input.textChanged.connect(self._update_save_state)

        self.port_input = QSpinBox(self)
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(camera.port)

        self.camera_type_values = ["Fixed", "PTZ", "Dome", "Fisheye", "360", "AI"]
        self.type_input = QComboBox(self)
        self.zone_input = QLineEdit(camera.zone, self)
        self.dvr_input = QLineEdit(camera.dvr_origin, self)

        self.rotation_slider = QSlider(self)
        self.rotation_slider.setOrientation(Qt.Orientation.Horizontal)
        self.rotation_slider.setRange(0, 359)
        self.rotation_slider.setValue(int(camera.rotation) % 360)

        self.rotation_input = QSpinBox(self)
        self.rotation_input.setRange(0, 359)
        self.rotation_input.setValue(int(camera.rotation) % 360)
        self.rotation_slider.valueChanged.connect(self.rotation_input.setValue)
        self.rotation_input.valueChanged.connect(self.rotation_slider.setValue)

        self.status_input = QCheckBox(self)
        self.status_input.setChecked(camera.status)

        self.notes_input = QPlainTextEdit(camera.notes, self)
        self.notes_input.setMinimumHeight(80)

        self.error_label = QLabel("", self)
        self.error_label.setStyleSheet("color: #ef4444;")

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.name_label = QLabel(self)
        self.ip_label = QLabel(self)
        self.port_label = QLabel(self)
        self.type_label = QLabel(self)
        self.zone_label = QLabel(self)
        self.dvr_label = QLabel(self)
        self.rotation_label = QLabel(self)
        self.status_label = QLabel(self)
        self.notes_label = QLabel(self)

        self._build_layout()
        self.retranslate()
        self._update_save_state()

    def get_camera(self) -> Camera:
        """Return a camera copy populated from dialog fields."""
        return Camera(
            id=self.camera.id,
            name=self.name_input.text().strip(),
            ip_address=self.ip_input.text().strip(),
            port=self.port_input.value(),
            camera_type=self.type_input.currentData(),
            position_x=self.camera.position_x,
            position_y=self.camera.position_y,
            rotation=float(self.rotation_input.value()),
            status=self.status_input.isChecked(),
            last_check=self.camera.last_check,
            notes=self.notes_input.toPlainText().strip(),
            zone=self.zone_input.text().strip(),
            dvr_origin=self.dvr_input.text().strip(),
        )

    def _build_layout(self) -> None:
        form = QFormLayout()
        form.addRow(self.name_label, self.name_input)
        form.addRow(self.ip_label, self.ip_input)
        form.addRow(self.port_label, self.port_input)
        form.addRow(self.type_label, self.type_input)
        form.addRow(self.zone_label, self.zone_input)
        form.addRow(self.dvr_label, self.dvr_input)

        rotation_layout = QHBoxLayout()
        rotation_layout.addWidget(self.rotation_slider)
        rotation_layout.addWidget(self.rotation_input)
        form.addRow(self.rotation_label, rotation_layout)

        form.addRow(self.status_label, self.status_input)
        form.addRow(self.notes_label, self.notes_input)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)

    def _update_save_state(self) -> None:
        has_name = bool(self.name_input.text().strip())
        has_valid_ip = self.ip_input.hasAcceptableInput()
        is_valid = has_name and has_valid_ip
        if not has_name:
            self.error_label.setText(t("validation.camera_name_required"))
        elif not has_valid_ip:
            self.error_label.setText(t("validation.invalid_ip"))
        else:
            self.error_label.setText("")
        save_button = self.button_box.button(QDialogButtonBox.StandardButton.Save)
        if save_button is not None:
            save_button.setEnabled(is_valid)

    def _ip_validator(self) -> QRegularExpressionValidator:
        octet = r"(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
        regex = QRegularExpression(rf"^{octet}\.{octet}\.{octet}\.{octet}$")
        return QRegularExpressionValidator(regex, self)

    def retranslate(self) -> None:
        """Refresh dialog text for the active language."""
        self.setWindowTitle(t("camera_dialog.title"))
        self.name_label.setText(t("camera_dialog.name"))
        self.ip_label.setText(t("camera_dialog.ip"))
        self.port_label.setText(t("camera_dialog.port"))
        self.type_label.setText(t("camera_dialog.type"))
        self.zone_label.setText(t("camera_dialog.zone"))
        self.dvr_label.setText(t("camera_dialog.dvr_origin"))
        self.rotation_label.setText(t("camera_dialog.rotation"))
        self.status_label.setText(t("camera_dialog.status"))
        self.notes_label.setText(t("camera_dialog.notes"))
        self.status_input.setText(t("camera.status.online"))
        self._retranslate_camera_types()

        save_button = self.button_box.button(QDialogButtonBox.StandardButton.Save)
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if save_button is not None:
            save_button.setText(t("camera_dialog.save"))
        if cancel_button is not None:
            cancel_button.setText(t("camera_dialog.cancel"))

    def _retranslate_camera_types(self) -> None:
        current_value = self.type_input.currentData() or self.camera.camera_type
        self.type_input.clear()
        labels = {
            "Fixed": t("camera_type.fixed"),
            "PTZ": t("camera_type.ptz"),
            "Dome": t("camera_type.dome"),
            "Fisheye": t("camera_type.fisheye"),
            "360": t("camera_type.360"),
            "AI": t("camera_type.ai"),
        }
        for value in self.camera_type_values:
            self.type_input.addItem(labels[value], value)
            if value == current_value:
                self.type_input.setCurrentIndex(self.type_input.count() - 1)
