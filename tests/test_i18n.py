"""Tests for application translations."""

import string

from config.i18n import SUPPORTED_LANGUAGES, TRANSLATIONS, get_language, set_language, t
from PyQt6.QtWidgets import QApplication, QCheckBox, QLabel, QMenu, QMessageBox

from views.app_view_window import MainWindow


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
        assert t("status.camera_placed", name="Lobby", x=10, y=20) == "Placed camera 'Lobby' at (10, 20)"

        set_language("jp")
        assert "Lobby" in t("status.camera_updated", name="Lobby")
    finally:
        set_language(original_language)


def test_main_window_language_switch_retranslates_visible_text(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    original_language = get_language()
    try:
        monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
        window = MainWindow()
        window.show()
        app.processEvents()
        window.set_language("en")

        assert window.file_menu.title() == "File"
        assert window.open_action.text() == "Load background map..."
        assert window.settings_action.text() == "Settings"
        assert window.dock.toggleViewAction() in window.view_menu.actions()
        assert window.camera_panel is window.layouts_panel
        assert window.dock.windowTitle() == "Control Panel"
        assert window.dock.features() == window.dock.DockWidgetFeature.DockWidgetClosable
        assert not window.dock.features() & window.dock.DockWidgetFeature.DockWidgetFloatable
        assert not window.dock.features() & window.dock.DockWidgetFeature.DockWidgetMovable
        assert window.camera_panel.tree_widget.indentation() == 10
        window.dock.hide()
        app.processEvents()
        assert not window.dock.isVisible()
        assert window.drawing_tools_panel.x() == 14
        window.dock.toggleViewAction().trigger()
        app.processEvents()
        assert window.dock.isVisible()
        assert window.layers_dock.windowTitle() == "Layers"
        assert window.drawing_tools_panel.isVisible()
        assert not window.drawing_tools_panel.isWindow()
        assert window.drawing_tools_panel.collapse_button.toolTip() == "Drawing Tools"
        assert not hasattr(window, "floating_tools_toolbar")
        assert window.drawing_tools_panel.x() >= window.map_canvas.mapTo(window, window.map_canvas.rect().topLeft()).x()
        assert window.settings_action in window.toolbar.actions()
        assert window.open_action in window.toolbar.actions()
        assert window.zoom_fit_action in window.toolbar.actions()
        assert window.settings_action not in window.annotate_menu.actions()
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
        assert not window.layers_dock.isFloating()
        assert window.layers_dock.features() == window.layers_dock.DockWidgetFeature.DockWidgetClosable
        assert not window.layers_dock.features() & window.layers_dock.DockWidgetFeature.DockWidgetFloatable
        assert not window.layers_dock.features() & window.layers_dock.DockWidgetFeature.DockWidgetMovable
        assert window.layers_panel.tree.topLevelItemCount() >= 4
        assert window.layers_panel.tree.columnCount() == 3
        assert not window.layers_panel.tree.rootIsDecorated()
        assert window.layers_panel.tree.headerItem().text(1) == "Name"
        assert window.layers_panel.tree.headerItem().text(2) == "#"
        first_layer = window.layers_panel.tree.topLevelItem(0)
        assert isinstance(window.layers_panel.tree.itemWidget(first_layer, 0), QCheckBox)
        assert window.layers_panel.tree.itemWidget(first_layer, 1) is None
        assert window.layers_panel.add_button.text() == ""
        assert window.layers_panel.add_button.toolTip() == "Add layer"
        assert window.layers_panel.move_button.toolTip() == "Move selected"
        assert window.draw_line_action not in window.toolbar.actions()
        assert window.draw_line_action in [action for menu in window.drawing_tools_panel.findChildren(QMenu) for action in menu.actions()]
        assert window.status_dashboard.total_label.text().startswith("Total:")
        assert len(window.status_dashboard.findChildren(QLabel)) == 1
        assert not window.status_dashboard.summary_label.wordWrap()

        window.set_language("jp")
        assert window.layers_dock.windowTitle() == "レイヤー"
        assert window.layouts_panel.layout_title.text() == "レイアウト"
        assert window.language_menu.title() == "言語"
        assert window.draw_rectangle_action.text() == "四角形を描く"

        window.close()
    finally:
        set_language(original_language)
    app.processEvents()


def test_unload_background_map_requires_confirmation(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    calls = 0

    def unload_stub() -> None:
        nonlocal calls
        calls += 1

    window.current_background_path = "map.png"
    window.map_canvas.unload_background_image = unload_stub
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.No)

    window.unload_background_image()

    assert calls == 0
    assert window.current_background_path == "map.png"

    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    window.unload_background_image()

    assert calls == 1
    assert window.current_background_path == ""
    window.close()
    app.processEvents()
