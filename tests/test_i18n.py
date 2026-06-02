"""Tests for application translations."""

import string

from config.i18n import SUPPORTED_LANGUAGES, TRANSLATIONS, get_language, set_language, t
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QApplication, QCheckBox, QLabel, QMenu, QPushButton, QTabWidget, QToolButton

from controllers.camera_data_manager import CameraDataManager
from services.app_settings_service import DEFAULT_SETTINGS, load_app_settings, save_app_settings
from views import confirm_dialog
from views.app_view_window import MainWindow
from views.confirm_dialog import ConfirmDialog
from models.drawing_shape_model import DrawingShape
from models.map_layout_model import MapLayout
from views.layout_properties_dialog import LayoutPropertiesDialog
from views.settings_dialog import SettingsDialog
from views.ui_theme import DANGER, LIGHT_ACTIVE_ROW, LIGHT_TEXT, app_stylesheet


def test_all_translation_keys_support_all_languages() -> None:
    for key, translations in TRANSLATIONS.items():
        assert set(SUPPORTED_LANGUAGES).issubset(translations), key


def test_translation_placeholders_are_consistent() -> None:
    formatter = string.Formatter()
    for key, translations in TRANSLATIONS.items():
        expected = {
            field_name
            for _, field_name, _, _ in formatter.parse(translations["vi"])
            if field_name
        }
        for language in SUPPORTED_LANGUAGES:
            fields = {
                field_name
                for _, field_name, _, _ in formatter.parse(translations[language])
                if field_name
            }
            assert fields == expected, f"{key}:{language}"


def test_runtime_language_switch_uses_placeholders() -> None:
    original_language = get_language()
    try:
        set_language("en")
        assert t("status.camera_placed", name="Lobby", x=10, y=20) == "Placed device 'Lobby' at (10, 20)"

        set_language("jp")
        assert "Lobby" in t("status.camera_updated", name="Lobby")
    finally:
        set_language(original_language)


def test_main_window_language_switch_retranslates_visible_text(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    original_language = get_language()
    try:
        monkeypatch.setattr("views.app_view_window.load_app_settings", lambda: DEFAULT_SETTINGS.copy())
        monkeypatch.setattr(confirm_dialog, "confirm", lambda *args, **kwargs: True)
        window = MainWindow()
        window.show()
        app.processEvents()
        window.set_language("en")

        assert window.file_menu.title() == "File"
        assert window.action_menu.title() == "Action"
        assert window.open_action.text() == "Load background map..."
        assert window.undo_action.text() == "Undo"
        assert window.redo_action.text() == "Redo"
        assert window.undo_action.shortcuts() == QKeySequence.keyBindings(QKeySequence.StandardKey.Undo)
        assert window.redo_action.shortcuts() == QKeySequence.keyBindings(QKeySequence.StandardKey.Redo)
        assert window.undo_action in window.action_menu.actions()
        assert window.redo_action in window.action_menu.actions()
        assert window.settings_action.text() == "Settings"
        assert window.dock.toggleViewAction() in window.view_menu.actions()
        assert window.camera_panel is window.layouts_panel
        assert window.dock.windowTitle() == "Control Panel"
        assert not hasattr(window, "control_dock_title")
        assert window.camera_panel.close_button.property("icon_name") == "close"
        assert window.camera_panel.close_button.toolTip() == "Close"
        assert window.dock.features() == window.dock.DockWidgetFeature.DockWidgetClosable
        assert not window.dock.features() & window.dock.DockWidgetFeature.DockWidgetFloatable
        assert not window.dock.features() & window.dock.DockWidgetFeature.DockWidgetMovable
        assert window.camera_panel.tree_widget.indentation() == 10
        assert window.camera_panel.unplaced_button.text() == "Unplaced"
        assert window.camera_panel.placed_button.text() == "Placed"
        assert window.camera_panel.placed_button.isChecked()
        assert not window.camera_panel.unplaced_button.isChecked()
        assert window.camera_panel.placed_button.x() < window.camera_panel.unplaced_button.x()
        assert window.camera_panel.rename_layout_button.property("icon_name") == "cog"
        assert window.camera_panel.edit_button.property("icon_name") == "cog"
        window.camera_panel.close_button.click()
        app.processEvents()
        assert not window.dock.isVisible()
        assert window.drawing_tools_panel.x() == 14
        window.dock.toggleViewAction().trigger()
        app.processEvents()
        assert window.dock.isVisible()
        assert window.drawing_tools_panel.x() >= window.map_canvas.mapTo(window, window.map_canvas.rect().topLeft()).x()
        assert window.layers_dock.windowTitle() == "Layers"
        assert not hasattr(window, "layers_dock_title")
        assert window.layers_panel.close_button.property("icon_name") == "close"
        assert window.layers_panel.close_button.toolTip() == "Close"
        assert window.drawing_tools_panel.isVisible()
        assert not window.drawing_tools_panel.isWindow()
        assert window.drawing_tools_panel.collapse_button.toolTip() == "Drawing Tools"
        assert not hasattr(window, "floating_tools_toolbar")
        assert not hasattr(window, "toolbar")
        assert window.settings_action in window.menuBar().actions()
        assert window.import_package_action in window.file_menu.actions()
        assert window.export_package_action in window.file_menu.actions()
        assert not hasattr(window, "draw_menu")
        assert not hasattr(window, "annotate_menu")
        assert not hasattr(window, "init_two_level_toolbar")
        assert not hasattr(window, "context_toolbar")
        assert not hasattr(window, "toolbar_group_selectors")
        window.drawing_tools_panel.set_collapsed(True)
        assert not window.drawing_tools_panel.content.isVisible()
        window._show_drawing_tools_panel()
        window.drawing_tools_panel.set_collapsed(False)
        assert window.drawing_tools_panel.content.isVisible()
        window.layers_dock.show()
        assert window.layers_dock.isVisible()
        window.layers_panel.close_button.click()
        app.processEvents()
        assert not window.layers_dock.isVisible()
        window.layers_dock.toggleViewAction().trigger()
        app.processEvents()
        assert not window.layers_dock.isFloating()
        assert window.layers_dock.features() == window.layers_dock.DockWidgetFeature.DockWidgetClosable
        assert not window.layers_dock.features() & window.layers_dock.DockWidgetFeature.DockWidgetFloatable
        assert not window.layers_dock.features() & window.layers_dock.DockWidgetFeature.DockWidgetMovable
        assert window.layers_panel.tree.topLevelItemCount() >= 1
        assert window.layers_panel.tree.columnCount() == 3
        assert not window.layers_panel.tree.rootIsDecorated()
        assert window.layers_panel.tree.headerItem().text(1) == "Name"
        assert window.layers_panel.tree.headerItem().text(2) == "#"
        window.layers_panel.apply_theme(True)
        first_layer = window.layers_panel.tree.selectedItems()[0]
        assert first_layer.background(1).color().name() == LIGHT_ACTIVE_ROW
        layer_controls = window.layers_panel.tree.itemWidget(first_layer, 0)
        assert isinstance(layer_controls.findChild(QCheckBox), QCheckBox)
        assert isinstance(layer_controls.findChild(QToolButton), QToolButton)
        assert window.layers_panel.tree.itemWidget(first_layer, 1) is None
        before_count = int(first_layer.text(2))
        first_layer.setExpanded(False)
        window.map_canvas.add_drawing_shape(DrawingShape("shape_realtime", "Line", [0.0, 0.0, 20.0, 20.0]), emit_created=True)
        app.processEvents()
        refreshed_layer = window.layers_panel.tree.selectedItems()[0]
        assert int(refreshed_layer.text(2)) == before_count + 1
        assert not refreshed_layer.isExpanded()
        refreshed_layer.setExpanded(True)
        child = refreshed_layer.child(0)
        assert child is not None
        assert child.flags() & Qt.ItemFlag.ItemIsEditable
        child.setText(1, "Renamed Line")
        app.processEvents()
        assert any(state.label == "Renamed Line" for state in window.map_canvas.get_layer_object_states(window.map_canvas.active_layer_id))
        assert window.layers_panel.add_button.text() == ""
        assert window.layers_panel.add_button.toolTip() == "Add layer"
        assert not hasattr(window.layers_panel, "select_button")
        assert not hasattr(window.layers_panel, "move_button")
        assert not hasattr(window, "toolbar")
        assert window.draw_line_action in [action for menu in window.drawing_tools_panel.findChildren(QMenu) for action in menu.actions()]
        assert window.pan_action.isChecked()
        assert not window.select_action.isChecked()
        assert window.status_dashboard.total_label.text().startswith("Total:")
        assert len(window.status_dashboard.findChildren(QLabel)) == 1
        assert not window.status_dashboard.summary_label.wordWrap()

        window.set_language("jp")
        assert window.layers_dock.windowTitle() == "レイヤー"
        assert window.layouts_panel.layout_title.text() == "レイアウト"
        assert window.language_menu.title() == "言語"
        assert window.action_menu.title() == "アクション"
        assert window.draw_rectangle_action.text() == "四角形を描く"

        window.close()
        app.processEvents()
        window.camera_manager.db.close()
    finally:
        set_language(original_language)


def test_main_window_starts_blank_when_no_layout_exists(monkeypatch, tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    manager = CameraDataManager(tmp_path / "blank.db")
    monkeypatch.setattr("views.app_view_window.load_app_settings", lambda: DEFAULT_SETTINGS.copy())
    monkeypatch.setattr("views.app_view_window.CameraDataManager", lambda: manager)
    monkeypatch.setattr(confirm_dialog, "confirm", lambda *args, **kwargs: True)

    window = MainWindow()

    assert window.current_layout_id == ""
    assert window.camera_manager.get_layouts() == []
    assert window.open_action.isEnabled() is False
    assert window.export_package_action.isEnabled() is False
    assert window.camera_panel.add_button.isEnabled() is False
    assert window.import_package_action.isEnabled() is True
    assert window.map_canvas.scene.sceneRect().isNull()

    window.ping_service.stop()
    window.close()
    app.processEvents()
    manager.db.close()


def test_settings_theme_dropdown_applies_immediately() -> None:
    app = QApplication.instance() or QApplication([])
    changed = []
    dialog = SettingsDialog(
        {
            "ping_interval": 30,
            "ping_timeout": 1.0,
            "ping_retries": 1,
            "canvas_width": 4000,
            "canvas_height": 3000,
            "grid_size": 20,
            "background_scale": 1.0,
            "light_theme": False,
        },
        theme_changed=changed.append,
    )

    dialog.theme_input.setCurrentIndex(1)

    assert changed == [True]
    assert dialog.values()["light_theme"] is True
    assert dialog.tabs.tabPosition() == QTabWidget.TabPosition.North
    assert dialog.tabs.count() == 2
    assert dialog.tabs.tabText(0) == t("settings.network")
    assert dialog.tabs.tabText(1) == t("settings.appearance")
    assert not hasattr(dialog, "canvas_width_input")
    assert "QTabBar::tab" in app_stylesheet(True)
    assert "QMenu::item" in app_stylesheet(True)
    assert "padding: 6px 76px 6px 16px;" in app_stylesheet(True)
    assert LIGHT_TEXT in app_stylesheet(True)
    app.processEvents()


def test_layout_properties_dialog_returns_layout_canvas_values() -> None:
    app = QApplication.instance() or QApplication([])
    layout = MapLayout("layout_a", "Original", canvas_width=1200, canvas_height=900, grid_size=25, background_scale=1.2)
    dialog = LayoutPropertiesDialog(layout)

    dialog.name_input.setText("Edited")
    dialog.canvas_width_input.setValue(2000)
    dialog.canvas_height_input.setValue(1500)
    dialog.grid_size_input.setValue(40)
    dialog.background_scale_input.setValue(1.5)
    edited = dialog.get_layout()

    assert edited.name == "Edited"
    assert edited.canvas_width == 2000
    assert edited.canvas_height == 1500
    assert edited.grid_size == 40
    assert edited.background_scale == 1.5
    app.processEvents()


def test_delete_layout_requires_confirmation(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("views.app_view_window.load_app_settings", lambda: DEFAULT_SETTINGS.copy())
    window = MainWindow()
    layout = window.camera_manager.create_layout("Delete Me")
    calls = []
    monkeypatch.setattr(confirm_dialog, "confirm", lambda *args, **kwargs: calls.append(args) or False)

    window.delete_layout(layout.id)

    assert calls
    assert window.camera_manager.get_layout(layout.id) is not None

    monkeypatch.setattr(confirm_dialog, "confirm", lambda *args, **kwargs: True)
    window.delete_layout(layout.id)

    assert window.camera_manager.get_layout(layout.id) is None
    window.close()
    app.processEvents()
    window.camera_manager.db.close()
    app.processEvents()


def test_confirm_dialog_has_red_no_button_and_fixed_order() -> None:
    app = QApplication.instance() or QApplication([])
    dialog = ConfirmDialog("Title", "Message")

    assert dialog.yes_button.text() == t("button.yes")
    assert dialog.no_button.text() == t("button.no")
    assert DANGER in dialog.no_button.styleSheet()
    assert dialog.no_button.styleSheet().count("#ffffff") >= 1
    assert dialog.yes_button.isDefault()
    button_row = dialog.layout().itemAt(1).layout()
    assert isinstance(button_row.itemAt(1).widget(), QPushButton)
    assert button_row.itemAt(1).widget() is dialog.yes_button
    assert button_row.itemAt(2).widget() is dialog.no_button
    app.processEvents()


def test_app_settings_persist_json(tmp_path) -> None:
    settings_path = tmp_path / "app_settings.json"
    settings = DEFAULT_SETTINGS.copy()
    settings["light_theme"] = True
    settings["ping_interval"] = 45
    settings["ping_timeout"] = 2.5

    save_app_settings(settings, settings_path)
    loaded = load_app_settings(settings_path)

    assert loaded["light_theme"] is True
    assert loaded["ping_interval"] == 45
    assert loaded["ping_timeout"] == 2.5


def test_unload_background_map_requires_confirmation(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("views.app_view_window.load_app_settings", lambda: DEFAULT_SETTINGS.copy())
    window = MainWindow()
    calls = 0

    def unload_stub() -> None:
        nonlocal calls
        calls += 1

    window.current_background_path = "map.png"
    window.map_canvas.unload_background_image = unload_stub
    monkeypatch.setattr(confirm_dialog, "confirm", lambda *args, **kwargs: False)

    window.unload_background_image()

    assert calls == 0
    assert window.current_background_path == "map.png"

    monkeypatch.setattr(confirm_dialog, "confirm", lambda *args, **kwargs: True)
    window.unload_background_image()

    assert calls == 1
    assert window.current_background_path == ""
    window.close()
    app.processEvents()
    window.camera_manager.db.close()
