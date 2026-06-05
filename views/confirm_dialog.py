"""Reusable confirmation dialog with fixed button order and destructive No style."""

from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from config.i18n import t
from views.ui_theme import DANGER, TEXT_WHITE

CONFIRM_BUTTON_WIDTH = 96


class ConfirmDialog(QDialog):
    """Show Yes on the left and a red No button on the right."""

    def __init__(self, title: str, message: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle(title)
        self.message_label = QLabel(message, self)
        self.message_label.setWordWrap(True)
        self.yes_button = QPushButton(t("button.yes"), self)
        self.no_button = QPushButton(t("button.no"), self)
        for button in (self.yes_button, self.no_button):
            button.setMinimumWidth(CONFIRM_BUTTON_WIDTH)
            button.setFixedHeight(34)
        self.no_button.setObjectName("confirmNoButton")
        self.no_button.setStyleSheet(
            f"""
            QPushButton#confirmNoButton {{
                background: {DANGER};
                color: {TEXT_WHITE};
                border: 1px solid #b91c1c;
                border-radius: 5px;
                padding: 6px 16px;
                font-weight: 700;
            }}
            QPushButton#confirmNoButton:hover {{
                background: #dc2626;
            }}
            QPushButton#confirmNoButton:pressed {{
                background: #991b1b;
            }}
            """
        )
        self.yes_button.clicked.connect(self.accept)
        self.no_button.clicked.connect(self.reject)
        self.yes_button.setDefault(True)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.yes_button)
        button_row.addWidget(self.no_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)
        layout.addWidget(self.message_label)
        layout.addLayout(button_row)
        self.resize(360, 130)


def confirm(parent: QWidget | None, title: str, message: str) -> bool:
    """Return True when the user confirms with Yes."""
    return ConfirmDialog(title, message, parent).exec() == QDialog.DialogCode.Accepted
