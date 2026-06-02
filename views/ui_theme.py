"""Reusable color tokens and Qt stylesheets for application UI surfaces."""

BLACK = "#000000"
DARK_PANEL = "#050505"
DARK_SURFACE = "#0b0b0b"
DARK_SURFACE_ALT = "#111111"
DARK_BORDER = "#2f2f2f"
DARK_HOVER = "#1a1a1a"
DARK_ACTIVE_ROW = "#242424"
LIGHT_BG = "#f8fafc"
LIGHT_TEXT = "#111827"
LIGHT_BORDER = "#cbd5e1"
TEXT_ON_DARK = "#f8fafc"
TEXT_MUTED = "#a3a3a3"
TEXT_WHITE = "#ffffff"
PRIMARY = "#7c3aed"
PRIMARY_SOFT = "#8b5cf6"
PRIMARY_FOCUS = "#c4b5fd"
SUCCESS = "#10b981"
DANGER = "#ef4444"
WARNING = "#facc15"
GRID_DARK = "#525252"
GRID_LIGHT = "#64748b"


def app_stylesheet(light_theme: bool) -> str:
    """Return the global application stylesheet for the selected theme."""
    if light_theme:
        return f"QWidget {{ background: {LIGHT_BG}; color: {LIGHT_TEXT}; }}"
    return f"""
        QMainWindow, QWidget {{
            background: {BLACK};
            color: {TEXT_ON_DARK};
        }}
        QMenuBar, QMenu {{
            background: {DARK_PANEL};
            color: {TEXT_ON_DARK};
            border: 1px solid {DARK_BORDER};
        }}
        QMenu::item:selected {{
            background: {DARK_HOVER};
        }}
        QToolBar, QStatusBar {{
            background: {DARK_PANEL};
            color: {TEXT_ON_DARK};
            border: 1px solid {DARK_BORDER};
        }}
        QDockWidget {{
            titlebar-close-icon: none;
            titlebar-normal-icon: none;
        }}
        QDockWidget::title {{
            background: {DARK_SURFACE};
            color: {TEXT_ON_DARK};
            padding: 5px;
        }}
    """


def control_panel_stylesheet() -> str:
    """Return styles for the combined camera/layout control panel."""
    return f"""
        QWidget#controlLayoutPanel {{
            background: {DARK_PANEL};
            color: {TEXT_ON_DARK};
        }}
        QLabel#sectionTitle {{
            color: {TEXT_ON_DARK};
            font-weight: 700;
            padding: 2px 0;
        }}
        QComboBox, QLineEdit, QTreeWidget {{
            background: {DARK_SURFACE_ALT};
            color: {TEXT_ON_DARK};
            border: 1px solid {DARK_BORDER};
            border-radius: 7px;
            padding: 5px;
        }}
        QTreeWidget::item {{
            min-height: 26px;
            padding: 3px;
        }}
        QTreeWidget::item:hover {{
            background: {DARK_HOVER};
        }}
        QTreeWidget::item:selected {{
            background: {DARK_ACTIVE_ROW};
            color: {TEXT_WHITE};
        }}
        QToolButton {{
            background: {DARK_SURFACE_ALT};
            border: 1px solid {DARK_BORDER};
            border-radius: 7px;
            padding: 3px;
        }}
        QToolButton:hover {{
            background: {DARK_HOVER};
            border-color: {PRIMARY_FOCUS};
        }}
        QToolButton:checked {{
            background: {PRIMARY};
            border-color: {PRIMARY_FOCUS};
        }}
    """


def drawing_tools_stylesheet() -> str:
    """Return styles for the fixed floating drawing tools panel."""
    return f"""
        QWidget#drawingToolsPanel {{
            background: rgba(0, 0, 0, 238);
            border: 1px solid {DARK_BORDER};
            border-radius: 10px;
        }}
        QToolButton {{
            background: {DARK_SURFACE_ALT};
            border: 1px solid {DARK_BORDER};
            border-radius: 7px;
            padding: 4px;
        }}
        QToolButton:hover {{
            background: {DARK_HOVER};
            border-color: {PRIMARY_FOCUS};
        }}
        QToolButton:checked {{
            background: {PRIMARY};
            border-color: {PRIMARY_FOCUS};
        }}
        QMenu {{
            background: {DARK_PANEL};
            color: {TEXT_ON_DARK};
            border: 1px solid {DARK_BORDER};
            padding: 4px;
        }}
        QMenu::item {{
            padding: 6px 18px;
        }}
        QMenu::item:selected {{
            background: {DARK_HOVER};
        }}
    """


def layers_panel_stylesheet() -> str:
    """Return styles for the layers panel tree, checkboxes, and action row."""
    return f"""
        QWidget#layersPanel {{
            background: {DARK_PANEL};
            color: {TEXT_ON_DARK};
        }}
        QLabel#sectionTitle {{
            color: {TEXT_ON_DARK};
            font-weight: 700;
            padding: 2px 0;
        }}
        QTreeWidget#layersTree {{
            background: {DARK_SURFACE_ALT};
            color: {TEXT_ON_DARK};
            border: 1px solid {DARK_BORDER};
            border-radius: 8px;
            alternate-background-color: {DARK_SURFACE};
            selection-background-color: {DARK_ACTIVE_ROW};
            selection-color: {TEXT_WHITE};
        }}
        QHeaderView::section {{
            background: {DARK_ACTIVE_ROW};
            color: {TEXT_ON_DARK};
            border: 0;
            border-right: 1px solid {DARK_BORDER};
            padding: 5px;
        }}
        QTreeWidget::item {{
            min-height: 28px;
            padding: 3px;
        }}
        QTreeWidget::item:hover {{
            background: {DARK_HOVER};
        }}
        QCheckBox {{
            background: transparent;
            padding: 2px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 5px;
            border: 2px solid {TEXT_ON_DARK};
            background: {BLACK};
        }}
        QCheckBox::indicator:checked {{
            background: {PRIMARY_SOFT};
            border-color: {PRIMARY_FOCUS};
        }}
        QCheckBox::indicator:hover {{
            border-color: {PRIMARY_FOCUS};
        }}
        QToolButton {{
            background: {DARK_SURFACE_ALT};
            border: 1px solid {DARK_BORDER};
            border-radius: 6px;
            padding: 3px;
        }}
        QToolButton:hover {{
            background: {DARK_HOVER};
            border-color: {PRIMARY_FOCUS};
        }}
    """


def color_swatch_stylesheet(color_name: str) -> str:
    """Return a high-contrast swatch style for user-selected colors."""
    return f"background: {color_name}; border: 1px solid {DARK_BORDER};"
