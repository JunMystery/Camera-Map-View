"""Settings and theme actions for the main window."""

from config.i18n import t
from services.app_settings_service import save_app_settings
from views.settings_dialog import SettingsDialog
from views.ui_theme import app_stylesheet


class AppSettingsActions:
    """Apply settings dialog values to services and canvas."""

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self, self.apply_theme_choice)
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
        save_app_settings(self.settings)
        self.apply_theme()

    def apply_theme_choice(self, light_theme: bool) -> None:
        """Apply a theme selection immediately from the settings dialog."""
        self.settings["light_theme"] = light_theme
        save_app_settings(self.settings)
        self.apply_theme()

    def apply_theme(self) -> None:
        """Apply the current application theme."""
        light_theme = bool(self.settings["light_theme"])
        self.map_canvas.set_light_theme(light_theme)
        self.setStyleSheet(app_stylesheet(light_theme))
        for panel_name in ("control_panel", "drawing_tools_panel", "layers_panel"):
            panel = getattr(self, panel_name, None)
            if panel is not None and hasattr(panel, "apply_theme"):
                panel.apply_theme(light_theme)

    def add_widget_reopen_actions(self) -> None:
        """Add menu actions that reopen dock widgets after users close them."""
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.dock.toggleViewAction())
        self.drawing_tools_view_action = self.view_menu.addAction(t("dock.drawing_tools"))
        self.drawing_tools_view_action.triggered.connect(self._show_drawing_tools_panel)
        self.view_menu.addAction(self.layers_dock.toggleViewAction())

    def _show_drawing_tools_panel(self) -> None:
        """Show the fixed drawing tools panel from the View menu."""
        self.drawing_tools_panel.show()
        self.drawing_tools_panel.set_collapsed(False)
        self.position_drawing_tools_panel()
