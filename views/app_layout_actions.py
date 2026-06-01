"""Map layout management actions for the main window."""

from PyQt6.QtWidgets import QInputDialog

from config.i18n import t
from models.map_layout_model import MapLayout


class AppLayoutActions:
    """Create, switch, rename, delete, and persist map layouts."""

    current_layout_id = "default"

    def refresh_layouts_panel(self) -> None:
        """Refresh layout choices."""
        self.layouts_panel.set_layouts(self.camera_manager.get_layouts(), self.current_layout_id)

    def switch_layout(self, layout_id: str) -> None:
        """Switch the workspace to another layout."""
        self.save_current_layout_state()
        self.current_layout_id = layout_id
        layout = self.camera_manager.get_layout(layout_id)
        if layout is not None:
            self.apply_layout_to_canvas(layout)
        self.camera_controller.load_cameras(layout_id)
        self.refresh_ping_cameras()
        self.refresh_status_dashboard()

    def add_layout(self) -> None:
        """Create a new blank layout."""
        name, accepted = QInputDialog.getText(self, t("layout.add"), t("layout.name"))
        if not accepted or not name.strip():
            return
        layout = self.camera_manager.create_layout(name.strip())
        self.current_layout_id = layout.id
        self.refresh_layouts_panel()
        self.switch_layout(layout.id)

    def rename_layout(self, layout_id: str) -> None:
        """Rename an existing layout."""
        layout = self.camera_manager.get_layout(layout_id)
        if layout is None:
            return
        name, accepted = QInputDialog.getText(self, t("layout.rename"), t("layout.name"), text=layout.name)
        if accepted and name.strip():
            layout.name = name.strip()
            self.camera_manager.update_layout(layout)
            self.refresh_layouts_panel()

    def delete_layout(self, layout_id: str) -> None:
        """Delete a layout and switch back to default."""
        if self.camera_manager.delete_layout(layout_id):
            self.current_layout_id = "default"
            self.refresh_layouts_panel()
            self.switch_layout("default")

    def apply_layout_to_canvas(self, layout: MapLayout) -> None:
        """Apply layout settings to the canvas."""
        self.settings.update(
            {
                "canvas_width": layout.canvas_width,
                "canvas_height": layout.canvas_height,
                "grid_size": layout.grid_size,
                "background_scale": layout.background_scale,
            }
        )
        self.map_canvas.background_scale = layout.background_scale
        self.current_background_path = layout.background_path
        if layout.background_path:
            self.map_canvas.load_background_image(layout.background_path)
        else:
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
        layout.background_path = getattr(self, "current_background_path", layout.background_path)
        self.camera_manager.update_layout(layout)
