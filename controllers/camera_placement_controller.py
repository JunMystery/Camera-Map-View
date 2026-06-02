"""Controller for camera placement workflow between model and view objects."""

from collections.abc import Callable

from config.i18n import t
from controllers.camera_data_manager import CameraDataManager
from views.camera_view_panel import CameraPanel
from views.camera_view_dialog import CameraPropertiesDialog
from views.map_view_canvas import MapCanvas


class CameraPlacementController:
    """Coordinate camera data with the sidebar and map canvas."""

    def __init__(
        self,
        camera_panel: CameraPanel,
        map_canvas: MapCanvas,
        camera_manager: CameraDataManager,
        status_callback: Callable[[str, int], None] | None = None,
        monitor_refresh_callback: Callable[[], None] | None = None,
        dashboard_refresh_callback: Callable[[], None] | None = None,
    ) -> None:
        self.camera_panel = camera_panel
        self.map_canvas = map_canvas
        self.camera_manager = camera_manager
        self.status_callback = status_callback
        self.monitor_refresh_callback = monitor_refresh_callback
        self.dashboard_refresh_callback = dashboard_refresh_callback
        self.current_layout_id = "default"

        self.map_canvas.camera_dropped.connect(self.handle_camera_dropped)
        self.map_canvas.camera_edit_requested.connect(self.edit_camera)
        self.map_canvas.camera_moved.connect(self.update_camera_position)
        self.map_canvas.camera_rotated.connect(self.camera_manager.update_camera_rotation)
        self.map_canvas.camera_resized.connect(self.camera_manager.update_camera_scale)
        self.map_canvas.camera_deleted.connect(self.unplace_camera)
        self.map_canvas.object_layer_changed.connect(self.update_object_layer)
        self.map_canvas.drawing_created.connect(self.add_drawing_shape)
        self.map_canvas.drawing_updated.connect(self.update_drawing_shape)
        self.map_canvas.drawing_deleted.connect(self.camera_manager.delete_drawing_shape)
        self.camera_panel.camera_edit_requested.connect(self.edit_camera)
        self.camera_panel.camera_delete_requested.connect(self.delete_camera)

    def load_cameras(self, layout_id: str | None = None) -> None:
        """Load persisted cameras into the sidebar and map."""
        if layout_id is not None:
            self.current_layout_id = layout_id
        self.map_canvas.clear_map_items()
        self.camera_manager.seed_default_cameras(self.current_layout_id)
        self.map_canvas.set_canvas_layers(self.camera_manager.get_layers(self.current_layout_id), self.current_layout_id)
        placed_cameras = self.camera_manager.get_placed_cameras(self.current_layout_id)
        self.camera_panel.set_cameras(
            self.camera_manager.get_all_cameras(self.current_layout_id),
            {camera.id for camera in placed_cameras},
        )

        for camera in placed_cameras:
            self.map_canvas.add_camera_item(camera)

        for shape in self.camera_manager.get_drawing_shapes(self.current_layout_id):
            self.map_canvas.add_drawing_shape(shape)

        self._refresh_dashboard()

    def handle_camera_dropped(self, camera_id: str, x: float, y: float) -> None:
        """Place a sidebar camera onto the map at the drop coordinates."""
        camera = self.camera_panel.remove_camera_from_list(camera_id)
        if camera is None:
            return

        camera.position_x = x
        camera.position_y = y
        camera.layer_id = self._target_layer_for_camera()

        self.camera_manager.update_camera_position(camera.id, x, y)
        if camera.layer_id:
            self.camera_manager.update_camera_layer(camera.id, camera.layer_id)
        self.map_canvas.add_camera_item(camera)
        self._refresh_dashboard()
        self._show_status(
            t("status.camera_placed", name=camera.name, x=int(x), y=int(y)),
            5000,
        )

    def update_camera_position(self, camera_id: str, x: float, y: float) -> None:
        """Persist direct movement of an already placed camera item."""
        self.camera_manager.update_camera_position(camera_id, x, y)

    def handle_camera_status_updated(self, camera_id: str, is_online: bool, latency_ms: float) -> None:
        """Persist ping results and update any visible camera marker."""
        if not self.camera_manager.update_camera_status(camera_id, is_online, latency_ms):
            return

        self.map_canvas.update_camera_status(camera_id, is_online)
        self._refresh_dashboard()
        status_key = "camera.status.online" if is_online else "camera.status.offline"
        self._show_status(
            t("status.camera_ping", camera_id=camera_id, status=t(status_key), latency_ms=latency_ms),
            3000,
        )

    def edit_camera(self, camera_id: str) -> None:
        """Open the camera properties dialog and persist accepted changes."""
        camera = self.camera_manager.get_camera(camera_id)
        if camera is None:
            return

        dialog = CameraPropertiesDialog(camera, self.map_canvas.window())
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        updated_camera = dialog.get_camera()
        if not self.camera_manager.update_camera_details(updated_camera):
            self._show_status(t("status.camera_update_failed"), 5000)
            return

        self.map_canvas.refresh_camera_item(updated_camera)
        self.camera_panel.set_cameras(
            self.camera_manager.get_all_cameras(self.current_layout_id),
            {camera.id for camera in self.camera_manager.get_placed_cameras(self.current_layout_id)},
        )
        if self.monitor_refresh_callback is not None:
            self.monitor_refresh_callback()
        self._show_status(t("status.camera_updated", name=updated_camera.name), 5000)

    def delete_camera(self, camera_id: str) -> None:
        """Delete a camera from storage and visible views."""
        if not self.camera_manager.delete_camera(camera_id):
            return
        self.map_canvas.remove_camera_item(camera_id)
        self.camera_panel.set_cameras(
            self.camera_manager.get_all_cameras(self.current_layout_id),
            {camera.id for camera in self.camera_manager.get_placed_cameras(self.current_layout_id)},
        )
        if self.monitor_refresh_callback is not None:
            self.monitor_refresh_callback()
        self._refresh_dashboard()

    def unplace_camera(self, camera_id: str) -> None:
        """Remove a camera marker from the canvas while keeping the camera record."""
        if not self.camera_manager.unplace_camera(camera_id):
            return
        self.map_canvas.remove_camera_item(camera_id)
        self.camera_panel.set_cameras(
            self.camera_manager.get_all_cameras(self.current_layout_id),
            {camera.id for camera in self.camera_manager.get_placed_cameras(self.current_layout_id)},
        )
        self._refresh_dashboard()

    def _show_status(self, message: str, timeout_ms: int) -> None:
        if self.status_callback is not None:
            self.status_callback(message, timeout_ms)

    def _refresh_dashboard(self) -> None:
        if self.dashboard_refresh_callback is not None:
            self.dashboard_refresh_callback()

    def add_drawing_shape(self, shape: object) -> bool:
        """Persist drawings into the active layout."""
        return self.camera_manager.add_drawing_shape(shape, self.current_layout_id)

    def update_drawing_shape(self, shape: object) -> bool:
        """Persist edited drawings into the active layout."""
        return self.camera_manager.update_drawing_shape(shape, self.current_layout_id)

    def update_object_layer(self, object_type: str, object_id: str, layer_id: str) -> None:
        """Persist a canvas object layer assignment."""
        if object_type == "camera":
            self.camera_manager.update_camera_layer(object_id, layer_id)
        elif object_type == "drawing":
            self.camera_manager.update_drawing_shape_layer(object_id, layer_id)

    def _target_layer_for_camera(self) -> str:
        return self.map_canvas.active_layer_id or self.camera_manager.first_layer_id(self.current_layout_id)
