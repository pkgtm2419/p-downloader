"""
Add New Download URL Dialog.
Auto-reads clipboard, probes remote file details, and configures task settings.
"""
import os
import threading
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFileDialog, QSpinBox, QMessageBox,
    QApplication, QGroupBox, QGridLayout
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import pyqtSignal
from core.segment import probe_url
from core.categories import get_category_for_filename, get_default_save_path, CATEGORY_EXTENSIONS
from core.torrent import is_torrent_or_magnet, parse_magnet_uri, parse_torrent_file
from .styles import format_bytes

class AddDownloadDialog(QDialog):
    probe_finished = pyqtSignal(dict)
    probe_failed = pyqtSignal(str)

    def __init__(self, parent=None, initial_url: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Enter New Download Address")
        self.resize(520, 320)
        
        icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "logo.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.initial_url = initial_url
        self.probed_info = None

        self.probe_finished.connect(self._on_probe_success)
        self.probe_failed.connect(self._on_probe_error)

        self._init_ui()
        self._check_clipboard()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # URL Input Group
        url_group = QGroupBox("Target URL")
        url_layout = QHBoxLayout(url_group)
        
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("https://example.com/file.zip")
        self.txt_url.textChanged.connect(self._on_url_changed)
        
        self.btn_probe = QPushButton("Detect")
        self.btn_probe.setObjectName("secondaryBtn")
        self.btn_probe.clicked.connect(self._start_probe)

        self.btn_torrent = QPushButton("📁 .Torrent...")
        self.btn_torrent.setObjectName("secondaryBtn")
        self.btn_torrent.setToolTip("Open local .torrent file")
        self.btn_torrent.clicked.connect(self._browse_torrent_file)
        
        url_layout.addWidget(self.txt_url)
        url_layout.addWidget(self.btn_probe)
        url_layout.addWidget(self.btn_torrent)
        layout.addWidget(url_group)

        # File Properties Group
        props_group = QGroupBox("Download Properties")
        props_layout = QGridLayout(props_group)
        props_layout.setVerticalSpacing(8)

        # File Name
        props_layout.addWidget(QLabel("File Name:"), 0, 0)
        self.txt_filename = QLineEdit()
        props_layout.addWidget(self.txt_filename, 0, 1)

        # Category
        props_layout.addWidget(QLabel("Category:"), 1, 0)
        self.cmb_category = QComboBox()
        self.cmb_category.addItems(["General"] + list(CATEGORY_EXTENSIONS.keys()))
        self.cmb_category.currentTextChanged.connect(self._on_category_changed)
        props_layout.addWidget(self.cmb_category, 1, 1)

        # Save Path
        props_layout.addWidget(QLabel("Save Directory:"), 2, 0)
        save_layout = QHBoxLayout()
        self.txt_save_dir = QLineEdit()
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.setObjectName("secondaryBtn")
        self.btn_browse.clicked.connect(self._browse_folder)
        save_layout.addWidget(self.txt_save_dir)
        save_layout.addWidget(self.btn_browse)
        props_layout.addLayout(save_layout, 2, 1)

        # Size & Range status
        self.lbl_info = QLabel("File Size: Unknown | Multi-threaded Resume: Unknown")
        self.lbl_info.setStyleSheet("color: #555;")
        props_layout.addWidget(self.lbl_info, 3, 0, 1, 2)

        # Connections count
        props_layout.addWidget(QLabel("Max Connections:"), 4, 0)
        self.spin_connections = QSpinBox()
        self.spin_connections.setRange(1, 32)
        self.spin_connections.setValue(8)
        props_layout.addWidget(self.spin_connections, 4, 1)

        layout.addWidget(props_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_now = QPushButton("Download Now")
        self.btn_now.clicked.connect(lambda: self.accept_with_action("now"))

        self.btn_later = QPushButton("Download Later")
        self.btn_later.setObjectName("secondaryBtn")
        self.btn_later.clicked.connect(lambda: self.accept_with_action("later"))

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("secondaryBtn")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_now)
        btn_layout.addWidget(self.btn_later)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.action = "now"

    def _check_clipboard(self):
        if self.initial_url:
            self.txt_url.setText(self.initial_url)
            self._start_probe()
            return

        cb = QApplication.clipboard()
        text = cb.text().strip()
        if text.startswith("http://") or text.startswith("https://") or text.startswith("ftp://") or text.startswith("magnet:?"):
            self.txt_url.setText(text)
            self._start_probe()

    def _browse_torrent_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Torrent File", "", "Torrent Files (*.torrent);;All Files (*.*)")
        if file_path:
            self.txt_url.setText(file_path)
            self._start_probe()

    def _on_url_changed(self, text: str):
        # Infer quick filename from URL
        parts = text.rstrip("/").split("/")
        if parts:
            cand = parts[-1].split("?")[0]
            if cand and not self.txt_filename.text():
                self.txt_filename.setText(cand)
                self._update_paths()

    def _start_probe(self):
        url = self.txt_url.text().strip()
        if not url:
            return
        self.btn_probe.setEnabled(False)
        self.lbl_info.setText("Detecting file information...")

        def run():
            try:
                if url.startswith("magnet:?"):
                    meta = parse_magnet_uri(url)
                    info = {
                        "url": url,
                        "final_url": url,
                        "filename": meta.get("name", "Torrent_Download"),
                        "total_bytes": meta.get("total_bytes", 0),
                        "supports_range": True,
                        "is_torrent": True
                    }
                    self.probe_finished.emit(info)
                elif url.endswith(".torrent") and os.path.exists(url):
                    meta = parse_torrent_file(url)
                    info = {
                        "url": url,
                        "final_url": url,
                        "filename": meta.get("name", "Torrent_Download"),
                        "total_bytes": meta.get("total_bytes", 0),
                        "supports_range": True,
                        "is_torrent": True
                    }
                    self.probe_finished.emit(info)
                else:
                    info = probe_url(url)
                    self.probe_finished.emit(info)
            except Exception as e:
                self.probe_failed.emit(str(e))

        threading.Thread(target=run, daemon=True).start()

    def _on_probe_success(self, info: dict):
        self.btn_probe.setEnabled(True)
        self.probed_info = info
        self.txt_filename.setText(info["filename"])
        
        cat = get_category_for_filename(info["filename"])
        self.cmb_category.setCurrentText(cat)
        
        default_dir = os.path.dirname(get_default_save_path(info["filename"], cat))
        self.txt_save_dir.setText(default_dir)

        size_text = format_bytes(info["total_bytes"]) if info["total_bytes"] > 0 else "Unknown (Dynamic Stream)"
        range_text = "Supported (Fast 8-32 connections)" if info["supports_range"] else "Not Supported (Single connection)"
        self.lbl_info.setText(f"File Size: <b>{size_text}</b> | Resume: <b>{range_text}</b>")

    def _on_probe_error(self, err: str):
        self.btn_probe.setEnabled(True)
        self.lbl_info.setText(f"<span style='color:red;'>Detection failed: {err}</span>")

    def _on_category_changed(self, category: str):
        fn = self.txt_filename.text().strip() or "download"
        default_dir = os.path.dirname(get_default_save_path(fn, category))
        self.txt_save_dir.setText(default_dir)

    def _update_paths(self):
        fn = self.txt_filename.text().strip()
        cat = get_category_for_filename(fn)
        self.cmb_category.setCurrentText(cat)
        default_dir = os.path.dirname(get_default_save_path(fn, cat))
        self.txt_save_dir.setText(default_dir)

    def _browse_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.txt_save_dir.text())
        if dir_path:
            self.txt_save_dir.setText(dir_path)

    def accept_with_action(self, action: str):
        url = self.txt_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid URL.")
            return
        fn = self.txt_filename.text().strip() or "download"
        save_dir = self.txt_save_dir.text().strip()
        if not save_dir:
            save_dir = os.path.dirname(get_default_save_path(fn, self.cmb_category.currentText()))
            self.txt_save_dir.setText(save_dir)

        self.action = action
        self.accept()

    def get_result(self) -> dict:
        fn = self.txt_filename.text().strip() or "download"
        save_dir = self.txt_save_dir.text().strip()
        return {
            "url": self.txt_url.text().strip(),
            "filename": fn,
            "save_path": os.path.join(save_dir, fn),
            "category": self.cmb_category.currentText(),
            "connections": self.spin_connections.value(),
            "auto_start": (self.action == "now")
        }
