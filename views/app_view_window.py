"""Main application window for composing the Camera Map Manager views."""

import os

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QColorDialog, QFileDialog, QInputDialog, QMainWindow, QMessageBox, QStatusBar, QToolBar, QVBoxLayout, QWidget

from config.i18n import LANGUAGE_LABELS, SUPPORTED_LANGUAGES, get_language, set_language, t
from controllers.camera_data_manager import CameraDataManager
from controllers.camera_placement_controller import CameraPlacementController
from services.network_ping_service import PingService
from utils.image_assets import import_png_asset
from views.app_camera_actions import AppCameraActions
from views.app_docks import AppDocks
from views.app_layout_actions import AppLayoutActions
from views.app_settings_actions import AppSettingsActions
from views.layer_state import ALL_LAYERS
from views.map_drawing_tools import DrawingMode
from views.map_view_canvas import MapCanvas
from views.status_dashboard import StatusDashboard


class MainWindow(AppLayoutActions, AppSettingsActions, AppCameraActions, AppDocks, QMainWindow):
    """Top-level window that wires the map canvas, sidebar, menus, and controller."""

    def __init__(self) -> None:
        super().__init__()
        self.resize(1100, 800)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.map_canvas = MapCanvas(self)
        self.current_layout_id = "default"
        self.current_background_path = ""
        self.settings = {
            "ping_interval": 30,
            "ping_timeout": 1.0,
            "ping_retries": 1,
            "canvas_width": 4000,
            "canvas_height": 3000,
            "grid_size": 20,
            "background_scale": 1.0,
            "light_theme": False,
        }
        self.main_layout.addWidget(self.map_canvas)
        self.status_dashboard = StatusDashboard(self)
        self.main_layout.addWidget(self.status_dashboard)

        self.init_camera_dock()
        self.init_menus_and_toolbars()

        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.init_layouts_dock()
        self.init_layers_dock()
        self.add_widget_reopen_actions()
        self.retranslate()
        self.status_bar.showMessage(t("app.ready"), 5000)

        self.camera_manager = CameraDataManager()
        self.ping_service = PingService(
            self.camera_manager.get_all_cameras_for_ping(),
            interval_seconds=30,
        )
        self.camera_controller = CameraPlacementController(
            self.camera_panel,
            self.map_canvas,
            self.camera_manager,
            self.status_bar.showMessage,
            self.refresh_ping_cameras,
            self.refresh_status_dashboard,
        )
        self.camera_controller.load_cameras()
        self.layouts_panel.layout_selected.connect(self.switch_layout)
        self.layouts_panel.layout_add_requested.connect(self.add_layout)
        self.layouts_panel.layout_rename_requested.connect(self.rename_layout)
        self.layouts_panel.layout_delete_requested.connect(self.delete_layout)
        self.refresh_layouts_panel()
        self.camera_panel.camera_add_requested.connect(self.add_camera)
        self.camera_panel.camera_import_requested.connect(self.import_cameras_csv)
        self.camera_panel.camera_export_requested.connect(self.export_cameras_csv)
        self.ping_service.status_updated.connect(self.camera_controller.handle_camera_status_updated)
        self.refresh_ping_cameras()
        self.ping_service.start()

    def init_menus_and_toolbars(self) -> None:
        self.open_action = QAction(self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.select_background_image)

        self.unload_map_action = QAction(self)
        self.unload_map_action.triggered.connect(self.unload_background_image)

        self.exit_action = QAction(self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)

        self.settings_action = QAction(self)
        self.settings_action.triggered.connect(self.open_settings)

        self.zoom_in_action = QAction(self)
        self.zoom_in_action.setShortcut("Ctrl++")
        self.zoom_in_action.triggered.connect(lambda: self.map_canvas.scale(1.25, 1.25))

        self.zoom_out_action = QAction(self)
        self.zoom_out_action.setShortcut("Ctrl+-")
        self.zoom_out_action.triggered.connect(lambda: self.map_canvas.scale(0.8, 0.8))

        self.zoom_fit_action = QAction(self)
        self.zoom_fit_action.setShortcut("Ctrl+0")
        self.zoom_fit_action.triggered.connect(self.map_canvas.fit_in_view)

        self.select_action = QAction(self)
        self.select_action.setCheckable(True)
        self.select_action.setChecked(True)
        self.select_action.triggered.connect(lambda: self.set_canvas_mode(DrawingMode.SELECT))

        self.draw_line_action = QAction(self)
        self.draw_line_action.setCheckable(True)
        self.draw_line_action.triggered.connect(lambda: self.set_canvas_mode(DrawingMode.LINE))

        self.draw_rectangle_action = QAction(self)
        self.draw_rectangle_action.setCheckable(True)
        self.draw_rectangle_action.triggered.connect(lambda: self.set_canvas_mode(DrawingMode.RECTANGLE))

        self.draw_zone_action = QAction(self)
        self.draw_zone_action.setCheckable(True)
        self.draw_zone_action.triggered.connect(lambda: self.set_canvas_mode(DrawingMode.ZONE))

        self.draw_freehand_action = QAction(self)
        self.draw_freehand_action.setCheckable(True)
        self.draw_freehand_action.triggered.connect(lambda: self.set_canvas_mode(DrawingMode.FREEHAND))

        self.add_text_action = QAction(self)
        self.add_text_action.triggered.connect(self.add_text_annotation)

        self.insert_png_action = QAction(self)
        self.insert_png_action.triggered.connect(self.insert_png_annotation)

        self.choose_color_action = QAction(self)
        self.choose_color_action.triggered.connect(self.choose_drawing_color)

        self.delete_selected_action = QAction(self)
        self.delete_selected_action.setShortcut("Delete")
        self.delete_selected_action.triggered.connect(self.delete_selected_drawings)

        self.rotate_camera_action = QAction(self)
        self.rotate_camera_action.setShortcut("R")
        self.rotate_camera_action.triggered.connect(self.rotate_selected_cameras)

        self.grid_action = QAction(self)
        self.grid_action.setCheckable(True)
        self.grid_action.setChecked(True)
        self.grid_action.triggered.connect(self.map_canvas.set_grid_visible)

        self.info_actions: dict[str, QAction] = {}
        for field in ("name", "zone", "ip", "dvr"):
            action = QAction(self)
            action.setCheckable(True)
            action.setChecked(field == "name")
            action.triggered.connect(lambda checked=False, item=field: self.map_canvas.set_camera_info_visibility(item, checked))
            self.info_actions[field] = action

        self.language_actions: dict[str, QAction] = {}
        for language in SUPPORTED_LANGUAGES:
            action = QAction(LANGUAGE_LABELS[language], self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, lang=language: self.set_language(lang))
            self.language_actions[language] = action

        self.file_menu = self.menuBar().addMenu("")
        self.file_menu.addAction(self.open_action)
        self.file_menu.addAction(self.unload_map_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)

        self.view_menu = self.menuBar().addMenu("")
        self.view_menu.addAction(self.zoom_in_action)
        self.view_menu.addAction(self.zoom_out_action)
        self.view_menu.addAction(self.zoom_fit_action)
        self.view_menu.addAction(self.settings_action)

        self.info_menu = self.menuBar().addMenu("")
        self.info_menu.addAction(self.grid_action)
        self.info_menu.addSeparator()
        for action in self.info_actions.values():
            self.info_menu.addAction(action)

        self.language_menu = self.menuBar().addMenu("")
        for action in self.language_actions.values():
            self.language_menu.addAction(action)

        self.toolbar = QToolBar(self)
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        self.toolbar.addAction(self.open_action)
        self.toolbar.addAction(self.unload_map_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.zoom_in_action)
        self.toolbar.addAction(self.zoom_out_action)
        self.toolbar.addAction(self.zoom_fit_action)
        self.init_drawing_tools_dock()

    def set_canvas_mode(self, mode: DrawingMode) -> None:
        mode_actions = {
            DrawingMode.SELECT: self.select_action,
            DrawingMode.LINE: self.draw_line_action,
            DrawingMode.RECTANGLE: self.draw_rectangle_action,
            DrawingMode.ZONE: self.draw_zone_action,
            DrawingMode.FREEHAND: self.draw_freehand_action,
        }
        for action_mode, action in mode_actions.items():
            action.setChecked(action_mode == mode)

        self.map_canvas.set_drawing_mode(mode)

    def add_text_annotation(self) -> None:
        """Prompt and add a text annotation."""
        text, accepted = QInputDialog.getText(self, t("dialog.add_text.title"), t("dialog.add_text.label"))
        if accepted and text.strip():
            self.map_canvas.add_text_annotation(text.strip())

    def insert_png_annotation(self) -> None:
        """Import and add a compressed PNG annotation."""
        file_path, _ = QFileDialog.getOpenFileName(self, t("dialog.choose_png.title"), "", t("dialog.choose_png.filter"))
        if not file_path:
            return
        imported = import_png_asset(file_path)
        if imported is None:
            QMessageBox.critical(self, t("error.load_file.title"), t("error.load_file.body"))
            return
        image_path, width, height = imported
        self.map_canvas.add_image_annotation(image_path, width, height)
        self.status_bar.showMessage(t("status.png_inserted"), 5000)

    def choose_drawing_color(self) -> None:
        """Open a color picker for map drawings."""
        color = QColorDialog.getColor(parent=self, title=t("dialog.choose_color.title"))
        if color.isValid():
            self.map_canvas.set_drawing_color(color.name())

    def delete_selected_drawings(self) -> None:
        """Delete selected drawable items."""
        count = self.map_canvas.delete_selected_drawings()
        if count:
            self.status_bar.showMessage(t("status.drawing_deleted", count=count), 5000)

    def rotate_selected_cameras(self) -> None:
        count = self.map_canvas.rotate_selected_cameras(15)
        if count:
            self.status_bar.showMessage(t("status.camera_rotated", count=count), 5000)

    def select_background_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("dialog.choose_map.title"),
            "",
            t("dialog.choose_map.filter"),
        )
        if not file_path:
            return

        success = self.map_canvas.load_background_image(file_path)
        if success:
            self.current_background_path = file_path
            self.save_current_layout_state()
            self.status_bar.showMessage(t("status.map_loaded", filename=os.path.basename(file_path)), 5000)
            return

        QMessageBox.critical(
            self,
            t("error.load_file.title"),
            t("error.load_file.body"),
        )

    def unload_background_image(self) -> None:
        self.map_canvas.unload_background_image()
        self.current_background_path = ""
        self.save_current_layout_state()
        self.status_bar.showMessage(t("status.map_unloaded"), 5000)

    def closeEvent(self, event: object) -> None:
        self.ping_service.stop()
        super().closeEvent(event)

    def refresh_ping_cameras(self) -> None:
        self.ping_service.set_cameras(self.camera_manager.get_all_cameras_for_ping(self.current_layout_id))

    def refresh_status_dashboard(self) -> None:
        cameras = self.camera_manager.get_all_cameras(self.current_layout_id)
        online = sum(1 for camera in cameras if camera.status)
        total = len(cameras)
        self.status_dashboard.update_counts(total, online, total - online)

    def set_language(self, language: str) -> None:
        set_language(language); self.retranslate()

    def retranslate(self) -> None:
        self.setWindowTitle(t("app.title"))
        if hasattr(self, "dock"):
            self.dock.setWindowTitle(t("dock.control_panel"))
        if hasattr(self, "tools_dock"):
            self.tools_dock.setWindowTitle(t("dock.drawing_tools"))
        if hasattr(self, "layers_dock"):
            self.layers_dock.setWindowTitle(t("dock.layers"))
        if hasattr(self, "open_action"):
            self.open_action.setText(t("action.open_map"))
            self.unload_map_action.setText(t("action.unload_map"))
            self.exit_action.setText(t("action.exit"))
            self.zoom_in_action.setText(t("action.zoom_in"))
            self.zoom_out_action.setText(t("action.zoom_out"))
            self.zoom_fit_action.setText(t("action.zoom_fit"))
            self.settings_action.setText(t("action.settings"))
            self.select_action.setText(t("action.select"))
            self.draw_line_action.setText(t("action.draw_line"))
            self.draw_rectangle_action.setText(t("action.draw_rectangle"))
            self.draw_zone_action.setText(t("action.draw_zone"))
            self.draw_freehand_action.setText(t("action.draw_freehand"))
            self.add_text_action.setText(t("action.add_text"))
            self.insert_png_action.setText(t("action.insert_png"))
            self.choose_color_action.setText(t("action.choose_color"))
            self.delete_selected_action.setText(t("action.delete_selected"))
            self.rotate_camera_action.setText(t("action.rotate_camera"))
            self.grid_action.setText(t("action.toggle_grid"))
            self.info_actions["name"].setText(t("action.show_name"))
            self.info_actions["zone"].setText(t("action.show_zone"))
            self.info_actions["ip"].setText(t("action.show_ip"))
            self.info_actions["dvr"].setText(t("action.show_dvr"))
            self.file_menu.setTitle(t("menu.file"))
            self.view_menu.setTitle(t("menu.view"))
            self.info_menu.setTitle(t("menu.view"))
            self.language_menu.setTitle(t("menu.language"))
            self.layouts_dock.setWindowTitle(t("dock.layouts"))
            self.toolbar.setWindowTitle(t("toolbar.main"))
            self.map_canvas.set_default_layer_names({layer_id: t(f"layer.{layer_id}") for layer_id in ALL_LAYERS})
            if hasattr(self, "layers_panel"):
                self.layers_panel.refresh()
            for language, action in self.language_actions.items():
                action.setChecked(language == get_language())
        if hasattr(self, "camera_panel"):
            self.camera_panel.retranslate()
        if hasattr(self, "layouts_panel"):
            self.layouts_panel.retranslate()
        if hasattr(self, "map_canvas"):
            self.map_canvas.retranslate_camera_items()
        if hasattr(self, "status_dashboard"):
            self.status_dashboard.retranslate()
        if hasattr(self, "status_bar"):
            self.status_bar.showMessage(t("app.ready"), 5000)
