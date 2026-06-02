"""Compact one-line dashboard for aggregate camera status counts."""

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from config.i18n import t


class StatusDashboard(QWidget):
    """Show total, online, and offline camera counts."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.total = 0
        self.online = 0
        self.offline = 0
        self.summary_label = QLabel(self)
        self.summary_label.setWordWrap(False)
        self.summary_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.total_label = self.summary_label

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.addWidget(self.summary_label)
        self.retranslate()

    def update_counts(self, total: int, online: int, offline: int) -> None:
        """Refresh visible aggregate counts."""
        self.total = total
        self.online = online
        self.offline = offline
        self.retranslate()

    def retranslate(self) -> None:
        """Refresh labels for the active language."""
        self.summary_label.setText(
            f"{t('dashboard.total', total=self.total)}  "
            f"{t('dashboard.online', online=self.online)}  "
            f"{t('dashboard.offline', offline=self.offline)}"
        )
