"""
Modern Light-Themed Add Download URL Dialog for P-Downloader.
Features URL validation, background non-blocking metadata detection,
real video quality/format selection, destination validation, and IDM-style controls.
"""
import os
import re
import urllib.parse
import threading
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFileDialog, QSpinBox, QMessageBox,
    QApplication, QGroupBox, QGridLayout, QFrame, QProgressBar
)
from PyQt6.QtGui import QIcon, QFont, QColor
from PyQt6.QtCore import Qt, pyqtSignal

from core.segment import probe_url
from core.categories import (
    get_category_for_filename,
    get_default_save_path,
    CATEGORY_EXTENSIONS,
    sanitize_filename,
    is_generic_route_name
)
from core.torrent import parse_magnet_uri, parse_torrent_file
from core.youtube_downloader import is_youtube_url, is_youtube_playlist, get_selectable_video_formats
from .styles import format_bytes
from .icons import get_icon, COLOR_SLATE, COLOR_WHITE, COLOR_PRIMARY


class AddDownloadDialog(QDialog):
    probe_finished = pyqtSignal(dict)
    probe_failed = pyqtSignal(str)

    def __init__(
        self,
        parent=None,
        initial_url: str = "",
        initial_filename: str = "",
        page_url: str = "",
        quality: str = "",
        headers: Optional[dict] = None,
        referer: str = ""
    ):
        super().__init__(parent)
        self.setWindowTitle("Add Download — P-Downloader")
        self.resize(580, 480)
        self.setMinimumWidth(540)

        icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "logo.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.initial_url = initial_url
        self.initial_filename = initial_filename
        self.page_url = page_url
        self.selected_quality = quality or "best"
        self.selected_format_spec = ""
        self.headers = headers or {}
        if referer and "Referer" not in self.headers and "referer" not in self.headers:
            self.headers["Referer"] = referer
        self.referer = referer
        self.probed_info: Optional[Dict[str, Any]] = None
        self.action = "now"

        self.probe_finished.connect(self._on_probe_success)
        self.probe_failed.connect(self._on_probe_error)

        self._init_ui()

        if self.initial_url:
            self.txt_url.setText(self.initial_url)
            self._start_probe()
        else:
            self._check_clipboard()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(18, 18, 18, 18)

        # ================= Section 1: URL Input =================
        sec1_group = QGroupBox("1. Target URL & Source")
        sec1_layout = QVBoxLayout(sec1_group)
        sec1_layout.setSpacing(8)

        url_row = QHBoxLayout()
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("Paste URL: https://example.com/file.zip or YouTube link...")
        self.txt_url.textChanged.connect(self._on_url_text_changed)

        self.btn_paste = QPushButton("Paste")
        self.btn_paste.setObjectName("secondaryBtn")
        self.btn_paste.setIcon(get_icon("copy", COLOR_SLATE, 16))
        self.btn_paste.setToolTip("Paste URL from clipboard")
        self.btn_paste.clicked.connect(self._paste_clipboard)

        self.btn_detect = QPushButton("Detect")
        self.btn_detect.setObjectName("secondaryBtn")
        self.btn_detect.setIcon(get_icon("search", COLOR_SLATE, 16))
        self.btn_detect.setToolTip("Fetch remote metadata and stream quality options")
        self.btn_detect.clicked.connect(self._start_probe)

        url_row.addWidget(self.txt_url, 1)
        url_row.addWidget(self.btn_paste)
        url_row.addWidget(self.btn_detect)
        sec1_layout.addLayout(url_row)

        # Status badge / indicator
        self.lbl_status = QLabel("Ready to detect.")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 8.5pt;")
        sec1_layout.addWidget(self.lbl_status)

        main_layout.addWidget(sec1_group)

        # ================= Section 2: Quality Selection (for Videos) =================
        self.sec_quality_group = QGroupBox("2. Media Quality & Stream Options")
        sec_quality_layout = QVBoxLayout(self.sec_quality_group)
        sec_quality_layout.setSpacing(8)

        quality_row = QHBoxLayout()
        quality_row.addWidget(QLabel("Quality / Format:"))
        self.cmb_quality = QComboBox()
        self.cmb_quality.currentIndexChanged.connect(self._on_quality_changed)
        quality_row.addWidget(self.cmb_quality, 1)

        self.btn_playlist_options = QPushButton("Playlist Videos...")
        self.btn_playlist_options.setObjectName("secondaryBtn")
        self.btn_playlist_options.setIcon(get_icon("video", COLOR_SLATE, 16))
        self.btn_playlist_options.setVisible(False)
        self.btn_playlist_options.clicked.connect(self._open_playlist_dialog)
        quality_row.addWidget(self.btn_playlist_options)

        sec_quality_layout.addLayout(quality_row)

        self.lbl_quality_note = QLabel("Stream: Full HD 1080p | Auto-merges video + audio with FFmpeg")
        self.lbl_quality_note.setStyleSheet("color: #2563eb; font-size: 8.5pt; font-weight: 500;")
        sec_quality_layout.addWidget(self.lbl_quality_note)

        self.sec_quality_group.setVisible(False)
        main_layout.addWidget(self.sec_quality_group)

        # ================= Section 3: File & Destination Details =================
        sec3_group = QGroupBox("3. Destination & File Properties")
        sec3_layout = QGridLayout(sec3_group)
        sec3_layout.setVerticalSpacing(10)
        sec3_layout.setHorizontalSpacing(10)

        # File Name
        sec3_layout.addWidget(QLabel("File Name:"), 0, 0)
        self.txt_filename = QLineEdit()
        self.txt_filename.textChanged.connect(self._on_filename_changed)
        sec3_layout.addWidget(self.txt_filename, 0, 1)

        # Category
        sec3_layout.addWidget(QLabel("Category:"), 1, 0)
        self.cmb_category = QComboBox()
        self.cmb_category.addItems(["General"] + list(CATEGORY_EXTENSIONS.keys()))
        self.cmb_category.currentTextChanged.connect(self._on_category_changed)
        sec3_layout.addWidget(self.cmb_category, 1, 1)

        # Save Directory
        sec3_layout.addWidget(QLabel("Save Folder:"), 2, 0)
        save_dir_row = QHBoxLayout()
        self.txt_save_dir = QLineEdit()
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.setObjectName("secondaryBtn")
        self.btn_browse.setIcon(get_icon("folder", COLOR_SLATE, 16))
        self.btn_browse.clicked.connect(self._browse_folder)
        save_dir_row.addWidget(self.txt_save_dir, 1)
        save_dir_row.addWidget(self.btn_browse)
        sec3_layout.addLayout(save_dir_row, 2, 1)

        # File Size & Resume Info
        sec3_layout.addWidget(QLabel("Info:"), 3, 0)
        self.lbl_file_meta = QLabel("Size: Unknown | Resume: Verifying...")
        self.lbl_file_meta.setStyleSheet("color: #475569; font-weight: 500;")
        sec3_layout.addWidget(self.lbl_file_meta, 3, 1)

        # Concurrency
        sec3_layout.addWidget(QLabel("Connections:"), 4, 0)
        self.spin_conns = QSpinBox()
        self.spin_conns.setRange(1, 32)
        self.spin_conns.setValue(8)
        self.spin_conns.setSuffix(" parallel threads")
        sec3_layout.addWidget(self.spin_conns, 4, 1)

        main_layout.addWidget(sec3_group)

        main_layout.addStretch()

        # ================= Section 4: Action Buttons =================
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("secondaryBtn")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_later = QPushButton("Download Later")
        self.btn_later.setObjectName("secondaryBtn")
        self.btn_later.setIcon(get_icon("clock", COLOR_SLATE, 16))
        self.btn_later.setToolTip("Queue download without starting immediately")
        self.btn_later.clicked.connect(lambda: self.accept_with_action("later"))

        self.btn_start = QPushButton("Start Downloading")
        self.btn_start.setIcon(get_icon("download", COLOR_WHITE, 16))
        self.btn_start.setToolTip("Begin high-speed accelerated download")
        self.btn_start.clicked.connect(lambda: self.accept_with_action("now"))

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_later)
        btn_layout.addWidget(self.btn_start)
        main_layout.addLayout(btn_layout)

    def _check_clipboard(self):
        cb = QApplication.clipboard()
        text = cb.text().strip()
        if text.startswith(("http://", "https://", "ftp://", "magnet:?")):
            self.txt_url.setText(text)
            self._start_probe()

    def _paste_clipboard(self):
        cb = QApplication.clipboard()
        text = cb.text().strip()
        if text:
            self.txt_url.setText(text)
            self._start_probe()

    def _on_url_text_changed(self, text: str):
        url = text.strip()
        if not url:
            self.btn_start.setEnabled(False)
            return

        is_valid = url.startswith(("http://", "https://", "ftp://", "magnet:?"))
        self.btn_start.setEnabled(is_valid)

        # Only set placeholder filename if filename is currently empty
        if not self.txt_filename.text().strip():
            parsed = urllib.parse.urlparse(url)
            cand = parsed.path.rstrip("/").split("/")[-1].split("?")[0]
            if cand and not is_generic_route_name(cand):
                self.txt_filename.setText(sanitize_filename(cand))
                self._update_destination_paths()

    def _start_probe(self):
        url = self.txt_url.text().strip()
        if not url:
            return

        self.btn_detect.setEnabled(False)
        self.lbl_status.setText("Fetching metadata and quality options from server...")
        self.lbl_status.setStyleSheet("color: #2563eb;")

        def worker():
            try:
                if url.startswith("magnet:?"):
                    meta = parse_magnet_uri(url)
                    info = {
                        "url": url,
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
                        "filename": meta.get("name", "Torrent_Download"),
                        "total_bytes": meta.get("total_bytes", 0),
                        "supports_range": True,
                        "is_torrent": True
                    }
                    self.probe_finished.emit(info)
                else:
                    target = self.page_url if (self.page_url and is_youtube_url(self.page_url)) else url
                    info = probe_url(target, headers=self.headers)
                    try:
                        self.probe_finished.emit(info)
                    except RuntimeError:
                        pass
            except Exception as e:
                try:
                    self.probe_failed.emit(str(e))
                except RuntimeError:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def _on_probe_success(self, info: dict):
        self.btn_detect.setEnabled(True)
        self.probed_info = info
        self.lbl_status.setText("Metadata retrieved successfully.")
        self.lbl_status.setStyleSheet("color: #16a34a;")

        # 1. Update Filename
        remote_fn = info.get("filename", "")
        curr_fn = self.txt_filename.text().strip()
        if not self.initial_filename or is_generic_route_name(curr_fn):
            if remote_fn and not is_generic_route_name(remote_fn):
                self.txt_filename.setText(remote_fn)
            elif info.get("is_youtube"):
                self.txt_filename.setText("YouTube_Video.mp4")

        final_fn = self.txt_filename.text().strip() or "download.bin"

        # 2. Update Category and Save Folder
        cat = get_category_for_filename(final_fn)
        self.cmb_category.setCurrentText(cat)
        default_dir = os.path.dirname(get_default_save_path(final_fn, cat))
        self.txt_save_dir.setText(default_dir)

        # 3. Handle YouTube & Video formats
        if info.get("is_youtube"):
            self.sec_quality_group.setVisible(True)
            self.btn_playlist_options.setVisible(info.get("is_playlist", False))

            formats = info.get("selectable_formats") or get_selectable_video_formats(info.get("formats", []), info.get("total_bytes", 0))
            self.cmb_quality.blockSignals(True)
            self.cmb_quality.clear()
            for fmt in formats:
                label = fmt.get("label", "Standard")
                sz = fmt.get("filesize", 0)
                sz_str = f" ~ {format_bytes(sz)}" if sz > 0 else ""
                self.cmb_quality.addItem(f"{label}{sz_str}", userData=fmt)
            self.cmb_quality.blockSignals(False)

            if info.get("is_playlist"):
                self.lbl_file_meta.setText(f"YouTube Playlist: <b>{info.get('count', 0)} videos</b> detected")
            else:
                sz_val = info.get("total_bytes", 0)
                dur = info.get("duration", 0)
                dur_str = f" | Duration: {dur//60}m {dur%60}s" if dur > 0 else ""
                self.lbl_file_meta.setText(f"Size: <b>{format_bytes(sz_val) if sz_val > 0 else 'Variable (DASH)'}</b>{dur_str} | Multi-threaded Resume: <b>Supported</b>")

            self._on_quality_changed(0)
        else:
            self.sec_quality_group.setVisible(False)
            sz = info.get("total_bytes", 0)
            sz_str = format_bytes(sz) if sz > 0 else "Dynamic / Unknown Length"
            rng_str = "Supported (8-32 connections)" if info.get("supports_range") else "Single Connection"
            self.lbl_file_meta.setText(f"Size: <b>{sz_str}</b> | Multi-threaded Resume: <b>{rng_str}</b>")

        self.btn_start.setEnabled(True)

    def _on_probe_error(self, error_msg: str):
        self.btn_detect.setEnabled(True)
        self.lbl_status.setText(f"Direct detection notice: {error_msg}")
        self.lbl_status.setStyleSheet("color: #d97706;")

        # Safe fallback
        if not self.txt_filename.text().strip():
            url = self.txt_url.text().strip()
            parsed = urllib.parse.urlparse(url)
            cand = parsed.path.rstrip("/").split("/")[-1].split("?")[0]
            if cand and not is_generic_route_name(cand):
                self.txt_filename.setText(sanitize_filename(cand))
            else:
                self.txt_filename.setText("download.bin")
            self._update_destination_paths()

        self.btn_start.setEnabled(True)

    def _on_quality_changed(self, idx: int):
        fmt = self.cmb_quality.currentData()
        if not fmt:
            return

        self.selected_quality = fmt.get("quality", "best")
        self.selected_format_spec = fmt.get("format_spec", "")
        target_ext = fmt.get("ext", "mp4")

        # Update filename extension to match selected container
        curr = self.txt_filename.text().strip()
        if curr:
            stem = os.path.splitext(curr)[0]
            new_fn = f"{stem}.{target_ext}"
            self.txt_filename.blockSignals(True)
            self.txt_filename.setText(new_fn)
            self.txt_filename.blockSignals(False)

        # Update note
        audio_note = "Audio included" if fmt.get("has_audio") else "No audio stream"
        merge_note = "Requires FFmpeg merge" if fmt.get("needs_merge") else "Direct progressive stream"
        self.lbl_quality_note.setText(f"Resolution: {fmt.get('resolution')} | {audio_note} | {merge_note}")

    def _on_filename_changed(self, text: str):
        fn = text.strip()
        if fn:
            cat = get_category_for_filename(fn)
            self.cmb_category.blockSignals(True)
            self.cmb_category.setCurrentText(cat)
            self.cmb_category.blockSignals(False)

    def _on_category_changed(self, cat: str):
        self._update_destination_paths()

    def _update_destination_paths(self):
        fn = self.txt_filename.text().strip() or "download.bin"
        cat = self.cmb_category.currentText()
        default_dir = os.path.dirname(get_default_save_path(fn, cat))
        self.txt_save_dir.setText(default_dir)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.txt_save_dir.text())
        if folder:
            self.txt_save_dir.setText(folder)

    def _open_playlist_dialog(self):
        if self.probed_info and self.probed_info.get("is_playlist"):
            from gui.youtube_dialog import YouTubeDownloadDialog
            dlg = YouTubeDownloadDialog(self.probed_info, self, default_save_dir=self.txt_save_dir.text())
            if dlg.exec():
                self.accept()

    def _open_yt_options(self):
        """Maintains backward compatibility for signal invocations."""
        if self.probed_info and self.probed_info.get("is_playlist"):
            self._open_playlist_dialog()
        else:
            self.sec_quality_group.setVisible(True)

    def accept_with_action(self, action: str):
        url = self.txt_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid download URL.")
            return

        fn = self.txt_filename.text().strip()
        if not fn or is_generic_route_name(fn):
            fn = "download.bin"

        dest_dir = self.txt_save_dir.text().strip()
        if not dest_dir:
            dest_dir = os.path.dirname(get_default_save_path(fn))

        os.makedirs(dest_dir, exist_ok=True)
        self.action = action
        self.accept()

    def get_result(self) -> dict:
        fn = self.txt_filename.text().strip() or "download.bin"
        dest_dir = self.txt_save_dir.text().strip()
        save_path = os.path.join(dest_dir, fn)

        return {
            "url": self.txt_url.text().strip(),
            "filename": fn,
            "save_path": save_path,
            "category": self.cmb_category.currentText(),
            "connections": self.spin_conns.value(),
            "auto_start": (self.action == "now"),
            "quality": self.selected_quality,
            "format_spec": self.selected_format_spec,
            "page_url": self.page_url or self.txt_url.text().strip()
        }
