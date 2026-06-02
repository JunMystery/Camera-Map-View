"""Settings and theme actions for the main window."""

from config.i18n import t
from views.settings_dialog import SettingsDialog


class AppSettingsActions:
    """Apply settings dialog values to services and canvas."""

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        self.settings.update(dialog.values())
        self.ping_service.update_settings(
            int(self.settings["ping_interval"]),
            float(self.settings["ping_timeout"]),
            int(self.settings["ping_retries"]),
        )
        self.map_canvas.resize_canvas(int(self.settings["canvas_width"]), int(self.settings["canvas_height"]))
        self.map_canvas.redraw_grid(int(self.settings["grid_size"]))
        self.map_canvas.set_background_scale(float(self.settings["background_scale"]))
        self.save_current_layout_state()
        self.apply_theme()

    def apply_theme(self) -> None:
        """Apply the current application theme."""
        light_theme = bool(self.settings["light_theme"])
        self.map_canvas.set_light_theme(light_theme)
        if light_theme:
            self.setStyleSheet("QWidget { background: #f8fafc; color: #111827; }")
        else:
            self.setStyleSheet("")

    def add_widget_reopen_actions(self) -> None:
        """Add menu actions that reopen dock widgets after users close them."""
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.dock.toggleViewAction())
        self.view_menu.addAction(self.layouts_dock.toggleViewAction())
        self.view_menu.addAction(self.tools_dock.toggleViewAction())
        self.view_menu.addAction(self.layers_dock.toggleViewAction())
