"""Map layout management actions for the main window."""

from config.i18n import t
from models.map_layout_model import MapLayout
from views import confirm_dialog
from views.layout_properties_dialog import LayoutPropertiesDialog


class AppLayoutActions:
    """Create, switch, rename, delete, and persist map layouts."""

    current_layout_id = ""

    def refresh_layouts_panel(self) -> None:
        """Refresh layout choices."""
        self.layouts_panel.set_layouts(self.camera_manager.get_layouts(), self.current_layout_id)
        self._sync_layout_dependent_actions()

    def switch_layout(self, layout_id: str) -> None:
        """Switch the workspace to another layout."""
        if not layout_id or self.camera_manager.get_layout(layout_id) is None:
            self.enter_blank_layout_state()
            return
        self.save_current_layout_state()
        self._clear_canvas_history()
        self.current_layout_id = layout_id
        layout = self.camera_manager.get_layout(layout_id)
        if layout is not None:
            self.apply_layout_to_canvas(layout)
        self.camera_controller.load_cameras(layout_id)
        self.refresh_ping_cameras()
        self.refresh_status_dashboard()
        self.refresh_layouts_panel()

    def add_layout(self) -> None:
        """Create a new blank layout with user-provided canvas settings."""
        draft = MapLayout(id="", name="")
        dialog = LayoutPropertiesDialog(draft, editing=False, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        values = dialog.get_layout()
        layout = self.camera_manager.create_layout(values.name)
        layout.canvas_width = values.canvas_width
        layout.canvas_height = values.canvas_height
        layout.grid_size = values.grid_size
        layout.background_scale = values.background_scale
        layout.background_x = values.background_x
        layout.background_y = values.background_y
        self.camera_manager.update_layout(layout)
        self.refresh_layouts_panel()
        self.switch_layout(layout.id)

    def rename_layout(self, layout_id: str) -> None:
        """Edit an existing layout name and canvas settings."""
        layout = self.camera_manager.get_layout(layout_id)
        if layout is None:
            return
        dialog = LayoutPropertiesDialog(layout, editing=True, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        updated_layout = dialog.get_layout()
        if layout_id == self.current_layout_id:
            self._begin_canvas_history("layout_properties")
            self.camera_manager.update_layout(updated_layout)
            self.apply_layout_to_canvas(updated_layout)
            self._commit_canvas_history("layout_properties")
        else:
            self.camera_manager.update_layout(updated_layout)
        self.refresh_layouts_panel()

    def delete_layout(self, layout_id: str) -> None:
        """Delete a layout and switch to another layout or blank state."""
        layout = self.camera_manager.get_layout(layout_id)
        if layout is None:
            return
        if not confirm_dialog.confirm(self, t("dialog.confirm_delete_layout.title"), t("dialog.confirm_delete_layout.body", name=layout.name)):
            return
        self._clear_canvas_history()
        if self.camera_manager.delete_layout(layout_id):
            layouts = self.camera_manager.get_layouts()
            if layouts:
                self.current_layout_id = layouts[0].id
                self.refresh_layouts_panel()
                self.switch_layout(layouts[0].id)
                return
            self.enter_blank_layout_state()

    def apply_layout_to_canvas(self, layout: MapLayout) -> None:
        """Apply layout settings to the canvas."""
        self.settings.update(
            {
                "canvas_width": layout.canvas_width,
                "canvas_height": layout.canvas_height,
                "grid_size": layout.grid_size,
                "background_scale": layout.background_scale,
                "background_x": layout.background_x,
                "background_y": layout.background_y,
            }
        )
        self.map_canvas.background_scale = layout.background_scale
        self.map_canvas.background_x = layout.background_x
        self.map_canvas.background_y = layout.background_y
        self.map_canvas.grid_size = layout.grid_size
        self.current_background_path = layout.background_path
        if layout.background_path:
            if self.map_canvas.load_background_image(layout.background_path, layout.canvas_width, layout.canvas_height):
                self.map_canvas.redraw_grid(layout.grid_size)
        else:
            self.map_canvas.background_x = 0.0
            self.map_canvas.background_y = 0.0
            self.map_canvas.draw_default_grid(layout.canvas_width, layout.canvas_height, layout.grid_size)

    def save_current_layout_state(self) -> None:
        """Persist current canvas settings into the active layout."""
        layout = self.camera_manager.get_layout(self.current_layout_id)
        if layout is None:
            return
        rect = self.map_canvas.scene.sceneRect()
        layout.canvas_width = int(rect.width())
        layout.canvas_height = int(rect.height())
        layout.grid_size = self.map_canvas.grid_size
        layout.background_scale = self.map_canvas.background_scale
        layout.background_x = self.map_canvas.background_x
        layout.background_y = self.map_canvas.background_y
        layout.background_path = getattr(self, "current_background_path", layout.background_path)
        self.camera_manager.update_layout(layout)

    def enter_blank_layout_state(self) -> None:
        """Clear layout-scoped UI when no layout exists."""
        self.current_layout_id = ""
        self.current_background_path = ""
        self._clear_canvas_history()
        self.map_canvas.clear_map_items()
        self.map_canvas.show_blank_canvas()
        self.map_canvas.set_canvas_layers([], "")
        self.camera_controller.load_cameras("")
        self.refresh_layouts_panel()
        self.refresh_ping_cameras()
        self.refresh_status_dashboard()
        self.status_bar.showMessage(t("status.no_layout"), 7000)
