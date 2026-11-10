"""
Comprehensive Modern IDM-Grade Design System and Stylesheet for P-Downloader.
Strictly adheres to the defined palette:
- Main background: #F4F7FB
- Sidebar background: #FFFFFF
- Main content surface: #FFFFFF
- Primary blue: #2563EB (Hover: #1D4ED8, Active: #1E40AF)
- Primary light background: #EFF6FF
- Main text: #172033
- Secondary text: #64748B
- Borders: #E2E8F0
- Table alternate row: #F8FAFC
- Success: #16A34A, Warning: #D97706, Error: #DC2626
"""

LIGHT_THEME_STYLESHEET = """
/* Global Window & Surface Canvas */
QMainWindow, QDialog {
    background-color: #f4f7fb;
    color: #172033;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Inter", "Roboto", "Helvetica Neue", Arial, sans-serif;
    font-size: 10pt;
}

QWidget {
    color: #172033;
    background-color: transparent;
    selection-background-color: #eff6ff;
    selection-color: #2563eb;
}

/* Central Card Containers */
QFrame#card, QWidget#card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}

/* Top Menu Bar */
QMenuBar {
    background-color: #FFFFFF;
    color: #172033;
    border-bottom: 1px solid #E2E8F0;
    padding: 3px 6px;
    font-size: 9.5pt;
}

QMenuBar::item {
    background: transparent;
    color: #172033;
    padding: 5px 10px;
    border-radius: 5px;
}

QMenuBar::item:selected, QMenuBar::item:pressed {
    background-color: #EFF6FF;
    color: #2563EB;
}

/* Context & Dropdown Menus */
QMenu {
    background-color: #FFFFFF;
    color: #172033;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 6px;
    font-size: 9.5pt;
}

QMenu::item {
    color: #172033;
    padding: 7px 26px 7px 12px;
    border-radius: 5px;
}

QMenu::item:selected {
    background-color: #EFF6FF;
    color: #2563EB;
}

QMenu::item:disabled {
    color: #94A3B8;
    background-color: transparent;
}

QMenu::separator {
    height: 1px;
    background-color: #E2E8F0;
    margin: 4px 8px;
}

/* Modern Action Toolbar */
QToolBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
    padding: 6px 12px;
    spacing: 6px;
}

QToolButton {
    background-color: #FFFFFF;
    color: #172033;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
    font-size: 9pt;
    min-height: 22px;
}

QToolButton:hover {
    background-color: #F8FAFC;
    border-color: #CBD5E1;
    color: #2563EB;
}

QToolButton:pressed {
    background-color: #EFF6FF;
    border-color: #2563EB;
    color: #1D4ED8;
}

QToolButton:disabled {
    background-color: #F8FAFC;
    color: #94A3B8;
    border-color: #E2E8F0;
}

/* Primary Action Button (Add URL) */
QToolButton#primaryBtn {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #1D4ED8;
    font-weight: 600;
}

QToolButton#primaryBtn:hover {
    background-color: #1D4ED8;
    border-color: #1E40AF;
    color: #FFFFFF;
}

QToolButton#primaryBtn:pressed {
    background-color: #1E40AF;
    color: #FFFFFF;
}

/* Destructive Action (Delete) */
QToolButton#dangerBtn {
    color: #DC2626;
    border: 1px solid #FECACA;
    background-color: #FFFFFF;
}

QToolButton#dangerBtn:hover {
    background-color: #FEF2F2;
    border-color: #F87171;
    color: #DC2626;
}

/* Left Navigation Sidebar Panel */
QWidget#sidebarContainer {
    background-color: #FFFFFF;
    border-right: 1px solid #E2E8F0;
}

QTreeWidget#sidebarTree {
    background-color: #FFFFFF;
    color: #172033;
    border: none;
    padding: 6px 4px;
    font-size: 9.5pt;
}

QTreeWidget#sidebarTree::item {
    padding: 8px 10px;
    border-radius: 6px;
    color: #172033;
    margin: 1px 4px;
}

QTreeWidget#sidebarTree::item:hover {
    background-color: #F8FAFC;
    color: #172033;
}

QTreeWidget#sidebarTree::item:selected {
    background-color: #EFF6FF;
    color: #2563EB;
    font-weight: 600;
    border-left: 3px solid #2563EB;
}

/* Main Downloads Data Table */
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f8fafc;
    color: #172033;
    gridline-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    selection-background-color: #eff6ff;
    selection-color: #0f172a;
    font-size: 9.5pt;
    outline: none;
}

/* Empty State Container */
QWidget#emptyStateContainer {
    background-color: #ffffff;
    border: 1px dashed #cbd5e1;
    border-radius: 8px;
}

QLabel#emptyStateTitle {
    color: #172033;
    font-size: 13pt;
    font-weight: 600;
}

QLabel#emptyStateSubtitle {
    color: #64748b;
    font-size: 9.5pt;
}

QTableWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #F1F5F9;
}

QTableWidget::item:selected {
    background-color: #EFF6FF;
    color: #172033;
}

QHeaderView::section {
    background-color: #F8FAFC;
    color: #475569;
    font-weight: 600;
    font-size: 8.5pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 9px 12px;
    border: none;
    border-bottom: 1px solid #E2E8F0;
    border-right: 1px solid #F1F5F9;
}

QHeaderView::section:hover {
    background-color: #EFF6FF;
    color: #2563EB;
}

/* Table Row Action Menu Button */
QPushButton#actionMenuBtn {
    background-color: transparent;
    color: #64748B;
    border: 1px solid transparent;
    border-radius: 5px;
    font-size: 11pt;
    font-weight: bold;
    padding: 3px 6px;
    min-width: 28px;
    max-width: 28px;
    height: 24px;
}

QPushButton#actionMenuBtn:hover {
    background-color: #EFF6FF;
    border-color: #BFDBFE;
    color: #2563EB;
}

/* In-Table & Dialog Progress Bars */
QProgressBar {
    background-color: #E2E8F0;
    border: none;
    border-radius: 5px;
    text-align: center;
    font-weight: 600;
    font-size: 8.5pt;
    color: #172033;
    min-height: 18px;
    max-height: 18px;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #2563EB);
    border-radius: 5px;
}

/* Push Buttons (Standard Dialogs & Modals) */
QPushButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #1D4ED8;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
    font-size: 9.5pt;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #1D4ED8;
    border-color: #1E40AF;
}

QPushButton:pressed {
    background-color: #1E40AF;
}

QPushButton:disabled {
    background-color: #F1F5F9;
    color: #94A3B8;
    border-color: #E2E8F0;
}

QPushButton#secondaryBtn {
    background-color: #FFFFFF;
    color: #172033;
    border: 1px solid #CBD5E1;
    font-weight: 500;
}

QPushButton#secondaryBtn:hover {
    background-color: #F8FAFC;
    color: #2563EB;
    border-color: #93C5FD;
}

QPushButton#dangerBtn {
    background-color: #DC2626;
    color: #FFFFFF;
    border: 1px solid #B91C1C;
}

QPushButton#dangerBtn:hover {
    background-color: #B91C1C;
    border-color: #991B1B;
}

/* Input Fields & Dropdowns */
QLineEdit, QSpinBox, QComboBox {
    background-color: #FFFFFF;
    color: #172033;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 7px 11px;
    font-size: 9.5pt;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #2563EB;
    background-color: #FFFFFF;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #172033;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    selection-background-color: #EFF6FF;
    selection-color: #2563EB;
    padding: 4px;
}

/* Group Boxes */
QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    font-weight: 600;
    font-size: 9.5pt;
    margin-top: 14px;
    padding-top: 18px;
    color: #172033;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #2563EB;
}

/* Checkboxes */
QCheckBox {
    color: #172033;
    font-size: 9.5pt;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1px solid #CBD5E1;
    background-color: #FFFFFF;
}

QCheckBox::indicator:checked {
    background-color: #2563EB;
    border-color: #1D4ED8;
}

/* Bottom Status Bar */
QStatusBar {
    background-color: #FFFFFF;
    color: #64748B;
    border-top: 1px solid #E2E8F0;
    font-size: 8.5pt;
    padding: 3px 10px;
}

QStatusBar QLabel {
    color: #64748B;
}

/* Dark Tooltips */
QToolTip {
    background-color: #172033;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 5px;
    padding: 5px 9px;
    font-size: 8.5pt;
}

/* Thin Elegant Scrollbars */
QScrollBar:vertical {
    background-color: #F8FAFC;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #CBD5E1;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #94A3B8;
}

QScrollBar:horizontal {
    background-color: #F8FAFC;
    height: 8px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #CBD5E1;
    min-width: 24px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #94A3B8;
}

QScrollBar::add-line, QScrollBar::sub-line {
    border: none;
    background: none;
}
"""

MAIN_STYLESHEET = LIGHT_THEME_STYLESHEET

THEME_PALETTES = {
    "fluent_light": {
        "bg": "#f4f7fb", "surface": "#ffffff", "border": "#e2e8f0",
        "text": "#172033", "text_muted": "#64748b",
        "primary": "#2563eb", "primary_hover": "#1d4ed8",
        "row_alt": "#f8fafc", "select_bg": "#eff6ff", "select_fg": "#2563eb"
    },
    "fluent_dark": {
        "bg": "#121418", "surface": "#1c1f26", "border": "#2a2e38",
        "text": "#e1e4e8", "text_muted": "#8a94a6",
        "primary": "#0078d4", "primary_hover": "#1084d8",
        "row_alt": "#161920", "select_bg": "#263040", "select_fg": "#38a4ff"
    },
    "classic_98": {
        "bg": "#c0c0c0", "surface": "#ffffff", "border": "#808080",
        "text": "#000000", "text_muted": "#404040",
        "primary": "#000080", "primary_hover": "#1010a0",
        "row_alt": "#efefef", "select_bg": "#000080", "select_fg": "#ffffff"
    },
    "aero_neon": {
        "bg": "#0a0f1d", "surface": "#121a2f", "border": "#1f2d4f",
        "text": "#d9e6ff", "text_muted": "#758fb8",
        "primary": "#00f0ff", "primary_hover": "#33f3ff",
        "row_alt": "#0d1426", "select_bg": "#172747", "select_fg": "#00f0ff"
    },
    "dracula": {
        "bg": "#282a36", "surface": "#44475a", "border": "#6272a4",
        "text": "#f8f8f2", "text_muted": "#99a2c2",
        "primary": "#bd93f9", "primary_hover": "#cfaafc",
        "row_alt": "#343746", "select_bg": "#44475a", "select_fg": "#ff79c6"
    },
    "nord": {
        "bg": "#2e3440", "surface": "#3b4252", "border": "#4c566a",
        "text": "#eceff4", "text_muted": "#8892b0",
        "primary": "#88c0d0", "primary_hover": "#81a1c1",
        "row_alt": "#353c4a", "select_bg": "#434c5e", "select_fg": "#88c0d0"
    },
    "monokai": {
        "bg": "#272822", "surface": "#3e3d32", "border": "#49483e",
        "text": "#f8f8f2", "text_muted": "#8f908a",
        "primary": "#a6e22e", "primary_hover": "#b7eb46",
        "row_alt": "#32332a", "select_bg": "#49483e", "select_fg": "#a6e22e"
    },
    "cyberpunk": {
        "bg": "#181926", "surface": "#24273a", "border": "#ff0055",
        "text": "#cad3f5", "text_muted": "#8087a2",
        "primary": "#fcee0a", "primary_hover": "#fffa65",
        "row_alt": "#1e2030", "select_bg": "#363a4f", "select_fg": "#fcee0a"
    },
    "high_contrast": {
        "bg": "#000000", "surface": "#121212", "border": "#ffffff",
        "text": "#ffffff", "text_muted": "#d0d0d0",
        "primary": "#ffff00", "primary_hover": "#ffff55",
        "row_alt": "#1a1a1a", "select_bg": "#ffff00", "select_fg": "#000000"
    }
}

# Aliases
THEME_PALETTES["light"] = THEME_PALETTES["fluent_light"]
THEME_PALETTES["dark"] = THEME_PALETTES["fluent_dark"]


def _build_theme_stylesheet(p: dict) -> str:
    return f"""
QMainWindow, QDialog {{
    background-color: {p['bg']};
    color: {p['text']};
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Inter", "Roboto", sans-serif;
    font-size: 10pt;
}}

QWidget {{
    color: {p['text']};
    background-color: transparent;
    selection-background-color: {p['select_bg']};
    selection-color: {p['select_fg']};
}}

QFrame#card, QWidget#card {{
    background-color: {p['surface']};
    border: 1px solid {p['border']};
    border-radius: 8px;
}}

QMenuBar {{
    background-color: {p['surface']};
    color: {p['text']};
    border-bottom: 1px solid {p['border']};
    padding: 3px 6px;
    font-size: 9.5pt;
}}

QMenuBar::item:selected, QMenuBar::item:pressed {{
    background-color: {p['select_bg']};
    color: {p['primary']};
}}

QMenu {{
    background-color: {p['surface']};
    color: {p['text']};
    border: 1px solid {p['border']};
    border-radius: 8px;
    padding: 6px;
}}

QMenu::item:selected {{
    background-color: {p['select_bg']};
    color: {p['primary']};
}}

QToolBar {{
    background-color: {p['surface']};
    border-bottom: 1px solid {p['border']};
    padding: 6px 12px;
    spacing: 6px;
}}

QToolButton {{
    background-color: transparent;
    color: {p['text']};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px 10px;
    font-weight: 500;
}}

QToolButton:hover {{
    background-color: {p['select_bg']};
    border: 1px solid {p['border']};
    color: {p['primary']};
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {p['surface']};
    color: {p['text']};
    border: 1px solid {p['border']};
    border-radius: 6px;
    padding: 6px 10px;
}}

QLineEdit:focus {{
    border: 1.5px solid {p['primary']};
}}

QPushButton {{
    background-color: {p['primary']};
    color: #ffffff;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {p['primary_hover']};
}}

QPushButton#secondaryBtn {{
    background-color: {p['surface']};
    color: {p['text']};
    border: 1px solid {p['border']};
}}

QPushButton#secondaryBtn:hover {{
    background-color: {p['select_bg']};
}}

QTableView, QTableWidget {{
    background-color: {p['surface']};
    alternate-background-color: {p['row_alt']};
    color: {p['text']};
    border: 1px solid {p['border']};
    border-radius: 6px;
    gridline-color: {p['border']};
}}

QHeaderView::section {{
    background-color: {p['surface']};
    color: {p['text_muted']};
    border: none;
    border-bottom: 1px solid {p['border']};
    padding: 6px 8px;
    font-weight: 600;
}}

QProgressBar {{
    background-color: {p['border']};
    color: {p['text']};
    border: none;
    border-radius: 4px;
    text-align: center;
    font-size: 10px;
}}

QProgressBar::chunk {{
    background-color: {p['primary']};
    border-radius: 4px;
}}

QScrollBar:vertical, QScrollBar:horizontal {{
    background-color: {p['bg']};
    border: none;
    margin: 0;
}}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background-color: {p['border']};
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
    background-color: {p['primary']};
}}
"""


def list_themes() -> list:
    """Returns list of all available theme names."""
    return [
        "fluent_light", "fluent_dark", "classic_98", "aero_neon",
        "dracula", "nord", "monokai", "cyberpunk", "high_contrast"
    ]


def get_theme_stylesheet(name: str = "fluent_light") -> str:
    """Returns the CSS stylesheet for the requested theme."""
    clean = name.lower().strip()
    if clean in ("light", "fluent_light") and "LIGHT_THEME_STYLESHEET" in globals():
        return LIGHT_THEME_STYLESHEET
    palette = THEME_PALETTES.get(clean, THEME_PALETTES["fluent_light"])
    return _build_theme_stylesheet(palette)

def format_bytes(num_bytes: int) -> str:
    if num_bytes <= 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} PB"

def format_speed(bytes_per_sec: float) -> str:
    return f"{format_bytes(int(bytes_per_sec))}/s"

def format_eta(remaining_bytes: int, speed: float) -> str:
    if speed <= 0 or remaining_bytes <= 0:
        return "--:--:--"
    seconds = int(remaining_bytes / speed)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 99:
        return "> 99 hours"
    return f"{h:02d}:{m:02d}:{s:02d}"
