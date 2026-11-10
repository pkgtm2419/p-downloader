"""
Torrent Details, 2D Piece Map Grid, and Peer Visualization Dialog for P-Downloader.
"""
import math
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel,
    QProgressBar, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox, QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont

from .styles import format_bytes, COLOR_PRIMARY, COLOR_SUCCESS


class PieceMapWidget(QWidget):
    """
    Renders an interactive 2D grid of BitTorrent pieces with live status:
    - Gray: Unrequested / Missing
    - Blue: Currently Downloading
    - Green: Verified Completed
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(140)
        self.pieces: List[int] = []

    def set_pieces(self, pieces: List[int]):
        self.pieces = pieces
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        w = self.width()
        h = self.height()

        total = len(self.pieces)
        if total == 0:
            painter.setPen(QColor("#888888"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No piece information available.")
            return

        cols = max(10, int(math.sqrt(total * (w / max(1, h)))))
        rows = math.ceil(total / cols)

        cell_w = max(2, w / cols)
        cell_h = max(2, h / rows)

        color_missing = QColor("#2a2d32")
        color_active = QColor("#0078d4")
        color_done = QColor("#107c41")

        for i, status in enumerate(self.pieces):
            r = i // cols
            c = i % cols
            x = int(c * cell_w)
            y = int(r * cell_h)

            if status == 2:
                col = color_done
            elif status == 1:
                col = color_active
            else:
                col = color_missing

            painter.fillRect(x, y, max(1, int(cell_w) - 1), max(1, int(cell_h) - 1), col)


class TorrentDetailsDialog(QDialog):
    """
    Detailed inspection dialog for active BitTorrent transfers.
    Displays live 2D piece map, peer connections, and file priorities.
    """
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle(f"Torrent Details — {getattr(task, 'name', 'Torrent')}")
        self.resize(650, 480)

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Tab 1: General & Status
        tab_gen = QWidget()
        v_gen = QVBoxLayout(tab_gen)

        grp_stats = QGroupBox("Transfer Statistics")
        grid = QGridLayout(grp_stats)

        self.lbl_status = QLabel(f"<b>Status:</b> {task.status}")
        self.lbl_downloaded = QLabel(f"<b>Downloaded:</b> {format_bytes(task.downloaded_bytes)} of {format_bytes(task.total_bytes)}")
        self.lbl_speed = QLabel(f"<b>DL Speed:</b> {format_bytes(task.speed)}/s")
        self.lbl_up_speed = QLabel(f"<b>UL Speed:</b> {format_bytes(getattr(task, 'upload_speed', 0))}/s")
        self.lbl_peers = QLabel(f"<b>Peers:</b> {getattr(task, 'peers_count', 0)} ({getattr(task, 'seeds_count', 0)} seeds)")
        self.lbl_pieces = QLabel(f"<b>Pieces:</b> {getattr(task, 'pieces_count', 0)}")

        grid.addWidget(self.lbl_status, 0, 0)
        grid.addWidget(self.lbl_downloaded, 0, 1)
        grid.addWidget(self.lbl_speed, 1, 0)
        grid.addWidget(self.lbl_up_speed, 1, 1)
        grid.addWidget(self.lbl_peers, 2, 0)
        grid.addWidget(self.lbl_pieces, 2, 1)

        v_gen.addWidget(grp_stats)

        self.chk_sequential = QCheckBox("Sequential Download (Prioritize head/tail pieces for media playback)")
        self.chk_sequential.setChecked(getattr(task, "sequential", False))
        self.chk_sequential.toggled.connect(self._toggle_sequential)
        v_gen.addWidget(self.chk_sequential)
        v_gen.addStretch()

        tabs.addTab(tab_gen, "General")

        # Tab 2: 2D Piece Map
        tab_pieces = QWidget()
        v_pieces = QVBoxLayout(tab_pieces)
        v_pieces.addWidget(QLabel("<b>BitTorrent Piece Map Grid</b> (Green: Complete, Blue: Active, Gray: Pending)"))
        self.piece_widget = PieceMapWidget()
        v_pieces.addWidget(self.piece_widget)

        tabs.addTab(tab_pieces, "Piece Map")

        # Tab 3: Files List
        tab_files = QWidget()
        v_files = QVBoxLayout(tab_files)
        self.tbl_files = QTableWidget(0, 3)
        self.tbl_files.setHorizontalHeaderLabels(["Filename", "Size", "Priority"])
        self.tbl_files.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        v_files.addWidget(self.tbl_files)
        self._populate_files()

        tabs.addTab(tab_files, "Files")

        # Button row
        btn_box = QHBoxLayout()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        btn_box.addStretch()
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

        # Live poll timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_stats)
        self.timer.start(500)
        self._refresh_stats()

    def _toggle_sequential(self, checked: bool):
        if hasattr(self.task, "set_sequential"):
            self.task.set_sequential(checked)

    def _populate_files(self):
        files = getattr(self.task, "files_list", [])
        self.tbl_files.setRowCount(len(files))
        for r, f in enumerate(files):
            self.tbl_files.setItem(r, 0, QTableWidgetItem(f.get("path", "file")))
            self.tbl_files.setItem(r, 1, QTableWidgetItem(format_bytes(f.get("length", 0))))
            self.tbl_files.setItem(r, 2, QTableWidgetItem("Normal"))

    def _refresh_stats(self):
        self.lbl_status.setText(f"<b>Status:</b> {self.task.status}")
        self.lbl_downloaded.setText(f"<b>Downloaded:</b> {format_bytes(self.task.downloaded_bytes)} of {format_bytes(self.task.total_bytes)}")
        self.lbl_speed.setText(f"<b>DL Speed:</b> {format_bytes(self.task.speed)}/s")
        self.lbl_up_speed.setText(f"<b>UL Speed:</b> {format_bytes(getattr(self.task, 'upload_speed', 0))}/s")
        self.lbl_peers.setText(f"<b>Peers:</b> {getattr(self.task, 'peers_count', 0)} ({getattr(self.task, 'seeds_count', 0)} seeds)")
        self.lbl_pieces.setText(f"<b>Pieces:</b> {getattr(self.task, 'pieces_count', 0)}")

        piece_map = getattr(self.task, "piece_map", [])
        self.piece_widget.set_pieces(piece_map)
