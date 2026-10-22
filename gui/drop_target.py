"""
IDM-Style Floating Drop Target Widget for P-Downloader.
A translucent, always-on-top desktop basket enabling instant drag-and-drop link catching.
"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QMenu, QApplication
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QRadialGradient,
    QLinearGradient, QDragEnterEvent, QDropEvent, QIcon, QFont, QCursor
)

RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources"))

class FloatingDropTarget(QWidget):
    link_dropped = pyqtSignal(str)

    def __init__(self, parent_window=None):
        super().__init__()
        self.parent_window = parent_window
        self.drag_position = QPoint()

        # Frameless, Always on Top, Tool Window (no taskbar clutter)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAcceptDrops(True)
        self.setFixedSize(130, 130)

        # Default position: top right corner of screen
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            self.move(geom.width() - 160, 60)

        self.setToolTip("P-Downloader Drop Basket\nDrag & drop links from your browser here to download!")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Outer glowing squircle
        rect = self.rect().adjusted(4, 4, -4, -4)

        # Radial dark gradient
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor(22, 30, 46, 230))
        grad.setColorAt(1.0, QColor(15, 23, 42, 240))

        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(16, 185, 129, 200), 2))
        painter.drawRoundedRect(rect, 20, 20)

        # Inner emerald accent ring
        inner_rect = rect.adjusted(12, 12, -12, -12)
        painter.setPen(QPen(QColor(5, 150, 105, 120), 1, Qt.PenStyle.DashLine))
        painter.drawRoundedRect(inner_rect, 14, 14)

        # Draw icon / arrow & text
        painter.setPen(QPen(QColor(16, 185, 129), 2))
        cx = self.width() // 2
        cy = self.height() // 2 - 8

        # Draw 3 flowing downward acceleration lines
        painter.drawLine(cx - 16, cy - 14, cx, cy + 2)
        painter.drawLine(cx, cy - 20, cx, cy + 8)
        painter.drawLine(cx + 16, cy - 14, cx, cy + 2)

        # Downward arrow tip
        painter.drawLine(cx - 10, cy + 4, cx, cy + 14)
        painter.drawLine(cx + 10, cy + 4, cx, cy + 14)

        # Label text
        painter.setPen(QColor(226, 232, 240))
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(0, self.height() - 24, self.width(), 20, Qt.AlignmentFlag.AlignCenter, "DROP LINKS")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if self.parent_window:
            self.parent_window.show()
            self.parent_window.activateWindow()
            self.parent_window.raise_()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e2430;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: #059669;
                color: #ffffff;
            }
        """)

        act_show_main = menu.addAction("🖥️ Show Main Window")
        act_add = menu.addAction("➕ Add Download...")
        menu.addSeparator()
        act_hide = menu.addAction("👁️ Hide Drop Basket")

        action = menu.exec(QCursor.pos())
        if action == act_show_main and self.parent_window:
            self.parent_window.show()
            self.parent_window.activateWindow()
            self.parent_window.raise_()
        elif action == act_add and self.parent_window:
            self.parent_window.show_add_dialog()
        elif action == act_hide:
            self.hide()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        dropped_text = ""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                dropped_text = urls[0].toString()
        elif event.mimeData().hasText():
            dropped_text = event.mimeData().text().strip()

        if dropped_text:
            self.link_dropped.emit(dropped_text)
            if self.parent_window:
                self.parent_window.show_add_dialog(dropped_text)
                self.parent_window.show()
                self.parent_window.activateWindow()
                self.parent_window.raise_()
            event.acceptProposedAction()
