"""
Compact IDM-Grade Download Transfer Status Dialog.
Features real-time progress syncing, multi-connection segment visualizer,
background tray minimize, and direct file/folder launching.
"""
import os
import subprocess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QGroupBox, QGridLayout, QScrollArea, QWidget, QFrame, QMessageBox
)
from PyQt6.QtGui import QIcon, QFont, QPixmap
from PyQt6.QtCore import Qt, QTimer
from core.segment import DownloadTask
from .styles import format_bytes, format_speed, format_eta

RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources"))

class SegmentBar(QWidget):
    def __init__(self, segment_index: int, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)
        
        self.seg_idx = segment_index
        self.label = QLabel(f"Part {segment_index + 1}:")
        self.label.setFixedWidth(115)
        self.label.setStyleSheet("color: #475569; font-size: 11px; font-weight: 500;")
        
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(12)
        self.pbar.setTextVisible(True)
        self.pbar.setStyleSheet("""
            QProgressBar {
                background-color: #e2e8f0;
                border: none;
                border-radius: 4px;
                text-align: center;
                font-size: 10px;
                color: #0f172a;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 4px;
            }
        """)
        
        layout.addWidget(self.label)
        layout.addWidget(self.pbar)

    def update_progress(self, downloaded: int, total: int, adapter_name: str = None):
        if adapter_name:
            self.label.setText(f"Part {self.seg_idx + 1} [{adapter_name}]:")
        if total > 0:
            pct = int((downloaded / total) * 100)
            self.pbar.setValue(min(100, max(0, pct)))
            self.pbar.setFormat(f"{pct}% ({format_bytes(downloaded)})")
        else:
            self.pbar.setValue(100 if downloaded > 0 else 0)

class DownloadDialog(QDialog):
    def __init__(self, task: DownloadTask, parent=None, engine=None):
        super().__init__(parent)
        self.task = task
        self.engine = engine or (parent.engine if parent and hasattr(parent, 'engine') else None)
        self.segment_bars = []
        
        filename = os.path.basename(task.save_path)
        self.setWindowTitle(f"Downloading - {filename}")
        self.resize(520, 390)
        self.setMinimumSize(500, 360)
        
        icon_path = os.path.join(RESOURCES_DIR, "logo.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.setStyleSheet("""
            QDialog {
                background-color: #f8fafc;
                color: #0f172a;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QFrame#card {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                color: #1e293b;
                font-size: 12px;
            }
            QProgressBar#mainProgress {
                background-color: #e2e8f0;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                text-align: center;
                font-weight: bold;
                font-size: 11px;
                color: #0f172a;
                height: 18px;
            }
            QProgressBar#mainProgress::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
                border-radius: 5px;
            }
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton#secondaryBtn {
                background-color: #e2e8f0;
                color: #334155;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #cbd5e1;
            }
            QPushButton:disabled {
                background-color: #f1f5f9;
                color: #94a3b8;
            }
            QScrollArea {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #ffffff;
            }
            QScrollBar:vertical {
                background: #f1f5f9;
                width: 6px;
                border-radius: 3px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #10b981;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self._init_ui()
        
        # Periodic UI sync timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_ui)
        self.timer.start(200)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(14, 14, 14, 14)

        # File Header Info Card
        card_file = QFrame(self)
        card_file.setObjectName("card")
        f_layout = QVBoxLayout(card_file)
        f_layout.setContentsMargins(10, 8, 10, 8)
        f_layout.setSpacing(4)

        top_row = QHBoxLayout()
        self.lbl_filename = QLabel(f"<b>{os.path.basename(self.task.save_path)}</b>")
        self.lbl_filename.setStyleSheet("font-size: 13px; color: #0f172a;")
        self.lbl_status_badge = QLabel(f"  {self.task.status.upper()}  ")
        self.lbl_status_badge.setStyleSheet("background-color: #d1fae5; color: #065f46; font-weight: bold; border-radius: 4px; padding: 2px 6px; font-size: 11px;")
        top_row.addWidget(self.lbl_filename)
        top_row.addStretch()
        top_row.addWidget(self.lbl_status_badge)
        f_layout.addLayout(top_row)

        dir_name = os.path.dirname(self.task.save_path)
        dir_display = dir_name if len(dir_name) <= 55 else (dir_name[:52] + "...")
        lbl_dir = QLabel(f"📁 Save to: <span style='color:#64748b;'>{dir_display}</span>")
        lbl_dir.setStyleSheet("font-size: 11px;")
        f_layout.addWidget(lbl_dir)
        main_layout.addWidget(card_file)

        # Progress Card
        card_prog = QFrame(self)
        card_prog.setObjectName("card")
        p_layout = QVBoxLayout(card_prog)
        p_layout.setContentsMargins(10, 8, 10, 8)
        p_layout.setSpacing(6)

        self.overall_pbar = QProgressBar()
        self.overall_pbar.setObjectName("mainProgress")
        self.overall_pbar.setValue(0)
        p_layout.addWidget(self.overall_pbar)

        grid = QGridLayout()
        grid.setVerticalSpacing(4)
        grid.setHorizontalSpacing(10)

        self.lbl_size = QLabel("Downloaded: 0 B of 0 B")
        self.lbl_speed = QLabel("Speed: Calculating...")
        self.lbl_eta = QLabel("Time Left: --:--")
        res_str = "Yes (Multi-threaded)" if self.task.supports_range else "No (Single stream)"
        self.lbl_resume = QLabel(f"Resume: <b>{res_str}</b>")

        grid.addWidget(self.lbl_size, 0, 0)
        grid.addWidget(self.lbl_speed, 0, 1)
        grid.addWidget(self.lbl_eta, 1, 0)
        grid.addWidget(self.lbl_resume, 1, 1)
        p_layout.addLayout(grid)
        main_layout.addWidget(card_prog)

        # Multi-connection Segments Card
        card_segs = QFrame(self)
        card_segs.setObjectName("card")
        s_box = QVBoxLayout(card_segs)
        s_box.setContentsMargins(8, 6, 8, 6)
        s_box.setSpacing(4)

        conns_label = QLabel(f"<b>Connection Segments ({len(self.task.segments)} active threads):</b>")
        conns_label.setStyleSheet("font-size: 11px; color: #475569;")
        s_box.addWidget(conns_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(100)
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background-color: #ffffff;")
        self.seg_container = QVBoxLayout(scroll_widget)
        self.seg_container.setSpacing(2)
        self.seg_container.setContentsMargins(4, 4, 4, 4)
        
        for seg in self.task.segments:
            bar = SegmentBar(seg.index)
            self.segment_bars.append(bar)
            self.seg_container.addWidget(bar)
            
        scroll.setWidget(scroll_widget)
        s_box.addWidget(scroll)
        main_layout.addWidget(card_segs)

        # Bottom Control Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_pause = QPushButton("⏸️ Pause")
        self.btn_pause.clicked.connect(self.toggle_pause)
        btn_layout.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹️ Stop")
        self.btn_stop.setObjectName("secondaryBtn")
        self.btn_stop.clicked.connect(self.stop_download)
        btn_layout.addWidget(self.btn_stop)

        self.btn_delete = QPushButton("❌ Delete")
        self.btn_delete.setObjectName("secondaryBtn")
        self.btn_delete.setStyleSheet("QPushButton#secondaryBtn:hover { background-color: #ef4444; color: white; border-color: #ef4444; }")
        self.btn_delete.clicked.connect(self.delete_download)
        btn_layout.addWidget(self.btn_delete)

        self.btn_minimize = QPushButton("⬇️ To Tray")
        self.btn_minimize.setObjectName("secondaryBtn")
        self.btn_minimize.setToolTip("Minimize to background system tray while maintaining ultra-speed acceleration")
        self.btn_minimize.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_minimize)

        self.btn_refresh = QPushButton("🔄 Refresh Address")
        self.btn_refresh.setObjectName("secondaryBtn")
        self.btn_refresh.setToolTip("Update expired download URL without losing progress")
        self.btn_refresh.clicked.connect(self._on_refresh_clicked)
        self.btn_refresh.setVisible(False)
        btn_layout.addWidget(self.btn_refresh)

        btn_layout.addStretch()

        self.btn_open_file = QPushButton("📄 Open")
        self.btn_open_file.setEnabled(False)
        self.btn_open_file.clicked.connect(self.open_file)
        btn_layout.addWidget(self.btn_open_file)

        self.btn_open_folder = QPushButton("📁 Folder")
        self.btn_open_folder.setObjectName("secondaryBtn")
        self.btn_open_folder.setEnabled(False)
        self.btn_open_folder.clicked.connect(self.open_folder)
        btn_layout.addWidget(self.btn_open_folder)
        
        main_layout.addLayout(btn_layout)

    def refresh_ui(self):
        total = self.task.total_bytes
        down = self.task.downloaded_bytes
        
        if total > 0:
            pct = int((down / total) * 100)
            self.overall_pbar.setValue(min(100, max(0, pct)))
            self.overall_pbar.setFormat(f"{pct}% ({format_bytes(down)} / {format_bytes(total)})")
            rem = max(0, total - down)
            self.lbl_eta.setText(f"Time Left: <b>{format_eta(rem, self.task.speed)}</b>")
            self.lbl_size.setText(f"Downloaded: <b>{format_bytes(down)}</b> of <b>{format_bytes(total)}</b>")
        else:
            self.overall_pbar.setRange(0, 0)
            self.lbl_size.setText(f"Downloaded: <b>{format_bytes(down)}</b>")

        speed_text = format_speed(self.task.speed) if self.task.speed > 0 else "Establishing connections..."
        self.lbl_speed.setText(f"Speed: <b>{speed_text}</b>")
        
        # Status Badge
        st = self.task.status.capitalize()
        self.lbl_status_badge.setText(f"  {st.upper()}  ")
        if self.task.status == "downloading":
            self.lbl_status_badge.setStyleSheet("background-color: #d1fae5; color: #065f46; font-weight: bold; border-radius: 4px; padding: 2px 6px; font-size: 11px;")
        elif self.task.status == "paused":
            self.lbl_status_badge.setStyleSheet("background-color: #fef3c7; color: #92400e; font-weight: bold; border-radius: 4px; padding: 2px 6px; font-size: 11px;")
        elif self.task.status == "completed":
            self.lbl_status_badge.setStyleSheet("background-color: #ecfdf5; color: #047857; font-weight: bold; border-radius: 4px; padding: 2px 6px; font-size: 11px;")
        elif self.task.status == "error":
            self.lbl_status_badge.setStyleSheet("background-color: #fee2e2; color: #991b1b; font-weight: bold; border-radius: 4px; padding: 2px 6px; font-size: 11px;")

        # Update Connection Segments
        for i, bar in enumerate(self.segment_bars):
            if i < len(self.task.segments):
                seg = self.task.segments[i]
                bar.update_progress(seg.downloaded, seg.total_size, seg.assigned_adapter)

        # Buttons state
        if self.task.status == "completed":
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)
            self.btn_refresh.setVisible(False)
            self.btn_open_file.setEnabled(True)
            self.btn_open_folder.setEnabled(True)
        elif self.task.status == "paused":
            self.btn_pause.setText("▶️ Resume")
            self.btn_pause.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.btn_refresh.setVisible(False)
        elif self.task.status == "downloading":
            self.btn_pause.setText("⏸️ Pause")
            self.btn_pause.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.btn_refresh.setVisible(False)
        elif self.task.status in ("error", "cancelled"):
            self.btn_pause.setText("▶️ Resume")
            self.btn_pause.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.btn_refresh.setVisible(True)

    def _on_refresh_clicked(self):
        p = self.parent()
        if p and hasattr(p, "show_refresh_dialog"):
            p.show_refresh_dialog(self.task.task_id)
            self.close()

    def toggle_pause(self):
        if self.task.status == "downloading":
            if self.engine:
                self.engine.pause_download(self.task.task_id)
            else:
                self.task.pause()
        elif self.task.status in ("paused", "queued", "error", "cancelled"):
            if self.engine:
                self.engine.resume_download(self.task.task_id)
            else:
                self.task.start()
        self.refresh_ui()

    def stop_download(self):
        if self.engine:
            self.engine.pause_download(self.task.task_id)
        else:
            self.task.pause()
        self.refresh_ui()

    def delete_download(self):
        filename = os.path.basename(self.task.save_path)
        reply = QMessageBox.question(
            self,
            "Delete Download",
            f"Are you sure you want to stop and delete '{filename}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.engine:
                self.engine.delete_download(self.task.task_id, delete_file=True)
            else:
                self.task.cancel()
            self.close()

    def open_file(self):
        if os.path.exists(self.task.save_path):
            os.startfile(self.task.save_path)

    def open_folder(self):
        folder = os.path.dirname(self.task.save_path)
        if os.path.exists(folder):
            subprocess.run(f'explorer /select,"{self.task.save_path}"')
