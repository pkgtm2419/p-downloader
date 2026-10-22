"""
Comprehensive Modern IDM-Style Theme for P-Downloader.
Ensures 100% dark-mode / light-mode OS compatibility with explicit contrast colors.
"""

MAIN_STYLESHEET = """
/* Base Window & Global Elements */
QMainWindow, QDialog {
    background-color: #f1f5f9;
    color: #0f172a;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Roboto", sans-serif;
    font-size: 13px;
}

QWidget {
    color: #0f172a;
}

/* Menu Bar */
QMenuBar {
    background-color: #ffffff;
    color: #0f172a;
    border-bottom: 1px solid #e2e8f0;
    padding: 3px 6px;
    font-size: 13px;
}

QMenuBar::item {
    background: transparent;
    color: #1e293b;
    padding: 5px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #e2e8f0;
    color: #0f172a;
}

QMenu {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    color: #0f172a;
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #10b981;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: #e2e8f0;
    margin: 4px 6px;
}

/* Modern Ribbon Toolbar */
QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #cbd5e1;
    padding: 6px 8px;
    spacing: 6px;
}

QToolButton {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}

QToolButton:hover {
    background-color: #f0fdf4;
    border-color: #10b981;
    color: #047857;
}

QToolButton:pressed {
    background-color: #dcfce7;
    border-color: #059669;
}

/* Left Sidebar Navigation (TreeWidget) */
QTreeWidget {
    background-color: #f8fafc;
    color: #0f172a;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 4px;
    outline: none;
    selection-background-color: transparent;
    font-family: "Segoe UI", Arial, sans-serif;
}

QTreeWidget::branch {
    background: transparent;
}

QTreeWidget::branch:selected {
    background: transparent;
}

QTreeWidget::item {
    color: #334155;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    margin: 1px 4px;
}

QTreeWidget::item:hover {
    background-color: #f1f5f9;
    color: #0f172a;
}

QTreeWidget::item:selected {
    background-color: #ecfdf5;
    color: #065f46;
    font-weight: 600;
    border-left: 3px solid #10b981;
}

QTreeWidget::item:selected:hover {
    background-color: #d1fae5;
    color: #047857;
}

QTreeWidget::branch {
    background: transparent;
}

/* Splitter between sidebar and table */
QSplitter::handle {
    background-color: #cbd5e1;
    width: 2px;
}

QSplitter::handle:hover {
    background-color: #10b981;
}

/* Main Table Widget */
QTableWidget {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    gridline-color: #f1f5f9;
    selection-background-color: #e6fcf5;
    selection-color: #065f46;
    outline: none;
}

QTableWidget::item {
    color: #0f172a;
    padding: 6px 8px;
    border-bottom: 1px solid #f8fafc;
}

QTableWidget::item:selected {
    background-color: #e6fcf5;
    color: #047857;
    font-weight: 500;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #334155;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #e2e8f0;
    border-right: 1px solid #f1f5f9;
}

QTableCornerButton::section {
    background-color: #f8fafc;
    border: none;
    border-bottom: 2px solid #e2e8f0;
}

/* Progress Bar (IDM Vibrant Dual Gradient) */
QProgressBar {
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    text-align: center;
    background-color: #f1f5f9;
    height: 18px;
    font-size: 11px;
    font-weight: bold;
    color: #0f172a;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #0284c7);
    border-radius: 3px;
}

/* Status Bar */
QStatusBar {
    background-color: #ffffff;
    color: #475569;
    border-top: 1px solid #e2e8f0;
    padding: 2px 6px;
    font-size: 12px;
}

/* Buttons */
QPushButton {
    background-color: #10b981;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #059669;
}

QPushButton:pressed {
    background-color: #047857;
}

QPushButton:disabled {
    background-color: #cbd5e1;
    color: #94a3b8;
}

QPushButton#secondaryBtn {
    background-color: #ffffff;
    color: #334155;
    border: 1px solid #cbd5e1;
}

QPushButton#secondaryBtn:hover {
    background-color: #f8fafc;
    border-color: #94a3b8;
    color: #0f172a;
}

QPushButton#secondaryBtn:pressed {
    background-color: #f1f5f9;
}

/* Input Fields & Combos */
QLineEdit, QComboBox, QSpinBox, QTimeEdit, QTextEdit {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTimeEdit:focus, QTextEdit:focus {
    border: 1px solid #10b981;
    outline: none;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-top: 16px;
    padding: 14px;
    font-weight: 600;
    color: #1e293b;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    background-color: #ffffff;
    color: #047857;
}

QTabWidget::pane {
    border: 1px solid #e2e8f0;
    background-color: #ffffff;
    border-radius: 6px;
    padding: 8px;
}

QTabBar::tab {
    background-color: #f8fafc;
    color: #475569;
    padding: 8px 16px;
    border: 1px solid #e2e8f0;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #10b981;
    font-weight: bold;
    border-top: 3px solid #10b981;
}

QCheckBox, QRadioButton {
    color: #1e293b;
    spacing: 8px;
    font-size: 13px;
}
"""

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
