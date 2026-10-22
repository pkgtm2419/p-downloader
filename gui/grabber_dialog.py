"""
Site Grabber and Media Sniffer Dialog (IDM Feature).
Crawls a webpage, discovers downloadable media/files, and batch enqueues them.
"""
import re
import os
import requests
import threading
from urllib.parse import urljoin, urlparse
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox, QGroupBox, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt

MEDIA_EXTS = {
    "video": [".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv", ".ts", ".m4v"],
    "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".opus"],
    "archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".iso"],
    "documents": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"],
    "images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"]
}

class GrabberDialog(QDialog):
    crawl_finished = pyqtSignal(list)
    crawl_failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Site Grabber & Media Sniffer")
        self.resize(720, 520)
        self.discovered_items = []

        self.crawl_finished.connect(self._on_crawl_success)
        self.crawl_failed.connect(self._on_crawl_error)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # URL Input
        grp_url = QGroupBox("Target Web Page Address")
        url_layout = QHBoxLayout(grp_url)
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("https://example.com/gallery-or-page")
        self.btn_crawl = QPushButton("Explore Webpage")
        self.btn_crawl.clicked.connect(self._start_crawl)
        url_layout.addWidget(self.txt_url)
        url_layout.addWidget(self.btn_crawl)
        layout.addWidget(grp_url)

        # Filters
        grp_filters = QGroupBox("Media Filters")
        f_layout = QHBoxLayout(grp_filters)
        self.chk_vid = QCheckBox("Videos")
        self.chk_vid.setChecked(True)
        self.chk_aud = QCheckBox("Audio")
        self.chk_aud.setChecked(True)
        self.chk_doc = QCheckBox("Documents")
        self.chk_doc.setChecked(True)
        self.chk_arc = QCheckBox("Archives")
        self.chk_arc.setChecked(True)
        self.chk_img = QCheckBox("Images")

        f_layout.addWidget(self.chk_vid)
        f_layout.addWidget(self.chk_aud)
        f_layout.addWidget(self.chk_doc)
        f_layout.addWidget(self.chk_arc)
        f_layout.addWidget(self.chk_img)
        f_layout.addStretch()
        layout.addWidget(grp_filters)

        # Discovered Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Select", "File Name", "Type", "Direct URL"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 240)
        self.table.setColumnWidth(2, 80)
        layout.addWidget(self.table)

        # Selection & Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.setObjectName("secondaryBtn")
        self.btn_select_all.clicked.connect(lambda: self._set_all_checks(True))

        self.btn_unselect = QPushButton("Unselect All")
        self.btn_unselect.setObjectName("secondaryBtn")
        self.btn_unselect.clicked.connect(lambda: self._set_all_checks(False))

        self.btn_download = QPushButton("Download Selected Files")
        self.btn_download.clicked.connect(self._accept_selection)

        btn_layout.addWidget(self.btn_select_all)
        btn_layout.addWidget(self.btn_unselect)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_download)
        layout.addLayout(btn_layout)

        self.selected_urls = []

    def _start_crawl(self):
        page_url = self.txt_url.text().strip()
        if not page_url:
            return
        self.btn_crawl.setEnabled(False)
        self.table.setRowCount(0)

        # Determine target extensions
        target_exts = set()
        if self.chk_vid.isChecked(): target_exts.update(MEDIA_EXTS["video"])
        if self.chk_aud.isChecked(): target_exts.update(MEDIA_EXTS["audio"])
        if self.chk_doc.isChecked(): target_exts.update(MEDIA_EXTS["documents"])
        if self.chk_arc.isChecked(): target_exts.update(MEDIA_EXTS["archives"])
        if self.chk_img.isChecked(): target_exts.update(MEDIA_EXTS["images"])

        def worker():
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                resp = requests.get(page_url, headers=headers, timeout=12)
                html = resp.text

                # Find all href and src
                raw_links = re.findall(r'(?:href|src)=["\']([^"\']+)["\']', html, re.IGNORECASE)
                items = []
                seen = set()

                for link in raw_links:
                    full_url = urljoin(page_url, link)
                    path = urlparse(full_url).path
                    ext = os.path.splitext(path)[1].lower()

                    if ext in target_exts and full_url not in seen:
                        seen.add(full_url)
                        fn = os.path.basename(path)
                        items.append({"filename": fn, "url": full_url, "type": ext.lstrip(".").upper()})

                self.crawl_finished.emit(items)
            except Exception as e:
                self.crawl_failed.emit(str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_crawl_success(self, items):
        self.btn_crawl.setEnabled(True)
        self.discovered_items = items
        self.table.setRowCount(len(items))

        for row, item in enumerate(items):
            chk = QCheckBox()
            chk.setChecked(True)
            self.table.setCellWidget(row, 0, chk)
            self.table.setItem(row, 1, QTableWidgetItem(item["filename"]))
            self.table.setItem(row, 2, QTableWidgetItem(item["type"]))
            self.table.setItem(row, 3, QTableWidgetItem(item["url"]))

        if not items:
            QMessageBox.information(self, "No Media Found", "No downloadable media matching selected filters was found on this page.")

    def _on_crawl_error(self, err):
        self.btn_crawl.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Could not crawl webpage: {err}")

    def _set_all_checks(self, checked: bool):
        for row in range(self.table.rowCount()):
            chk = self.table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox):
                chk.setChecked(checked)

    def _accept_selection(self):
        urls = []
        for row in range(self.table.rowCount()):
            chk = self.table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox) and chk.isChecked():
                url_item = self.table.item(row, 3)
                if url_item:
                    urls.append(url_item.text())

        if not urls:
            QMessageBox.warning(self, "No Selection", "Please check at least one file to download.")
            return

        self.selected_urls = urls
        self.accept()
