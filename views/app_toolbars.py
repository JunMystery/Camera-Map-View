"""Main toolbar construction for the application window."""

from PyQt6.QtWidgets import QToolBar

from config.i18n import t


class AppToolbars:
    """Manage the single main toolbar."""

    def init_main_toolbar(self) -> None:
        """Create a single compact toolbar for map, zoom, and settings actions."""
        self.toolbar = QToolBar(self)
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        self.toolbar.addAction(self.open_action)
        self.toolbar.addAction(self.unload_map_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.zoom_in_action)
        self.toolbar.addAction(self.zoom_out_action)
        self.toolbar.addAction(self.zoom_fit_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.settings_action)

    def retranslate_toolbars(self) -> None:
        """Refresh toolbar title."""
        self.toolbar.setWindowTitle(t("toolbar.main"))
