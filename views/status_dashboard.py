"""Compact dashboard for aggregate camera status counts."""

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from config.i18n import t


class StatusDashboard(QWidget):
    """Show total, online, and offline camera counts."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.total = 0
        self.online = 0
        self.offline = 0
        self.total_label = QLabel(self)
        self.online_label = QLabel(self)
        self.offline_label = QLabel(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.addWidget(self.total_label)
        layout.addWidget(self.online_label)
        layout.addWidget(self.offline_label)
        layout.addStretch()
        self.retranslate()

    def update_counts(self, total: int, online: int, offline: int) -> None:
        """Refresh visible aggregate counts."""
        self.total = total
        self.online = online
        self.offline = offline
        self.retranslate()

    def retranslate(self) -> None:
        """Refresh labels for the active language."""
        self.total_label.setText(t("dashboard.total", total=self.total))
        self.online_label.setText(t("dashboard.online", online=self.online))
        self.offline_label.setText(t("dashboard.offline", offline=self.offline))
