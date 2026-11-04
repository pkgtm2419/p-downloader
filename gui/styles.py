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

def get_theme_stylesheet(name: str = "light") -> str:
    """Returns the CSS stylesheet for the requested theme."""
    return LIGHT_THEME_STYLESHEET

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
