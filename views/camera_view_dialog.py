"""Camera properties dialog for editing camera metadata."""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from PyQt6.QtCore import QRegularExpression, Qt
from PyQt6.QtGui import QPixmap, QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config.i18n import t
from models.camera_data_model import Camera
from models.device_catalog import DEVICE_KIND_CAMERA, DEVICE_KINDS, device_kind_label, device_variant_label, variants_for_kind
from utils.image_assets import import_camera_location_image, is_supported_image
from views.device_connections_dialog import DeviceConnectionsDialog
from views.ui_theme import DANGER


class CameraPropertiesDialog(QDialog):
    """Edit a device name, network settings, type, status, links, and notes."""

    def __init__(
        self,
        camera: Camera,
        parent: QWidget | None = None,
        available_devices: list[Camera] | None = None,
        linked_device_ids: list[str] | None = None,
        incoming_device_ids: list[str] | None = None,
        parent_ip_lookup: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.camera = camera
        self.location_image_path = camera.location_image_path
        self.pending_location_source = ""
        self.available_devices = [device for device in available_devices or [] if device.id != camera.id]
        self.linked_device_ids = set(linked_device_ids or [])
        self.checked_link_ids = set(self.linked_device_ids)
        self.incoming_device_ids = set(incoming_device_ids or [])
        self.removed_incoming_device_ids: set[str] = set()
        self.parent_ip_lookup = parent_ip_lookup or (lambda _device_id: "")

        self.setModal(True)
        self.resize(540, 560)

        self.name_input = QLineEdit(camera.name, self)
        self.name_input.textChanged.connect(self._update_save_state)
        self.badge_input = QLineEdit(camera.badge_text[:3].upper(), self)
        self.badge_input.setMaxLength(3)
        self.badge_input.textChanged.connect(self._normalize_badge_text)
        self.ip_input = QLineEdit(camera.ip_address, self)
        self.ip_input.setValidator(self._ip_validator())
        self.ip_input.textChanged.connect(self._handle_ip_changed)

        self.port_input = QSpinBox(self)
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(camera.port)

        self.kind_input = QComboBox(self)
        self.kind_input.currentIndexChanged.connect(self._handle_kind_changed)
        self.variant_input = QComboBox(self)
        self.variant_input.currentIndexChanged.connect(self._update_save_state)
        self.type_input = self.variant_input
        self.fov_input = QComboBox(self)
        self.fov_input.currentIndexChanged.connect(self._update_save_state)
        self.zone_input = QLineEdit(camera.zone, self)
        self.ping_input = QCheckBox(self)
        self.ping_input.setChecked(camera.ping_enabled)

        self.notes_input = QPlainTextEdit(camera.notes, self)
        self.notes_input.setMinimumHeight(80)
        self.location_preview = QLabel(self)
        self.location_preview.setFixedSize(96, 64)
        self.location_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.location_path_label = QLabel(self)
        self.location_path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.upload_location_button = QPushButton(self)
        self.remove_location_button = QPushButton(self)
        self.manage_connections_button = QPushButton(self)
        self.upload_location_button.clicked.connect(self.upload_location_image)
        self.remove_location_button.clicked.connect(self.remove_location_image)
        self.manage_connections_button.clicked.connect(self.manage_connections)

        self.error_label = QLabel("", self)
        self.error_label.setStyleSheet(f"color: {DANGER};")

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.name_label = QLabel(self)
        self.badge_label = QLabel(self)
        self.ip_label = QLabel(self)
        self.port_label = QLabel(self)
        self.type_label = QLabel(self)
        self.fov_label = QLabel(self)
        self.kind_label = QLabel(self)
        self.zone_label = QLabel(self)
        self.status_label = QLabel(self)
        self.notes_label = QLabel(self)
        self.location_image_label = QLabel(self)
        self.connections_label = QLabel(self)

        self._build_layout()
        self.retranslate()
        self._refresh_location_preview()
        self._update_save_state()

    def get_camera(self) -> Camera:
        """Return a camera copy populated from dialog fields."""
        location_image_path = self.location_image_path
        if self.pending_location_source:
            imported = import_camera_location_image(self.pending_location_source)
            if imported is not None:
                location_image_path = imported[0]
        return Camera(
            id=self.camera.id,
            name=self.name_input.text().strip(),
            ip_address=self.ip_input.text().strip(),
            port=self.port_input.value(),
            camera_type=str(self.variant_input.currentData() or ""),
            position_x=self.camera.position_x,
            position_y=self.camera.position_y,
            rotation=self.camera.rotation,
            display_scale=self.camera.display_scale,
            status=self.camera.status,
            last_check=self.camera.last_check,
            notes=self.notes_input.toPlainText().strip(),
            zone=self.zone_input.text().strip(),
            dvr_origin=self.camera.dvr_origin,
            layer_id=self.camera.layer_id,
            location_image_path=location_image_path,
            device_kind=str(self.kind_input.currentData() or DEVICE_KIND_CAMERA),
            variant=str(self.variant_input.currentData() or ""),
            ping_enabled=self.ping_input.isChecked(),
            fov_degrees=int(self.fov_input.currentData() or self.camera.fov_degrees or 80),
            object_locked=self.camera.object_locked,
            z_index=self.camera.z_index,
            object_visible=self.camera.object_visible,
            badge_text=self.badge_input.text().strip().upper()[:3],
        )

    def _build_layout(self) -> None:
        form = QFormLayout()
        form.setVerticalSpacing(10)
        form.addRow(self.name_label, self.name_input)
        form.addRow(self.badge_label, self.badge_input)
        form.addRow(self.kind_label, self.kind_input)
        form.addRow(self.ip_label, self.ip_input)
        form.addRow(self.port_label, self.port_input)
        form.addRow(self.type_label, self.variant_input)
        form.addRow(self.fov_label, self.fov_input)
        form.addRow(self.zone_label, self.zone_input)

        form.addRow(self.status_label, self._status_ping_row())
        form.addRow(self.notes_label, self.notes_input)
        form.addRow(self.location_image_label, self._location_image_row())
        form.addRow(self.connections_label, self.manage_connections_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)

    def _update_save_state(self) -> None:
        has_name = bool(self.name_input.text().strip())
        ip_text = self.ip_input.text().strip()
        has_valid_ip = self.ip_input.hasAcceptableInput() if ip_text else True
        is_valid = has_name and has_valid_ip
        if not has_name:
            self.error_label.setText(t("validation.device_name_required"))
        elif not has_valid_ip:
            self.error_label.setText(t("validation.invalid_ip"))
        else:
            self.error_label.setText("")
        save_button = self.button_box.button(QDialogButtonBox.StandardButton.Save)
        if save_button is not None:
            save_button.setEnabled(is_valid)

    def get_linked_device_ids(self) -> list[str]:
        """Return checked upstream target ids from the dialog."""
        ordered_ids = [device.id for device in self.available_devices if device.id in self.checked_link_ids]
        remaining_ids = sorted(self.checked_link_ids.difference(ordered_ids))
        return [*ordered_ids, *remaining_ids]

    def get_removed_incoming_device_ids(self) -> list[str]:
        """Return incoming source ids that were unchecked in the connection dialog."""
        ordered_ids = [device.id for device in self.available_devices if device.id in self.removed_incoming_device_ids]
        remaining_ids = sorted(self.removed_incoming_device_ids.difference(ordered_ids))
        return [*ordered_ids, *remaining_ids]

    def manage_connections(self) -> None:
        """Open the dedicated connection editor."""
        current_device = replace(
            self.camera,
            name=self.name_input.text().strip() or self.camera.name,
            ip_address=self.ip_input.text().strip(),
            device_kind=str(self.kind_input.currentData() or self.camera.device_kind),
            variant=str(self.variant_input.currentData() or self.camera.effective_variant()),
        )
        dialog = DeviceConnectionsDialog(
            current_device,
            self.available_devices,
            self.checked_link_ids,
            self.incoming_device_ids,
            self.parent_ip_lookup,
            self,
        )
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.checked_link_ids = set(dialog.get_linked_device_ids())
            self.removed_incoming_device_ids = set(dialog.get_removed_incoming_device_ids())
            self.incoming_device_ids.difference_update(self.removed_incoming_device_ids)

    def upload_location_image(self) -> None:
        """Select a source image and preview it before saving."""
        file_path, _ = QFileDialog.getOpenFileName(self, t("dialog.choose_location_image.title"), "", t("dialog.image.filter"))
        if not file_path:
            return
        if not is_supported_image(file_path):
            self.error_label.setText(t("error.location_image_invalid"))
            return
        self.pending_location_source = file_path
        self.location_image_path = file_path
        self._refresh_location_preview()

    def remove_location_image(self) -> None:
        """Clear the location image from the edited camera."""
        self.pending_location_source = ""
        self.location_image_path = ""
        self._refresh_location_preview()

    def _location_image_row(self) -> QWidget:
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        text_layout = QVBoxLayout()
        text_layout.addWidget(self.location_path_label)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.upload_location_button)
        button_layout.addWidget(self.remove_location_button)
        text_layout.addLayout(button_layout)
        layout.addWidget(self.location_preview)
        layout.addLayout(text_layout)
        return row

    def _status_ping_row(self) -> QWidget:
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ping_input)
        layout.addStretch(1)
        return row

    def _refresh_location_preview(self) -> None:
        if self.location_image_path and Path(self.location_image_path).exists():
            pixmap = QPixmap(self.location_image_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.location_preview.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.location_preview.setPixmap(scaled)
            else:
                self.location_preview.setText(t("camera_dialog.no_location_image"))
            self.location_path_label.setText(Path(self.location_image_path).name)
        else:
            self.location_preview.setPixmap(QPixmap())
            self.location_preview.setText(t("camera_dialog.no_location_image"))
            self.location_path_label.setText(t("camera_dialog.no_location_image"))

    def _ip_validator(self) -> QRegularExpressionValidator:
        octet = r"(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
        regex = QRegularExpression(rf"^{octet}\.{octet}\.{octet}\.{octet}$")
        return QRegularExpressionValidator(regex, self)

    def retranslate(self) -> None:
        """Refresh dialog text for the active language."""
        self.setWindowTitle(t("device_dialog.title"))
        self.name_label.setText(t("device_dialog.name"))
        self.badge_label.setText(t("device_dialog.badge"))
        self.kind_label.setText(t("device_dialog.kind"))
        self.ip_label.setText(t("camera_dialog.ip"))
        self.port_label.setText(t("camera_dialog.port"))
        self.type_label.setText(t("device_dialog.variant"))
        self.fov_label.setText(t("camera_dialog.fov"))
        self.zone_label.setText(t("camera_dialog.zone"))
        self.status_label.setText(t("camera_dialog.status"))
        self.ping_input.setText(t("device_dialog.ping_enabled"))
        self.notes_label.setText(t("camera_dialog.notes"))
        self.location_image_label.setText(t("camera_dialog.location_image"))
        self.connections_label.setText(t("device_dialog.connections"))
        self.manage_connections_button.setText(t("device_dialog.manage_connections"))
        self.upload_location_button.setText(t("camera_dialog.upload_location_image"))
        self.remove_location_button.setText(t("camera_dialog.remove_location_image"))
        self._retranslate_device_kinds()
        self._retranslate_variants()
        self._populate_fov_values()

        save_button = self.button_box.button(QDialogButtonBox.StandardButton.Save)
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if save_button is not None:
            save_button.setText(t("camera_dialog.save"))
        if cancel_button is not None:
            cancel_button.setText(t("camera_dialog.cancel"))

    def _retranslate_device_kinds(self) -> None:
        current_value = self.kind_input.currentData() or self.camera.device_kind
        self.kind_input.blockSignals(True)
        self.kind_input.clear()
        for value in DEVICE_KINDS:
            self.kind_input.addItem(device_kind_label(value), value)
            if value == current_value:
                self.kind_input.setCurrentIndex(self.kind_input.count() - 1)
        self.kind_input.blockSignals(False)

    def _retranslate_variants(self) -> None:
        current_kind = str(self.kind_input.currentData() or self.camera.device_kind)
        current_value = self.variant_input.currentData() or self.camera.effective_variant()
        self.variant_input.blockSignals(True)
        self.variant_input.clear()
        for value in variants_for_kind(current_kind):
            self.variant_input.addItem(device_variant_label(value), value)
            if value == current_value:
                self.variant_input.setCurrentIndex(self.variant_input.count() - 1)
        self.variant_input.blockSignals(False)

    def _handle_kind_changed(self) -> None:
        self._retranslate_variants()
        kind = self.kind_input.currentData()
        is_camera = kind == DEVICE_KIND_CAMERA
        self.fov_label.setVisible(is_camera)
        self.fov_input.setVisible(is_camera)
        if kind != DEVICE_KIND_CAMERA and not self.camera.name:
            self.ip_input.clear()
            self.ping_input.setChecked(False)
        self._update_save_state()

    def _handle_ip_changed(self, value: str) -> None:
        if not value.strip():
            self.ping_input.setChecked(False)
        self._update_save_state()

    def _normalize_badge_text(self, value: str) -> None:
        normalized = value.strip().upper()[:3]
        if value != normalized:
            self.badge_input.blockSignals(True)
            self.badge_input.setText(normalized)
            self.badge_input.blockSignals(False)

    def _populate_fov_values(self) -> None:
        current_value = int(self.fov_input.currentData() or self.camera.fov_degrees or 80)
        self.fov_input.blockSignals(True)
        self.fov_input.clear()
        for value in (80, 180, 360):
            self.fov_input.addItem(f"{value}°", value)
            if value == current_value:
                self.fov_input.setCurrentIndex(self.fov_input.count() - 1)
        self.fov_input.blockSignals(False)
        is_camera = self.kind_input.currentData() == DEVICE_KIND_CAMERA
        self.fov_label.setVisible(is_camera)
        self.fov_input.setVisible(is_camera)
