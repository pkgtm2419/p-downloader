"""
Video Stream Quality and Format Selection Dialog.
Allows users to choose desired video resolution (4K, 1080p, 720p, Audio Only),
container format, and output destination before starting download.
"""
import os
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QLineEdit, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt
from gui.styles import format_bytes

class VideoQualityDialog(QDialog):
    def __init__(
        self,
        video_title: str,
        variants: List[Dict[str, Any]],
        default_dir: str,
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Select Video Quality - P-Downloader")
        self.resize(620, 420)

        self.video_title = video_title or "Video_Download"
        self.variants = variants
        self.default_dir = default_dir
        self.selected_variant: Optional[Dict[str, Any]] = None
        self.output_path: str = ""
        self.start_immediately: bool = True

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Video Title Header
        lbl_title = QLabel(f"<b>Title:</b> {self.video_title}")
        lbl_title.setStyleSheet("font-size: 13px; color: #64B5F6;")
        lbl_title.setWordWrap(True)
        layout.addWidget(lbl_title)

        # Quality Variants Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Resolution", "Bitrate", "Codec", "Direct Link"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        self._populate_table()
        layout.addWidget(self.table)

        # Output Path Group
        grp_save = QGroupBox("Save Destination")
        save_layout = QHBoxLayout(grp_save)

        # Sanitize filename
        safe_name = "".join(c for c in self.video_title if c.isalnum() or c in " ._-").strip() or "video"
        if not safe_name.lower().endswith(".mp4"):
            safe_name += ".mp4"

        default_file = os.path.join(self.default_dir, safe_name)
        self.txt_path = QLineEdit(default_file)
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.setObjectName("secondaryBtn")
        self.btn_browse.clicked.connect(self._browse_save)

        save_layout.addWidget(self.txt_path)
        save_layout.addWidget(self.btn_browse)
        layout.addWidget(grp_save)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("secondaryBtn")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_later = QPushButton("Download Later")
        self.btn_later.setObjectName("secondaryBtn")
        self.btn_later.clicked.connect(self._on_download_later)

        self.btn_download = QPushButton("Download Now")
        self.btn_download.clicked.connect(self._on_download_now)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_later)
        btn_layout.addWidget(self.btn_download)
        layout.addLayout(btn_layout)

    def _populate_table(self):
        self.table.setRowCount(len(self.variants))
        for row, v in enumerate(self.variants):
            res = v.get("resolution", "Default")
            bw = v.get("bandwidth", 0)
            bw_str = f"{bw // 1000} kbps" if bw > 0 else "Auto"
            codecs = v.get("codecs", "H.264 / AAC")
            url = v.get("url", "")

            # Highlight 1080p/4K
            res_item = QTableWidgetItem(f"⭐ {res}" if "1080" in res or "2160" in res else res)
            self.table.setItem(row, 0, res_item)
            self.table.setItem(row, 1, QTableWidgetItem(bw_str))
            self.table.setItem(row, 2, QTableWidgetItem(codecs))
            self.table.setItem(row, 3, QTableWidgetItem(url))

        if self.variants:
            self.table.selectRow(0)

    def _browse_save(self):
        curr = self.txt_path.text().strip()
        init_dir = os.path.dirname(curr) if curr else self.default_dir
        fn, _ = QFileDialog.getSaveFileName(self, "Save Video As", curr, "Video Files (*.mp4 *.mkv *.ts);;All Files (*.*)")
        if fn:
            self.txt_path.setText(fn)

    def _on_download_now(self):
        self.start_immediately = True
        self._accept_with_selection()

    def _on_download_later(self):
        self.start_immediately = False
        self._accept_with_selection()

    def _accept_with_selection(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.variants):
            QMessageBox.warning(self, "No Selection", "Please select a video quality to download.")
            return

        self.selected_variant = self.variants[row]
        self.output_path = self.txt_path.text().strip()
        if not self.output_path:
            QMessageBox.warning(self, "Missing Path", "Please specify a valid save file path.")
            return

        self.accept()
