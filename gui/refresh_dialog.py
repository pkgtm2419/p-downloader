"""
IDM-Grade Refresh Download Address Dialog.
Enables recovering expired temporary or signed URLs (Rapidgator, Uptobox, Google Drive, Mega)
without losing downloaded segments or restarting from zero.
"""
import webbrowser
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QApplication, QProgressBar, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont

from core.engine import DownloadEngine
from core.segment import validate_refresh_url
from .styles import format_bytes

class URLValidatorThread(QThread):
    finished_validation = pyqtSignal(bool, str, dict)

    def __init__(self, new_url: str, expected_size: int):
        super().__init__()
        self.new_url = new_url
        self.expected_size = expected_size

    def run(self):
        valid, msg, info = validate_refresh_url(self.new_url, self.expected_size)
        self.finished_validation.emit(valid, msg, info)

class RefreshDownloadDialog(QDialog):
    def __init__(self, parent, engine: DownloadEngine, task_id: str):
        super().__init__(parent)
        self.engine = engine
        self.task_id = task_id
        self.validation_thread = None

        self.task_info = self.engine.db.get_download(task_id) or {}
        self.total_bytes = self.task_info.get("total_bytes", 0)
        self.downloaded_bytes = self.task_info.get("downloaded_bytes", 0)
        self.filename = self.task_info.get("filename", "Unknown File")
        self.old_url = self.task_info.get("url", "")

        self.setWindowTitle(f"Refresh Download Address - {self.filename}")
        self.resize(620, 360)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e2430;
                color: #e2e8f0;
                font-family: 'Segoe UI', Tahoma, sans-serif;
            }
            QLabel {
                color: #e2e8f0;
                font-size: 13px;
            }
            QLineEdit {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                color: #f8fafc;
                font-size: 13px;
                selection-background-color: #059669;
            }
            QLineEdit:focus {
                border: 1px solid #10b981;
            }
            QPushButton {
                background-color: #059669;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #10b981;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
            QPushButton#btnSecondary {
                background-color: #334155;
                color: #e2e8f0;
            }
            QPushButton#btnSecondary:hover {
                background-color: #475569;
            }
            QFrame#card {
                background-color: #161e2e;
                border: 1px solid #2d3748;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header Info Card
        card = QFrame(self)
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(6)

        title_lbl = QLabel(f"<b>File:</b> {self.filename}")
        title_lbl.setStyleSheet("font-size: 14px; color: #10b981;")
        card_layout.addWidget(title_lbl)

        progress_pct = (self.downloaded_bytes / self.total_bytes * 100) if self.total_bytes > 0 else 0
        progress_text = f"<b>Progress Saved:</b> {format_bytes(self.downloaded_bytes)} of {format_bytes(self.total_bytes)} ({progress_pct:.1f}%)"
        card_layout.addWidget(QLabel(progress_text))

        old_url_display = self.old_url if len(self.old_url) <= 75 else (self.old_url[:72] + "...")
        card_layout.addWidget(QLabel(f"<b>Expired URL:</b> <span style='color: #94a3b8;'>{old_url_display}</span>"))

        layout.addWidget(card)

        # Instructions
        desc = QLabel(
            "The download session or temporary link has expired. Enter the newly generated download URL below.<br>"
            "P-Downloader will verify the byte range and file length, then resume downloading without losing your progress."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
        layout.addWidget(desc)

        # New URL Input Row
        lbl_new_url = QLabel("<b>New Download URL:</b>")
        layout.addWidget(lbl_new_url)

        url_input_layout = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://...")

        # Pre-populate from clipboard if it holds an HTTP URL
        clip_text = QApplication.clipboard().text().strip()
        if clip_text.startswith("http://") or clip_text.startswith("https://"):
            if clip_text != self.old_url:
                self.url_edit.setText(clip_text)

        url_input_layout.addWidget(self.url_edit)

        btn_paste = QPushButton("📋 Paste", self)
        btn_paste.setObjectName("btnSecondary")
        btn_paste.clicked.connect(self._paste_clipboard)
        url_input_layout.addWidget(btn_paste)

        btn_open_browser = QPushButton("🌐 Open Source Page", self)
        btn_open_browser.setObjectName("btnSecondary")
        btn_open_browser.setToolTip("Opens the original link/domain in your default web browser to obtain a new URL")
        btn_open_browser.clicked.connect(self._open_in_browser)
        url_input_layout.addWidget(btn_open_browser)

        layout.addLayout(url_input_layout)

        # Checkbox & Status
        self.chk_auto_resume = QCheckBox("Resume download automatically after validation")
        self.chk_auto_resume.setChecked(True)
        self.chk_auto_resume.setStyleSheet("color: #cbd5e1;")
        layout.addWidget(self.chk_auto_resume)

        self.status_lbl = QLabel("")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet("font-size: 12px; font-weight: 600;")
        layout.addWidget(self.status_lbl)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setObjectName("btnSecondary")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton("🔄 Refresh & Resume", self)
        self.btn_apply.clicked.connect(self._validate_and_apply)
        btn_layout.addWidget(self.btn_apply)

        layout.addLayout(btn_layout)

    def _paste_clipboard(self):
        clip = QApplication.clipboard().text().strip()
        if clip:
            self.url_edit.setText(clip)

    def _open_in_browser(self):
        if self.old_url:
            webbrowser.open(self.old_url)

    def _validate_and_apply(self):
        new_url = self.url_edit.text().strip()
        if not new_url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid replacement download URL.")
            return

        if not (new_url.startswith("http://") or new_url.startswith("https://")):
            QMessageBox.warning(self, "Invalid URL", "URL must begin with http:// or https://")
            return

        self.btn_apply.setEnabled(False)
        self.status_lbl.setStyleSheet("color: #38bdf8;")
        self.status_lbl.setText("⏳ Verifying new download URL and server byte-range support...")

        self.validation_thread = URLValidatorThread(new_url, self.total_bytes)
        self.validation_thread.finished_validation.connect(self._on_validation_result)
        self.validation_thread.start()

    def _on_validation_result(self, valid: bool, message: str, info: dict):
        self.btn_apply.setEnabled(True)
        new_url = self.url_edit.text().strip()

        if not valid:
            self.status_lbl.setStyleSheet("color: #f87171;")
            self.status_lbl.setText(f"❌ {message}")
            return

        self.status_lbl.setStyleSheet("color: #10b981;")
        self.status_lbl.setText("✅ Verified! Updating download address and resuming...")

        auto_resume = self.chk_auto_resume.isChecked()
        self.engine.refresh_download(self.task_id, new_url, resume_now=auto_resume)

        QMessageBox.information(
            self, "Download Address Refreshed",
            f"Successfully updated download address for '{self.filename}'.\n"
            f"The download will resume from {format_bytes(self.downloaded_bytes)} without any loss of progress."
        )
        self.accept()
