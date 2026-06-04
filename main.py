"""Application entrypoint for the Camera Map Manager desktop app."""

import sys

from PyQt6.QtWidgets import QApplication

from config.i18n import t
from views.app_view_window import MainWindow


def main() -> None:
    """Start the PyQt application."""
    app = QApplication(sys.argv)
    app.setApplicationName(t("app.title"))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

"""
 * Copyright (c) 2026 JunMystery. All rights reserved.
 * Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
 * Commercial use is strictly prohibited without prior written permission.
"""