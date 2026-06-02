"""Main-window actions for portable map package import and export."""

from config.i18n import t
from services.map_package_service import export_map_package, import_map_package
from PyQt6.QtWidgets import QFileDialog, QMessageBox


class AppPackageActions:
    """Export and import the active map layout as a single package file."""

    def export_current_map_package(self) -> None:
        """Prompt for a package path and export the active layout."""
        layout = self.camera_manager.get_layout(self.current_layout_id)
        if layout is None:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t("dialog.save_package.title"),
            "",
            t("dialog.package.filter"),
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".cmvmap"):
            file_path = f"{file_path}.cmvmap"
        self.save_current_layout_state()
        layout = self.camera_manager.get_layout(self.current_layout_id)
        if layout is None:
            return
        if not export_map_package(
            file_path,
            layout,
            self.settings.copy(),
            self.map_canvas.camera_info_visibility.copy(),
            self._camera_package_rows(),
            self.camera_manager.get_layers(self.current_layout_id),
            self.camera_manager.get_drawing_shapes(self.current_layout_id),
            self.camera_manager.get_device_links(self.current_layout_id),
        ):
            QMessageBox.critical(self, t("error.package.title"), t("error.package.body"))
            return
        self.status_bar.showMessage(t("status.package_exported"), 5000)

    def import_map_package_file(self) -> None:
        """Prompt for a package file and import it as a new layout."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("dialog.choose_package.title"),
            "",
            t("dialog.package.filter"),
        )
        if not file_path:
            return
        layout_id = import_map_package(file_path, self.camera_manager)
        if not layout_id:
            QMessageBox.critical(self, t("error.package.title"), t("error.package.body"))
            return
        self.refresh_layouts_panel()
        self.switch_layout(layout_id)
        self.status_bar.showMessage(t("status.package_imported"), 5000)

    def _camera_package_rows(self) -> list[dict[str, object]]:
        placed_ids = {camera.id for camera in self.camera_manager.get_placed_cameras(self.current_layout_id)}
        rows = []
        for camera in self.camera_manager.get_all_cameras(self.current_layout_id):
            data = camera.to_dict()
            data["is_placed"] = camera.id in placed_ids
            rows.append(data)
        return rows
