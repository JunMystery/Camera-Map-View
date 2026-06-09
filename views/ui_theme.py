"""Reusable color tokens and Qt stylesheets for application UI surfaces."""

BLACK = "#000000"
DARK_PANEL = "#050505"
DARK_SURFACE = "#0b0b0b"
DARK_SURFACE_ALT = "#111111"
DARK_BORDER = "#2f2f2f"
DARK_HOVER = "#1a1a1a"
DARK_ACTIVE_ROW = "#242424"
LIGHT_BG = "#f8fafc"
LIGHT_ACTIVE_ROW = "#dbeafe"
LIGHT_TEXT = "#111827"
LIGHT_BORDER = "#cbd5e1"
TEXT_ON_DARK = "#f8fafc"
TEXT_MUTED = "#a3a3a3"
TEXT_WHITE = "#ffffff"
PRIMARY = "#2563eb"
PRIMARY_SOFT = "#3b82f6"
PRIMARY_FOCUS = "#93c5fd"
SUCCESS = "#10b981"
DANGER = "#ef4444"
WARNING = "#facc15"
GRID_DARK = "#525252"
GRID_LIGHT = "#64748b"
CANVAS_BG_DARK = "#151515"
CANVAS_BG_LIGHT = "#eef2f7"


def app_stylesheet(light_theme: bool) -> str:
    """Return the global application stylesheet for the selected theme."""
    if light_theme:
        return f"""
            QWidget {{
                background: {LIGHT_BG};
                color: {LIGHT_TEXT};
            }}
            QMenuBar, QMenu, QStatusBar {{
                background: #ffffff;
                color: {LIGHT_TEXT};
                border: 1px solid {LIGHT_BORDER};
            }}
            QMenu::item:selected {{
                background: #e5e7eb;
            }}
            QMenu::item {{
                padding: 6px 76px 6px 16px;
            }}
            QMenu::separator {{
                height: 1px;
                background: {LIGHT_BORDER};
                margin: 4px 8px;
            }}
            QDockWidget::title {{
                background: #e5e7eb;
                color: {LIGHT_TEXT};
                padding: 5px;
            }}
            QTabWidget::pane {{
                background: #ffffff;
                border: 1px solid {LIGHT_BORDER};
                border-radius: 6px;
            }}
            QTabBar::tab {{
                background: #e5e7eb;
                color: {LIGHT_TEXT};
                border: 1px solid {LIGHT_BORDER};
                padding: 8px 10px;
                min-width: 82px;
            }}
            QTabBar::tab:selected {{
                background: #ffffff;
                color: {LIGHT_TEXT};
                border-color: {PRIMARY_SOFT};
            }}
            QTabBar::tab:hover {{
                background: #f1f5f9;
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                background: #ffffff;
                color: {LIGHT_TEXT};
                border: 1px solid {LIGHT_BORDER};
                border-radius: 5px;
                padding: 4px;
            }}
        """
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
        QMenu::item {{
            padding: 6px 76px 6px 16px;
        }}
        QMenu::separator {{
            height: 1px;
            background: {DARK_BORDER};
            margin: 4px 8px;
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
        QTabWidget::pane {{
            background: {DARK_SURFACE};
            border: 1px solid {DARK_BORDER};
            border-radius: 6px;
        }}
        QTabBar::tab {{
            background: {DARK_SURFACE_ALT};
            color: {TEXT_ON_DARK};
            border: 1px solid {DARK_BORDER};
            padding: 8px 10px;
            min-width: 82px;
        }}
        QTabBar::tab:selected {{
            background: {DARK_ACTIVE_ROW};
            color: {TEXT_ON_DARK};
            border-color: {PRIMARY_SOFT};
        }}
        QTabBar::tab:hover {{
            background: {DARK_HOVER};
        }}
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background: {DARK_SURFACE_ALT};
            color: {TEXT_ON_DARK};
            border: 1px solid {DARK_BORDER};
            border-radius: 5px;
            padding: 4px;
        }}
    """


def control_panel_stylesheet(light_theme: bool = False) -> str:
    """Return styles for the combined camera/layout control panel."""
    panel = LIGHT_BG if light_theme else DARK_PANEL
    surface = "#ffffff" if light_theme else DARK_SURFACE_ALT
    hover = "#e5e7eb" if light_theme else DARK_HOVER
    active = LIGHT_ACTIVE_ROW if light_theme else DARK_ACTIVE_ROW
    border = LIGHT_BORDER if light_theme else DARK_BORDER
    text = LIGHT_TEXT if light_theme else TEXT_ON_DARK
    selected_text = LIGHT_TEXT if light_theme else TEXT_WHITE
    return f"""
        QWidget#controlLayoutPanel {{
            background: {panel};
            color: {text};
        }}
        QLabel#sectionTitle {{
            color: {text};
            font-weight: 700;
            padding: 2px 0;
        }}
        QComboBox, QLineEdit, QTreeWidget {{
            background: {surface};
            color: {text};
            border: 1px solid {border};
            border-radius: 7px;
            padding: 5px;
        }}
        QTreeWidget::item {{
            min-height: 26px;
            padding: 3px;
        }}
        QTreeWidget::item:hover {{
            background: {hover};
        }}
        QTreeWidget::item:selected {{
            background: {active};
            color: {selected_text};
        }}
        QToolButton {{
            background: {surface};
            border: 1px solid {border};
            border-radius: 7px;
            padding: 3px;
        }}
        QToolButton:hover {{
            background: {hover};
            border-color: {PRIMARY_FOCUS};
        }}
        QToolButton:checked {{
            background: {PRIMARY};
            border-color: {PRIMARY_FOCUS};
        }}
    """


def drawing_tools_stylesheet(light_theme: bool = False) -> str:
    """Return styles for the fixed floating drawing tools panel."""
    panel = "rgba(255, 255, 255, 242)" if light_theme else "rgba(0, 0, 0, 238)"
    surface = "#ffffff" if light_theme else DARK_SURFACE_ALT
    hover = "#e5e7eb" if light_theme else DARK_HOVER
    border = LIGHT_BORDER if light_theme else DARK_BORDER
    text = LIGHT_TEXT if light_theme else TEXT_ON_DARK
    return f"""
        QWidget#drawingToolsPanel {{
            background: {panel};
            border: 1px solid {border};
            border-radius: 10px;
        }}
        QToolButton {{
            background: {surface};
            border: 1px solid {border};
            border-radius: 7px;
            padding: 4px;
        }}
        QToolButton:hover {{
            background: {hover};
            border-color: {PRIMARY_FOCUS};
        }}
        QToolButton:checked {{
            background: {PRIMARY};
            border-color: {PRIMARY_FOCUS};
        }}
        QMenu {{
            background: {surface};
            color: {text};
            border: 1px solid {border};
            padding: 4px;
        }}
        QMenu::item {{
            padding: 6px 20px;
        }}
        QMenu::item:selected {{
            background: {hover};
        }}
        QMenu::indicator {{
            width: 12px;
            height: 12px;
            border: 1px solid {border};
            border-radius: 6px;
        }}
        QMenu::indicator:checked {{
            background: {PRIMARY_SOFT};
            border-color: {PRIMARY_FOCUS};
        }}
    """


def layers_panel_stylesheet(light_theme: bool = False) -> str:
    """Return styles for the layers panel tree, checkboxes, and action row."""
    panel = LIGHT_BG if light_theme else DARK_PANEL
    surface = "#ffffff" if light_theme else DARK_SURFACE_ALT
    alt = "#f1f5f9" if light_theme else DARK_SURFACE
    header = "#e5e7eb" if light_theme else DARK_ACTIVE_ROW
    hover = "#e5e7eb" if light_theme else DARK_HOVER
    active = LIGHT_ACTIVE_ROW if light_theme else DARK_ACTIVE_ROW
    border = LIGHT_BORDER if light_theme else DARK_BORDER
    text = LIGHT_TEXT if light_theme else TEXT_ON_DARK
    selected_text = LIGHT_TEXT if light_theme else TEXT_WHITE
    checkbox_bg = "#ffffff" if light_theme else BLACK
    return f"""
        QWidget#layersPanel {{
            background: {panel};
            color: {text};
        }}
        QLabel#sectionTitle {{
            color: {text};
            font-weight: 700;
            padding: 2px 0;
        }}
        QTreeWidget#layersTree {{
            background: {surface};
            color: {text};
            border: 1px solid {border};
            border-radius: 8px;
            alternate-background-color: {alt};
            selection-background-color: {active};
            selection-color: {selected_text};
        }}
        QHeaderView::section {{
            background: {header};
            color: {text};
            border: 0;
            border-right: 1px solid {border};
            padding: 5px;
        }}
        QTreeWidget::item {{
            min-height: 28px;
            padding: 3px;
        }}
        QTreeWidget::item:hover {{
            background: {hover};
        }}
        QCheckBox {{
            background: transparent;
            padding: 2px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 5px;
            border: 2px solid {text};
            background: {checkbox_bg};
        }}
        QCheckBox::indicator:checked {{
            background: {PRIMARY_SOFT};
            border-color: {PRIMARY_FOCUS};
        }}
        QCheckBox::indicator:hover {{
            border-color: {PRIMARY_FOCUS};
        }}
        QToolButton {{
            background: {surface};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 3px;
        }}
        QToolButton:hover {{
            background: {hover};
            border-color: {PRIMARY_FOCUS};
        }}
    """


def color_swatch_stylesheet(color_name: str) -> str:
    """Return a high-contrast swatch style for user-selected colors."""
    return f"background: {color_name}; border: 1px solid {DARK_BORDER};"
