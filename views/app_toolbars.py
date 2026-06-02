"""Two-level toolbar construction for the main application window."""

from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import QToolBar

from config.i18n import t


class AppToolbars:
    """Manage primary toolbar groups and their contextual actions."""

    def init_two_level_toolbar(self) -> None:
        """Create a compact primary toolbar and contextual secondary toolbar."""
        self.toolbar_group_actions = {
            "map": [self.open_action, self.unload_map_action, self.settings_action],
            "draw": [
                self.select_action,
                self.draw_line_action,
                self.draw_rectangle_action,
                self.draw_zone_action,
                self.draw_freehand_action,
            ],
            "annotate": [
                self.add_text_action,
                self.insert_png_action,
                self.choose_color_action,
                self.delete_selected_action,
                self.rotate_camera_action,
            ],
            "view": [self.zoom_in_action, self.zoom_out_action, self.zoom_fit_action, self.grid_action, *self.info_actions.values()],
        }

        self.toolbar_group = QActionGroup(self)
        self.toolbar_group.setExclusive(True)
        self.toolbar_group_selectors: dict[str, QAction] = {}

        self.toolbar = QToolBar(self)
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        for group_id in self.toolbar_group_actions:
            action = QAction(self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, item=group_id: self.set_toolbar_group(item))
            self.toolbar_group.addAction(action)
            self.toolbar_group_selectors[group_id] = action
            self.toolbar.addAction(action)

        self.context_toolbar = QToolBar(self)
        self.context_toolbar.setMovable(False)
        self.addToolBar(self.context_toolbar)
        self.set_toolbar_group("map")

    def set_toolbar_group(self, group_id: str) -> None:
        """Switch the secondary toolbar to the selected action group."""
        if group_id not in self.toolbar_group_actions:
            return
        self.toolbar_group_selectors[group_id].setChecked(True)
        self.context_toolbar.clear()
        for action in self.toolbar_group_actions[group_id]:
            self.context_toolbar.addAction(action)

    def retranslate_toolbars(self) -> None:
        """Refresh toolbar titles and group labels."""
        self.toolbar.setWindowTitle(t("toolbar.main"))
        self.context_toolbar.setWindowTitle(t("toolbar.context"))
        for group_id, action in self.toolbar_group_selectors.items():
            action.setText(t(f"toolbar.group.{group_id}"))
