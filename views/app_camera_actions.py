"""Camera CRUD and CSV actions for the main window."""

import uuid

from PyQt6.QtWidgets import QFileDialog

from config.i18n import t
from models.camera_data_model import Camera
from views.camera_view_dialog import CameraPropertiesDialog


class AppCameraActions:
    """Provide camera creation and CSV import/export actions."""

    def add_camera(self) -> None:
        """Create a new device from the device dialog."""
        if not self.current_layout_id:
            self.status_bar.showMessage(t("status.no_layout"), 7000)
            return
        camera = Camera(f"dev_{uuid.uuid4().hex[:8]}", "", "", status=False, ping_enabled=False)
        dialog = CameraPropertiesDialog(camera, self, self.camera_manager.get_all_cameras(self.current_layout_id), [], [])
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        new_camera = dialog.get_camera()
        if self.camera_manager.add_camera(new_camera, layout_id=self.current_layout_id):
            self.camera_manager.replace_device_links(new_camera.id, dialog.get_linked_device_ids(), self.current_layout_id)
            self._refresh_camera_panel()
            self.refresh_ping_cameras()
            self.refresh_status_dashboard()
            self.map_canvas.set_device_catalog(self.camera_manager.get_all_cameras(self.current_layout_id))
            self.map_canvas.set_device_links(self.camera_manager.get_device_links(self.current_layout_id))
            self.status_bar.showMessage(t("status.device_updated", name=new_camera.name), 5000)
        else:
            self.status_bar.showMessage(t("status.camera_update_failed"), 5000)

    def import_cameras_csv(self) -> None:
        """Import camera records from CSV."""
        if not self.current_layout_id:
            self.status_bar.showMessage(t("status.no_layout"), 7000)
            return
        file_path, _ = QFileDialog.getOpenFileName(self, t("dialog.choose_csv.title"), "", t("dialog.choose_csv.filter"))
        if file_path:
            count = self.camera_manager.import_cameras_csv(file_path, self.current_layout_id)
            self._refresh_camera_panel()
            self.map_canvas.set_device_catalog(self.camera_manager.get_all_cameras(self.current_layout_id))
            for camera in self.camera_manager.get_placed_cameras(self.current_layout_id):
                self.map_canvas.refresh_camera_item(camera)
            self.map_canvas.set_device_links(self.camera_manager.get_device_links(self.current_layout_id))
            self.refresh_ping_cameras()
            self.refresh_status_dashboard()
            self.status_bar.showMessage(t("status.csv_imported", count=count), 5000)

    def export_cameras_csv(self) -> None:
        """Export camera records to CSV."""
        if not self.current_layout_id:
            self.status_bar.showMessage(t("status.no_layout"), 7000)
            return
        file_path, _ = QFileDialog.getSaveFileName(self, t("dialog.save_csv.title"), "", t("dialog.choose_csv.filter"))
        if file_path:
            self.camera_manager.export_cameras_csv(file_path, self.current_layout_id)
            self.status_bar.showMessage(t("status.csv_exported"), 5000)

    def _refresh_camera_panel(self) -> None:
        cameras = self.camera_manager.get_all_cameras(self.current_layout_id)
        self.camera_panel.set_cameras(
            cameras,
            {item.id for item in self.camera_manager.get_placed_cameras(self.current_layout_id)},
            self.camera_manager.get_device_links(self.current_layout_id),
        )
        if hasattr(self, "map_canvas"):
            self.map_canvas.set_device_catalog(cameras)
