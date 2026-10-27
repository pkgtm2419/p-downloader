"""
Quick Mini-Prompt Dialog for Clipboard & Browser Interceptions.
Floats near the system tray / bottom-right corner of the desktop,
allowing one-click download capture without stealing focus from active apps.
"""
import os
from urllib.parse import urlparse, unquote
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor

class QuickPromptDialog(QDialog):
    download_requested = pyqtSignal(str, bool) # url, start_now

    def __init__(self, url: str, parent=None, auto_close_sec: int = 15):
        super().__init__(parent)
        self.url = url
        self.auto_close_sec = auto_close_sec

        # Frameless floating tool window that stays on top
        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(380, 160)

        self._init_ui()
        self._position_bottom_right()

        # Auto-dismiss timer
        if auto_close_sec > 0:
            self.dismiss_timer = QTimer(self)
            self.dismiss_timer.setSingleShot(True)
            self.dismiss_timer.timeout.connect(self.reject)
            self.dismiss_timer.start(auto_close_sec * 1000)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background: #1E2128;
                border: 1px solid #1E88E5;
                border-radius: 10px;
            }
        """)
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(14, 12, 14, 12)
        c_layout.setSpacing(8)

        # Header with Logo & Close
        header = QHBoxLayout()
        lbl_title = QLabel("⚡ <b>P-Downloader Ultra</b>")
        lbl_title.setStyleSheet("color: #64B5F6; font-size: 13px; border: none;")
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(20, 20)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8E9297;
                border: none;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #FFFFFF;
            }
        """)
        btn_close.clicked.connect(self.reject)

        header.addWidget(lbl_title)
        header.addStretch()
        header.addWidget(btn_close)
        c_layout.addLayout(header)

        # Inferred Filename
        parsed = urlparse(self.url)
        path = unquote(parsed.path)
        filename = os.path.basename(path) or "download"
        if len(filename) > 42:
            filename = filename[:39] + "..."

        lbl_file = QLabel(filename)
        lbl_file.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: bold; border: none;")
        c_layout.addWidget(lbl_file)

        # Subtitle / URL
        disp_url = self.url if len(self.url) <= 50 else self.url[:47] + "..."
        lbl_url = QLabel(disp_url)
        lbl_url.setStyleSheet("color: #8E9297; font-size: 11px; border: none;")
        c_layout.addWidget(lbl_url)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_later = QPushButton("Download Later")
        btn_later.setStyleSheet("""
            QPushButton {
                background: #2C3038;
                color: #E0E0E0;
                border: 1px solid #3E4451;
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #3A404D;
            }
        """)
        btn_later.clicked.connect(lambda: self._trigger(False))

        btn_now = QPushButton("Download Now")
        btn_now.setStyleSheet("""
            QPushButton {
                background: #1E88E5;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1976D2;
            }
        """)
        btn_now.clicked.connect(lambda: self._trigger(True))

        btn_row.addStretch()
        btn_row.addWidget(btn_later)
        btn_row.addWidget(btn_now)
        c_layout.addLayout(btn_row)

        main_layout.addWidget(container)

    def _position_bottom_right(self):
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            x = avail.right() - self.width() - 15
            y = avail.bottom() - self.height() - 15
            self.move(x, y)

    def _trigger(self, start_now: bool):
        self.download_requested.emit(self.url, start_now)
        self.accept()
