"""Tests for application translations."""

import string

from config.i18n import SUPPORTED_LANGUAGES, TRANSLATIONS, get_language, set_language, t
from PyQt6.QtWidgets import QApplication

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


def test_main_window_language_switch_retranslates_visible_text() -> None:
    app = QApplication.instance() or QApplication([])
    original_language = get_language()
    try:
        window = MainWindow()
        window.set_language("en")

        assert window.file_menu.title() == "File"
        assert window.open_action.text() == "Load background map..."
        assert window.settings_action.text() == "Settings"
        assert window.dock.toggleViewAction() in window.view_menu.actions()
        assert window.layouts_dock.windowTitle() == "Layouts"
        assert window.tools_dock.windowTitle() == "Drawing Tools"
        assert window.layers_dock.windowTitle() == "Layers"
        assert window.draw_line_action not in window.toolbar.actions()
        assert window.status_dashboard.total_label.text().startswith("Total:")

        window.set_language("jp")
        assert window.layers_dock.windowTitle() == "レイヤー"
        assert window.layouts_dock.windowTitle() == "レイアウト"
        assert window.language_menu.title() == "言語"
        assert window.draw_rectangle_action.text() == "四角形を描く"

        window.close()
    finally:
        set_language(original_language)
    app.processEvents()
