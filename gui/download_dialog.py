"""
Detailed Download Transfer Status Dialog with Dynamic Multi-Segment Visualizer.
"""
import os
import subprocess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QGroupBox, QGridLayout, QScrollArea, QWidget
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QTimer
from core.segment import DownloadTask
from .styles import format_bytes, format_speed, format_eta

class SegmentBar(QWidget):
    def __init__(self, segment_index: int, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        
        self.label = QLabel(f"Part {segment_index + 1}:")
        self.label.setFixedWidth(55)
        self.label.setStyleSheet("color: #666; font-size: 11px;")
        
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(12)
        self.pbar.setTextVisible(True)
        
        layout.addWidget(self.label)
        layout.addWidget(self.pbar)

    def update_progress(self, downloaded: int, total: int):
        if total > 0:
            pct = int((downloaded / total) * 100)
            self.pbar.setValue(min(100, max(0, pct)))
            self.pbar.setFormat(f"{pct}% ({format_bytes(downloaded)})")
        else:
            self.pbar.setValue(100 if downloaded > 0 else 0)

class DownloadDialog(QDialog):
    def __init__(self, task: DownloadTask, parent=None):
        super().__init__(parent)
        self.task = task
        self.segment_bars = []
        
        self.setWindowTitle(f"Downloading - {os.path.basename(task.save_path)}")
        self.resize(520, 420)
        
        icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "logo.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self._init_ui()
        
        # Periodic update timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_ui)
        self.timer.start(250)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # File Info Group
        info_group = QGroupBox("File Information")
        info_layout = QGridLayout(info_group)
        info_layout.setVerticalSpacing(6)
        
        info_layout.addWidget(QLabel("<b>File Name:</b>"), 0, 0)
        self.lbl_filename = QLabel(os.path.basename(self.task.save_path))
        info_layout.addWidget(self.lbl_filename, 0, 1)

        info_layout.addWidget(QLabel("<b>Save To:</b>"), 1, 0)
        self.lbl_path = QLabel(self.task.save_path)
        self.lbl_path.setWordWrap(True)
        info_layout.addWidget(self.lbl_path, 1, 1)

        info_layout.addWidget(QLabel("<b>Resume Capability:</b>"), 2, 0)
        res_text = "Yes (Multi-threaded Range Supported)" if self.task.supports_range else "No (Single stream)"
        info_layout.addWidget(QLabel(f"<span style='color: {'#2e7d32' if self.task.supports_range else '#c62828'}; font-weight:bold;'>{res_text}</span>"), 2, 1)

        main_layout.addWidget(info_group)

        # Overall Progress Group
        prog_group = QGroupBox("Download Progress")
        prog_layout = QGridLayout(prog_group)
        
        self.lbl_status = QLabel(f"<b>Status:</b> {self.task.status.capitalize()}")
        prog_layout.addWidget(self.lbl_status, 0, 0, 1, 2)

        self.overall_pbar = QProgressBar()
        self.overall_pbar.setFixedHeight(22)
        prog_layout.addWidget(self.overall_pbar, 1, 0, 1, 2)

        self.lbl_size = QLabel("Downloaded: 0 B / 0 B")
        prog_layout.addWidget(self.lbl_size, 2, 0)

        self.lbl_speed = QLabel("Speed: 0 B/s")
        prog_layout.addWidget(self.lbl_speed, 2, 1, Qt.AlignmentFlag.AlignRight)

        self.lbl_eta = QLabel("Time Left: --:--:--")
        prog_layout.addWidget(self.lbl_eta, 3, 0)

        main_layout.addWidget(prog_group)

        # Dynamic Connection Segments
        seg_group = QGroupBox("Connection Segments (Multi-threading)")
        seg_layout = QVBoxLayout(seg_group)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(110)
        scroll_widget = QWidget()
        self.seg_container = QVBoxLayout(scroll_widget)
        self.seg_container.setSpacing(2)
        self.seg_container.setContentsMargins(4, 4, 4, 4)
        
        for seg in self.task.segments:
            bar = SegmentBar(seg.index)
            self.segment_bars.append(bar)
            self.seg_container.addWidget(bar)
            
        scroll.setWidget(scroll_widget)
        seg_layout.addWidget(scroll)
        main_layout.addWidget(seg_group)

        # Control Buttons
        btn_layout = QHBoxLayout()
        self.btn_pause = QPushButton("Pause")
        self.btn_pause.clicked.connect(self.toggle_pause)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("secondaryBtn")
        self.btn_cancel.clicked.connect(self.cancel_download)

        self.btn_open_folder = QPushButton("Open Folder")
        self.btn_open_folder.setObjectName("secondaryBtn")
        self.btn_open_folder.clicked.connect(self.open_folder)
        self.btn_open_folder.setEnabled(False)

        btn_layout.addWidget(self.btn_pause)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_open_folder)
        
        main_layout.addLayout(btn_layout)

    def refresh_ui(self):
        # Update Overall Progress
        total = self.task.total_bytes
        down = self.task.downloaded_bytes
        
        if total > 0:
            pct = int((down / total) * 100)
            self.overall_pbar.setValue(min(100, max(0, pct)))
            self.overall_pbar.setFormat(f"{pct}%")
            rem = total - down
            self.lbl_eta.setText(f"Time Left: {format_eta(rem, self.task.speed)}")
            self.lbl_size.setText(f"Downloaded: {format_bytes(down)} of {format_bytes(total)}")
        else:
            self.overall_pbar.setRange(0, 0)  # indeterminate
            self.lbl_size.setText(f"Downloaded: {format_bytes(down)}")

        self.lbl_speed.setText(f"Speed: {format_speed(self.task.speed)}")
        self.lbl_status.setText(f"<b>Status:</b> {self.task.status.capitalize()}")

        # Update Segments
        for i, bar in enumerate(self.segment_bars):
            if i < len(self.task.segments):
                seg = self.task.segments[i]
                bar.update_progress(seg.downloaded, seg.total_size)

        # Buttons state
        if self.task.status == "completed":
            self.btn_pause.setEnabled(False)
            self.btn_open_folder.setEnabled(True)
            self.lbl_status.setText("<b style='color:#2e7d32;'>Status: Download Finished!</b>")
        elif self.task.status == "paused":
            self.btn_pause.setText("Resume")
        elif self.task.status == "downloading":
            self.btn_pause.setText("Pause")
        elif self.task.status == "error":
            self.lbl_status.setText(f"<b style='color:#c62828;'>Error: {self.task.error_message}</b>")

    def toggle_pause(self):
        if self.task.status == "downloading":
            self.task.pause()
        elif self.task.status == "paused":
            self.task.start()
        self.refresh_ui()

    def cancel_download(self):
        self.task.cancel()
        self.close()

    def open_folder(self):
        folder = os.path.dirname(self.task.save_path)
        if os.path.exists(folder):
            subprocess.run(f'explorer /select,"{self.task.save_path}"')
