"""
YouTube Single Video & Playlist Download Dialog for P-Downloader.
Provides format selection, playlist batch selection, audio extraction,
and responsive non-blocking background queue ingestion.
"""
import os
import re
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFileDialog, QListWidget, QListWidgetItem,
    QProgressBar, QGroupBox, QFrame, QCheckBox, QMessageBox, QApplication
)
from PyQt6.QtGui import QIcon, QFont, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal

from core.categories import sanitize_filename, get_default_save_path
from .icons import get_icon, COLOR_SLATE, COLOR_WHITE, COLOR_PRIMARY

RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources"))


def format_duration(seconds: int) -> str:
    if not seconds or seconds <= 0:
        return "--:--"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class YouTubeDownloadDialog(QDialog):
    def __init__(self, metadata: Dict[str, Any], parent=None, default_save_dir: str = ""):
        super().__init__(parent)
        self.metadata = metadata
        self.is_playlist = metadata.get("is_playlist", False)
        self.default_save_dir = default_save_dir or os.path.expanduser("~/Downloads")

        title_prefix = "YouTube Playlist" if self.is_playlist else "YouTube Video"
        self.setWindowTitle(f"P-Downloader - Download {title_prefix}")
        self.resize(600, 520 if self.is_playlist else 360)
        self.setMinimumSize(540, 320)

        icon_path = os.path.join(RESOURCES_DIR, "logo.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.selected_items: List[Dict[str, Any]] = []
        self.selected_quality = "1080p"
        self.save_directory = self.default_save_dir
        self.start_immediately = True

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Header Card
        header_card = QFrame()
        header_card.setObjectName("card")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(12)

        icon_lbl = QLabel()
        yt_icon_path = os.path.join(RESOURCES_DIR, "logo.png")
        if os.path.exists(yt_icon_path):
            pix = QPixmap(yt_icon_path).scaled(42, 42, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_lbl.setPixmap(pix)
        header_layout.addWidget(icon_lbl)

        info_vbox = QVBoxLayout()
        info_vbox.setSpacing(4)
        title_text = self.metadata.get("title") or ("YouTube Playlist" if self.is_playlist else "YouTube Video")
        lbl_title = QLabel(f"<b>{title_text}</b>")
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2563EB;")
        info_vbox.addWidget(lbl_title)

        if self.is_playlist:
            count = self.metadata.get("count", len(self.metadata.get("entries", [])))
            sub_lbl = QLabel(f"Playlist detected: <b>{count} video(s)</b> found")
            sub_lbl.setStyleSheet("color: #64748B; font-size: 12px;")
            info_vbox.addWidget(sub_lbl)
        else:
            dur = format_duration(self.metadata.get("duration", 0))
            sub_lbl = QLabel(f"Video Duration: <b>{dur}</b>")
            sub_lbl.setStyleSheet("color: #64748B; font-size: 12px;")
            info_vbox.addWidget(sub_lbl)

        header_layout.addLayout(info_vbox)
        header_layout.addStretch()
        main_layout.addWidget(header_card)

        # Playlist Items Section (if playlist)
        if self.is_playlist:
            pl_group = QGroupBox(f"Select Playlist Videos ({self.metadata.get('count', 0)})")
            pl_layout = QVBoxLayout(pl_group)
            pl_layout.setSpacing(8)

            # Select All / None bar
            ctrl_bar = QHBoxLayout()
            self.chk_all = QCheckBox("Select All")
            self.chk_all.setChecked(True)
            self.chk_all.stateChanged.connect(self._toggle_select_all)
            ctrl_bar.addWidget(self.chk_all)

            self.lbl_selected_count = QLabel("")
            self.lbl_selected_count.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
            ctrl_bar.addWidget(self.lbl_selected_count)
            ctrl_bar.addStretch()

            pl_layout.addLayout(ctrl_bar)

            # List of items with checkboxes
            self.list_widget = QListWidget()
            self.list_widget.setStyleSheet("""
                QListWidget {
                    background-color: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    padding: 4px;
                    color: #f0f6fc;
                }
                QListWidget::item {
                    padding: 6px;
                    border-bottom: 1px solid #21262d;
                }
                QListWidget::item:hover {
                    background-color: #1f2937;
                }
            """)
            entries = self.metadata.get("entries", [])
            for e in entries:
                idx = e.get("index", 1)
                dur = format_duration(e.get("duration", 0))
                item_text = f"#{idx:02d}  {e.get('title', 'Video')}  ({dur})"
                item = QListWidgetItem(item_text, self.list_widget)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                item.setData(Qt.ItemDataRole.UserRole, e)

            self.list_widget.itemChanged.connect(self._update_selected_count)
            pl_layout.addWidget(self.list_widget)
            main_layout.addWidget(pl_group)
            self._update_selected_count()

        # Settings Group: Format & Quality + Destination
        cfg_group = QGroupBox("Download Settings")
        cfg_layout = QVBoxLayout(cfg_group)
        cfg_layout.setSpacing(10)

        # Quality Picker
        q_box = QHBoxLayout()
        q_lbl = QLabel("Resolution & Format:")
        q_lbl.setFixedWidth(130)
        self.cmb_quality = QComboBox()
        self.cmb_quality.addItems([
            "1080p Full HD (MP4)",
            "720p HD (MP4)",
            "480p Standard (MP4)",
            "360p Low (MP4)",
            "Best Available Video (MP4)",
            "Extract Audio Only - MP3 (192 kbps)",
            "Extract Audio Only - M4A"
        ])
        q_box.addWidget(q_lbl)
        q_box.addWidget(self.cmb_quality)
        cfg_layout.addLayout(q_box)

        # Single video custom filename
        if not self.is_playlist:
            fn_box = QHBoxLayout()
            fn_lbl = QLabel("Save Filename:")
            fn_lbl.setFixedWidth(130)
            self.txt_filename = QLineEdit()
            init_fn = self.metadata.get("filename") or "YouTube_Video.mp4"
            self.txt_filename.setText(init_fn)
            fn_box.addWidget(fn_lbl)
            fn_box.addWidget(self.txt_filename)
            cfg_layout.addLayout(fn_box)

        # Destination Folder
        dest_box = QHBoxLayout()
        dest_lbl = QLabel("Save Folder:")
        dest_lbl.setFixedWidth(130)
        self.txt_dest = QLineEdit(self.default_save_dir)
        btn_browse = QPushButton("Browse...")
        btn_browse.setObjectName("secondaryBtn")
        btn_browse.setIcon(get_icon("folder", COLOR_SLATE, 16))
        btn_browse.clicked.connect(self._browse_dest)
        dest_box.addWidget(dest_lbl)
        dest_box.addWidget(self.txt_dest)
        dest_box.addWidget(btn_browse)
        cfg_layout.addLayout(dest_box)

        main_layout.addWidget(cfg_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_now = QPushButton("Download Now")
        self.btn_now.setIcon(get_icon("download", COLOR_WHITE, 16))
        self.btn_now.clicked.connect(self._on_download_now)
        btn_layout.addWidget(self.btn_now)

        self.btn_queue = QPushButton("Add to Queue")
        self.btn_queue.setObjectName("secondaryBtn")
        self.btn_queue.setIcon(get_icon("clock", COLOR_SLATE, 16))
        self.btn_queue.clicked.connect(self._on_download_later)
        btn_layout.addWidget(self.btn_queue)

        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondaryBtn")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        main_layout.addLayout(btn_layout)

    def _toggle_select_all(self, state):
        checked = (state == 2 or state == Qt.CheckState.Checked.value)
        if hasattr(self, "list_widget"):
            self.list_widget.blockSignals(True)
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self.list_widget.blockSignals(False)
            self._update_selected_count()

    def _update_selected_count(self):
        if not hasattr(self, "list_widget"):
            return
        selected = 0
        total = self.list_widget.count()
        for i in range(total):
            if self.list_widget.item(i).checkState() == Qt.CheckState.Checked:
                selected += 1
        self.lbl_selected_count.setText(f"{selected} of {total} selected")
        if hasattr(self, "btn_now"):
            self.btn_now.setEnabled(selected > 0)
        if hasattr(self, "btn_queue"):
            self.btn_queue.setEnabled(selected > 0)

    def _browse_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.txt_dest.text())
        if folder:
            self.txt_dest.setText(folder)

    def _get_quality_token(self) -> str:
        text = self.cmb_quality.currentText()
        if "1080p" in text:
            return "1080p"
        if "720p" in text:
            return "720p"
        if "480p" in text:
            return "480p"
        if "360p" in text:
            return "360p"
        if "MP3" in text:
            return "audio_mp3"
        if "M4A" in text:
            return "audio_m4a"
        return "best"

    def _on_download_now(self):
        self.start_immediately = True
        self._commit_selection()

    def _on_download_later(self):
        self.start_immediately = False
        self._commit_selection()

    def _commit_selection(self):
        self.save_directory = self.txt_dest.text().strip() or self.default_save_dir
        self.selected_quality = self._get_quality_token()

        if self.is_playlist:
            self.selected_items = []
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    data = item.data(Qt.ItemDataRole.UserRole)
                    if data:
                        raw_title = data.get("title") or f"Video_{data.get('index', i+1)}"
                        safe_title = sanitize_filename(raw_title)
                        ext = ".mp3" if self.selected_quality == "audio_mp3" else (".m4a" if self.selected_quality == "audio_m4a" else ".mp4")
                        fn = f"{safe_title}{ext}"
                        self.selected_items.append({
                            "url": data.get("url"),
                            "filename": fn,
                            "save_path": os.path.join(self.save_directory, fn),
                            "quality": self.selected_quality,
                            "category": "Music" if "audio" in self.selected_quality else "Video",
                            "connections": 8,
                            "auto_start": self.start_immediately
                        })
            if not self.selected_items:
                QMessageBox.warning(self, "No Videos Selected", "Please select at least one video to download.")
                return
        else:
            raw_fn = self.txt_filename.text().strip() or self.metadata.get("filename") or "YouTube_Video.mp4"
            if self.selected_quality == "audio_mp3" and not raw_fn.lower().endswith(".mp3"):
                raw_fn = os.path.splitext(raw_fn)[0] + ".mp3"
            elif self.selected_quality == "audio_m4a" and not raw_fn.lower().endswith(".m4a"):
                raw_fn = os.path.splitext(raw_fn)[0] + ".m4a"
            elif "audio" not in self.selected_quality and not raw_fn.lower().endswith((".mp4", ".mkv", ".webm")):
                raw_fn = os.path.splitext(raw_fn)[0] + ".mp4"

            safe_fn = sanitize_filename(raw_fn)
            self.selected_items = [{
                "url": self.metadata.get("url"),
                "filename": safe_fn,
                "save_path": os.path.join(self.save_directory, safe_fn),
                "quality": self.selected_quality,
                "category": "Music" if "audio" in self.selected_quality else "Video",
                "connections": 8,
                "auto_start": self.start_immediately
            }]

        self.accept()

