"""Controller for camera placement workflow between model and view objects."""

from collections.abc import Callable
from contextlib import nullcontext
from typing import Any

from config.i18n import t
from controllers.camera_data_manager import CameraDataManager
from services.active_ping_service import open_active_ping
from views.camera_view_panel import CameraPanel
from views.camera_location_image_dialog import CameraLocationImageDialog
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
        history_manager: Any | None = None,
    ) -> None:
        self.camera_panel = camera_panel
        self.map_canvas = map_canvas
        self.camera_manager = camera_manager
        self.status_callback = status_callback
        self.monitor_refresh_callback = monitor_refresh_callback
        self.dashboard_refresh_callback = dashboard_refresh_callback
        self.history_manager = history_manager
        self.current_layout_id = ""

        self.map_canvas.camera_dropped.connect(self.handle_camera_dropped)
        self.map_canvas.camera_edit_requested.connect(self.edit_camera)
        self.map_canvas.camera_location_image_requested.connect(self.show_location_image)
        self.map_canvas.camera_ping_requested.connect(self.ping_camera)
        self.map_canvas.camera_moved.connect(self.update_camera_position)
        self.map_canvas.camera_rotated.connect(self.update_camera_rotation)
        self.map_canvas.camera_resized.connect(self.update_camera_scale)
        self.map_canvas.camera_deleted.connect(self.unplace_camera)
        self.map_canvas.device_link_created.connect(self.add_device_link)
        self.map_canvas.device_link_delete_requested.connect(self.delete_device_link)
        self.map_canvas.object_layer_changed.connect(self.update_object_layer)
        self.map_canvas.object_renamed.connect(self.update_object_name)
        self.map_canvas.object_locked_changed.connect(self.update_object_lock)
        self.map_canvas.object_visibility_changed.connect(self.update_object_visibility)
        self.map_canvas.object_z_changed.connect(self.update_object_z_index)
        self.map_canvas.drawing_created.connect(self.add_drawing_shape)
        self.map_canvas.drawing_updated.connect(self.update_drawing_shape)
        self.map_canvas.drawing_deleted.connect(self.delete_drawing_shape)
        self.camera_panel.camera_edit_requested.connect(self.edit_camera)
        self.camera_panel.camera_delete_requested.connect(self.delete_camera)
        if hasattr(self.camera_panel, "set_device_link_request_handler"):
            self.camera_panel.set_device_link_request_handler(self.add_device_link)
        elif hasattr(self.camera_panel, "device_link_requested"):
            self.camera_panel.device_link_requested.connect(self.add_device_link)
        if hasattr(self.camera_panel, "set_device_unlink_request_handler"):
            self.camera_panel.set_device_unlink_request_handler(self.unlink_devices_from_group)
        elif hasattr(self.camera_panel, "device_unlink_requested"):
            self.camera_panel.device_unlink_requested.connect(self.unlink_devices_from_group)

    def load_cameras(self, layout_id: str | None = None) -> None:
        """Load persisted cameras into the sidebar and map."""
        if layout_id is not None:
            self.current_layout_id = layout_id
        self.map_canvas.clear_map_items()
        if not self.current_layout_id or self.camera_manager.get_layout(self.current_layout_id) is None:
            self.map_canvas.set_canvas_layers([], "")
            self.camera_panel.set_cameras([], set(), [])
            self.map_canvas.set_device_links([])
            self._refresh_dashboard()
            return
        self.camera_manager.seed_default_cameras(self.current_layout_id)
        self.map_canvas.set_canvas_layers(self.camera_manager.get_layers(self.current_layout_id), self.current_layout_id)
        placed_cameras = self.camera_manager.get_placed_cameras(self.current_layout_id)
        device_links = self.camera_manager.get_device_links(self.current_layout_id)
        self.camera_panel.set_cameras(
            self.camera_manager.get_all_cameras(self.current_layout_id),
            {camera.id for camera in placed_cameras},
            device_links,
        )

        for camera in placed_cameras:
            self.map_canvas.add_camera_item(camera)

        for shape in self.camera_manager.get_drawing_shapes(self.current_layout_id):
            self.map_canvas.add_drawing_shape(shape)

        self.map_canvas.set_device_links(device_links)
        self._refresh_dashboard()

    def handle_camera_dropped(self, camera_id: str, x: float, y: float) -> None:
        """Place a sidebar camera onto the map at the drop coordinates."""
        with self._capture_history("camera_drop"):
            camera = self.camera_panel.remove_camera_from_list(camera_id)
            if camera is None:
                return

            camera.position_x = x
            camera.position_y = y
            camera.layer_id = self._target_layer_for_camera()

            if not self.camera_manager.update_camera_position_in_layout(camera.id, x, y, self.current_layout_id):
                return
            if camera.layer_id:
                self.camera_manager.update_camera_layer(camera.id, camera.layer_id, self.current_layout_id)
            self.map_canvas.add_camera_item(camera)
            self._refresh_dashboard()
            self._show_status(
                t("status.camera_placed", name=camera.name, x=int(x), y=int(y)),
                5000,
            )

    def update_camera_position(self, camera_id: str, x: float, y: float) -> None:
        """Persist direct movement of an already placed camera item."""
        self.camera_manager.update_camera_position_in_layout(camera_id, x, y, self.current_layout_id)

    def update_camera_rotation(self, camera_id: str, rotation: float) -> None:
        """Persist direct rotation inside the active layout."""
        self.camera_manager.update_camera_rotation_in_layout(camera_id, rotation, self.current_layout_id)

    def update_camera_scale(self, camera_id: str, display_scale: float) -> None:
        """Persist direct resize inside the active layout."""
        self.camera_manager.update_camera_scale_in_layout(camera_id, display_scale, self.current_layout_id)

    def handle_camera_status_updated(self, camera_id: str, is_online: bool, latency_ms: float) -> None:
        """Persist ping results and update any visible camera marker."""
        if not self.camera_manager.update_camera_status(camera_id, is_online, latency_ms):
            return

        self.map_canvas.update_camera_status(camera_id, is_online)
        self._refresh_camera_panel()
        self._refresh_dashboard()
        status_key = "camera.status.online" if is_online else "camera.status.offline"
        self._show_status(
            t("status.camera_ping", camera_id=camera_id, status=t(status_key), latency_ms=latency_ms),
            3000,
        )

    def edit_camera(self, camera_id: str) -> None:
        """Open the camera properties dialog and persist accepted changes."""
        camera = self.camera_manager.get_camera_in_layout(camera_id, self.current_layout_id)
        if camera is None:
            return

        dialog = CameraPropertiesDialog(
            camera,
            self.map_canvas.window(),
            self.camera_manager.get_all_cameras(self.current_layout_id),
            self.camera_manager.get_linked_device_ids(camera_id, self.current_layout_id),
            self.camera_manager.get_incoming_device_ids(camera_id, self.current_layout_id),
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        with self._capture_history("camera_edit"):
            updated_camera = dialog.get_camera()
            if not self.camera_manager.update_camera_details(updated_camera):
                self._show_status(t("status.camera_update_failed"), 5000)
                return
            self.camera_manager.replace_device_links(updated_camera.id, dialog.get_linked_device_ids(), self.current_layout_id)
            for source_id in dialog.get_removed_incoming_device_ids():
                self.camera_manager.delete_device_link_between(source_id, updated_camera.id, self.current_layout_id)

            self.map_canvas.refresh_camera_item(updated_camera)
            self.map_canvas.set_device_links(self.camera_manager.get_device_links(self.current_layout_id))
            self._refresh_camera_panel()
            if self.monitor_refresh_callback is not None:
                self.monitor_refresh_callback()
            self._show_status(t("status.device_updated", name=updated_camera.name), 5000)

    def show_location_image(self, camera_id: str) -> None:
        """Open the location photo for a camera or its edit dialog when missing."""
        camera = self.camera_manager.get_camera_in_layout(camera_id, self.current_layout_id)
        if camera is None:
            return
        if not camera.location_image_path:
            self._show_status(t("status.location_image_missing", name=camera.name), 5000)
            self.edit_camera(camera_id)
            return
        dialog = CameraLocationImageDialog(camera.location_image_path, camera.name, self.map_canvas.window())
        dialog.exec()

    def ping_camera(self, camera_id: str) -> None:
        """Open a user-managed active ping terminal for one camera."""
        camera = self.camera_manager.get_camera_in_layout(camera_id, self.current_layout_id)
        if camera is None:
            return
        if open_active_ping(camera.ip_address):
            self._show_status(t("status.active_ping_started", ip_address=camera.ip_address), 5000)
            return
        self._show_status(t("status.active_ping_failed", ip_address=camera.ip_address), 5000)

    def delete_camera(self, camera_id: str) -> None:
        """Delete a camera from storage and visible views."""
        with self._capture_history("camera_delete"):
            if not self.camera_manager.delete_camera_in_layout(camera_id, self.current_layout_id):
                return
            self.map_canvas.remove_camera_item(camera_id)
            self.map_canvas.set_device_links(self.camera_manager.get_device_links(self.current_layout_id))
            self._refresh_camera_panel()
            if self.monitor_refresh_callback is not None:
                self.monitor_refresh_callback()
            self._refresh_dashboard()

    def unplace_camera(self, camera_id: str) -> None:
        """Remove a camera marker from the canvas while keeping the camera record."""
        with self._capture_history("camera_unplace"):
            if not self.camera_manager.unplace_camera_in_layout(camera_id, self.current_layout_id):
                return
            self.map_canvas.remove_camera_item(camera_id)
            self._refresh_camera_panel()
            self._refresh_dashboard()

    def _show_status(self, message: str, timeout_ms: int) -> None:
        if self.status_callback is not None:
            self.status_callback(message, timeout_ms)

    def _refresh_dashboard(self) -> None:
        if self.dashboard_refresh_callback is not None:
            self.dashboard_refresh_callback()

    def _refresh_camera_panel(self) -> None:
        """Refresh the sidebar with current devices, placement, and topology links."""
        if not self.current_layout_id:
            self.camera_panel.set_cameras([], set(), [])
            return
        self.camera_panel.set_cameras(
            self.camera_manager.get_all_cameras(self.current_layout_id),
            {camera.id for camera in self.camera_manager.get_placed_cameras(self.current_layout_id)},
            self.camera_manager.get_device_links(self.current_layout_id),
        )

    def add_drawing_shape(self, shape: object) -> bool:
        """Persist drawings into the active layout."""
        with self._capture_history("drawing_create"):
            return self.camera_manager.add_drawing_shape(shape, self.current_layout_id)

    def update_drawing_shape(self, shape: object) -> bool:
        """Persist edited drawings into the active layout."""
        with self._capture_history("drawing_update"):
            return self.camera_manager.update_drawing_shape(shape, self.current_layout_id)

    def delete_drawing_shape(self, shape_id: str) -> bool:
        """Delete a persisted drawing shape inside the active layout history."""
        with self._capture_history("drawing_delete"):
            return self.camera_manager.delete_drawing_shape(shape_id)

    def update_object_layer(self, object_type: str, object_id: str, layer_id: str) -> None:
        """Persist a canvas object layer assignment."""
        with self._capture_history("object_layer"):
            if object_type == "camera":
                self.camera_manager.update_camera_layer(object_id, layer_id, self.current_layout_id)
            elif object_type == "drawing":
                self.camera_manager.update_drawing_shape_layer(object_id, layer_id, self.current_layout_id)

    def update_object_lock(self, object_type: str, object_id: str, locked: bool) -> None:
        """Persist layer-object lock state."""
        with self._capture_history("object_lock"):
            if object_type == "camera":
                self.camera_manager.update_camera_object_locked(object_id, locked, self.current_layout_id)
            elif object_type == "drawing":
                self.camera_manager.update_drawing_shape_object_locked(object_id, locked, self.current_layout_id)

    def update_object_visibility(self, object_type: str, object_id: str, visible: bool) -> None:
        """Persist layer-object visibility state."""
        with self._capture_history("object_visibility"):
            if object_type == "camera":
                self.camera_manager.update_camera_object_visible(object_id, visible, self.current_layout_id)
            elif object_type == "drawing":
                self.camera_manager.update_drawing_shape_object_visible(object_id, visible, self.current_layout_id)

    def update_object_z_index(self, object_type: str, object_id: str, z_index: int) -> None:
        """Persist layer-object z-index."""
        with self._capture_history("object_z"):
            if object_type == "camera":
                self.camera_manager.update_camera_z_index(object_id, z_index, self.current_layout_id)
            elif object_type == "drawing":
                self.camera_manager.update_drawing_shape_z_index(object_id, z_index, self.current_layout_id)

    def add_device_link(self, source_device_id: str, target_device_id: str) -> bool:
        """Persist a canvas-created device link."""
        with self._capture_history("device_link_create"):
            if self.camera_manager.add_device_link(source_device_id, target_device_id, self.current_layout_id):
                self.map_canvas.set_device_links(self.camera_manager.get_device_links(self.current_layout_id))
                self._refresh_camera_panel()
                self._show_status(t("status.device_link_created"), 3000)
                return True
            self._show_status(t("status.device_link_skipped"), 3000)
            return False

    def delete_device_link(self, source_device_id: str, target_device_id: str) -> None:
        """Remove one canvas-requested device link."""
        with self._capture_history("device_link_delete"):
            if self.camera_manager.delete_device_link_between(source_device_id, target_device_id, self.current_layout_id):
                self.map_canvas.set_device_links(self.camera_manager.get_device_links(self.current_layout_id))
                self._refresh_camera_panel()
                self._show_status(t("status.device_link_removed"), 3000)
                return
            self._show_status(t("status.device_link_remove_failed"), 3000)

    def unlink_devices_from_group(self, source_device_ids: object) -> bool:
        """Remove outgoing parent links for one or more devices."""
        device_ids = [
            str(device_id)
            for device_id in (source_device_ids if isinstance(source_device_ids, list) else [source_device_ids])
            if str(device_id)
        ]
        device_ids = list(dict.fromkeys(device_ids))
        if not device_ids:
            self._show_status(t("status.device_link_remove_failed"), 3000)
            return False
        with self._capture_history("device_link_ungroup"):
            current_links = self.camera_manager.get_device_links(self.current_layout_id)
            removed_any = False
            for link in current_links:
                if link.source_device_id in device_ids:
                    removed_any = (
                        self.camera_manager.delete_device_link_between(
                            link.source_device_id,
                            link.target_device_id,
                            self.current_layout_id,
                        )
                        or removed_any
                    )
            if not removed_any:
                self._show_status(t("status.device_link_remove_failed"), 3000)
                return False
            self.map_canvas.set_device_links(self.camera_manager.get_device_links(self.current_layout_id))
            self._refresh_camera_panel()
            self._show_status(t("status.device_link_removed"), 3000)
            return True

    def update_object_name(self, object_type: str, object_id: str, display_name: str) -> None:
        """Persist a layer object display name change."""
        display_name = display_name.strip()
        if not display_name:
            return
        with self._capture_history("object_rename"):
            if object_type == "camera":
                camera = self.camera_manager.get_camera_in_layout(object_id, self.current_layout_id)
                if camera is None:
                    return
                camera.name = display_name
                if self.camera_manager.update_camera_details(camera):
                    self.map_canvas.refresh_camera_item(camera)
                    self._refresh_camera_panel()
                    self._refresh_dashboard()
            elif object_type == "drawing":
                self.camera_manager.update_drawing_shape_display_name(object_id, display_name, self.current_layout_id)

    def _target_layer_for_camera(self) -> str:
        return self.map_canvas.active_layer_id or self.camera_manager.first_layer_id(self.current_layout_id)

    def _capture_history(self, label: str) -> Any:
        if self.history_manager is None:
            return nullcontext()
        return self.history_manager.capture(label)
