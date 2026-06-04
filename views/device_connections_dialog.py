"""Dialog for editing directed device topology links."""

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from config.i18n import t
from models.camera_data_model import Camera
from models.device_catalog import device_kind_label, device_variant_label
from views.tool_icons import device_icon

LINK_SEARCH_ROLE = Qt.ItemDataRole.UserRole.value + 1


class DeviceConnectionsDialog(QDialog):
    """Manage outgoing and incoming links for one device."""

    def __init__(
        self,
        current_device: Camera,
        available_devices: list[Camera],
        linked_device_ids: set[str],
        incoming_device_ids: set[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.current_device = current_device
        self.available_devices = [device for device in available_devices if device.id != current_device.id]
        self.checked_link_ids = set(linked_device_ids)
        self.incoming_device_ids = set(incoming_device_ids)
        self.removed_incoming_ids: set[str] = set()
        self.resize(560, 520)

        self.search_input = QLineEdit(self)
        self.search_input.textChanged.connect(self._filter_links)
        self.outgoing_label = QLabel(self)
        self.incoming_label = QLabel(self)
        self.outgoing_list = QListWidget(self)
        self.outgoing_list.setAlternatingRowColors(True)
        self.outgoing_list.setSortingEnabled(False)
        self.outgoing_list.itemChanged.connect(self._handle_link_item_changed)
        self.incoming_list = QListWidget(self)
        self.incoming_list.setAlternatingRowColors(True)
        self.incoming_list.setSortingEnabled(False)
        self.incoming_list.itemChanged.connect(self._handle_incoming_item_changed)
        for list_widget in (self.outgoing_list, self.incoming_list):
            list_widget.setSpacing(2)
            list_widget.setStyleSheet(
                """
                QListWidget::item {
                    padding: 6px 8px;
                    border-bottom: 1px solid rgba(148, 163, 184, 0.35);
                }
                QListWidget::item:alternate {
                    background: rgba(148, 163, 184, 0.10);
                }
                """
            )
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self._build_layout()
        self.retranslate()
        self._populate_links()

    def get_linked_device_ids(self) -> list[str]:
        """Return outgoing link ids in available-device order."""
        ordered_ids = [device.id for device in self.available_devices if device.id in self.checked_link_ids]
        remaining_ids = sorted(self.checked_link_ids.difference(ordered_ids))
        return [*ordered_ids, *remaining_ids]

    def get_removed_incoming_device_ids(self) -> list[str]:
        """Return source ids whose incoming link should be removed."""
        ordered_ids = [device.id for device in self.available_devices if device.id in self.removed_incoming_ids]
        remaining_ids = sorted(self.removed_incoming_ids.difference(ordered_ids))
        return [*ordered_ids, *remaining_ids]

    def retranslate(self) -> None:
        """Refresh translated strings."""
        self.setWindowTitle(t("device_connections.title", name=self.current_device.name))
        self.search_input.setPlaceholderText(t("device_dialog.link_search"))
        self.outgoing_label.setText(t("device_connections.links_to"))
        self.incoming_label.setText(t("device_connections.linked_from"))
        save_button = self.button_box.button(QDialogButtonBox.StandardButton.Save)
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if save_button is not None:
            save_button.setText(t("camera_dialog.save"))
        if cancel_button is not None:
            cancel_button.setText(t("camera_dialog.cancel"))

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.addWidget(self.search_input)
        layout.addWidget(self.outgoing_label)
        layout.addWidget(self.outgoing_list, 1)
        layout.addWidget(self.incoming_label)
        layout.addWidget(self.incoming_list, 1)
        layout.addWidget(self.button_box)

    def _populate_links(self) -> None:
        self.outgoing_list.blockSignals(True)
        self.incoming_list.blockSignals(True)
        self.outgoing_list.clear()
        self.incoming_list.clear()
        for device in self.available_devices:
            label = self._device_label(device)
            outgoing = QListWidgetItem(device_icon(device.device_kind), label)
            outgoing.setData(Qt.ItemDataRole.UserRole, device.id)
            outgoing.setData(LINK_SEARCH_ROLE, self._device_search_text(device, label))
            outgoing.setSizeHint(QSize(0, 34))
            outgoing.setCheckState(Qt.CheckState.Checked if device.id in self.checked_link_ids else Qt.CheckState.Unchecked)
            self.outgoing_list.addItem(outgoing)
            if device.id in self.incoming_device_ids:
                incoming = QListWidgetItem(device_icon(device.device_kind), label)
                incoming.setData(Qt.ItemDataRole.UserRole, device.id)
                incoming.setData(LINK_SEARCH_ROLE, self._device_search_text(device, label))
                incoming.setSizeHint(QSize(0, 34))
                incoming.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsUserCheckable
                )
                incoming.setCheckState(Qt.CheckState.Unchecked if device.id in self.removed_incoming_ids else Qt.CheckState.Checked)
                self.incoming_list.addItem(incoming)
        self.outgoing_list.blockSignals(False)
        self.incoming_list.blockSignals(False)
        self._filter_links()

    def _handle_link_item_changed(self, item: QListWidgetItem) -> None:
        device_id = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not device_id:
            return
        if item.checkState() == Qt.CheckState.Checked:
            self.checked_link_ids.add(device_id)
            return
        self.checked_link_ids.discard(device_id)

    def _handle_incoming_item_changed(self, item: QListWidgetItem) -> None:
        device_id = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not device_id:
            return
        if item.checkState() == Qt.CheckState.Checked:
            self.removed_incoming_ids.discard(device_id)
            return
        self.removed_incoming_ids.add(device_id)

    def _filter_links(self) -> None:
        query = self.search_input.text().strip().lower()
        for list_widget in (self.outgoing_list, self.incoming_list):
            for index in range(list_widget.count()):
                item = list_widget.item(index)
                haystack = str(item.data(LINK_SEARCH_ROLE) or "").lower()
                item.setHidden(bool(query) and query not in haystack)

    def _device_label(self, device: Camera) -> str:
        label = f"{device.name} ({device_kind_label(device.device_kind)})"
        if device.ip_address:
            label = f"{label} - {device.ip_address}"
        return label

    def _device_search_text(self, device: Camera, label: str) -> str:
        return " ".join(
            [
                label,
                device.name,
                device.ip_address,
                device.dvr_origin,
                device.zone,
                device.device_kind,
                device.variant,
                device_kind_label(device.device_kind),
                device_variant_label(device.effective_variant()),
            ]
        )
