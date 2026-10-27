"""
Comprehensive Modern IDM-Grade Main Dashboard Window for P-Downloader.
Fixes all layout bugs, dark-mode styling issues, and integrates all IDM features.
"""
import os
import sys
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView, QToolBar, QMenuBar, QMenu, QStatusBar,
    QProgressBar, QMessageBox, QApplication, QSystemTrayIcon,
    QLabel, QPushButton, QFileDialog
)
from PyQt6.QtGui import QAction, QIcon, QCursor, QColor, QFont, QPixmap
from PyQt6.QtCore import Qt, QTimer

from core import __version__
from core.engine import DownloadEngine
from core.segment import DownloadTask
from core.network_binder import NetworkManager
from .styles import MAIN_STYLESHEET, format_bytes, format_speed, format_eta
from .add_dialog import AddDownloadDialog
from .download_dialog import DownloadDialog
from .settings_dialog import SettingsDialog
from .batch_dialog import BatchDownloadDialog
from .scheduler_dialog import SchedulerDialog
from .grabber_dialog import GrabberDialog
from .refresh_dialog import RefreshDownloadDialog
from .site_logins_dialog import SiteLoginsDialog
from .icons import get_sidebar_icon
import winsound

RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources"))

class MainWindow(QMainWindow):
    def __init__(self, engine: DownloadEngine):
        super().__init__()
        self.engine = engine
        self.active_dialogs = {}
        self.last_clipboard_text = ""

        self.setWindowTitle(f"P-Downloader - Pure Download Accelerator (v{__version__})")
        self.resize(1150, 680)
        self.setStyleSheet(MAIN_STYLESHEET)

        # Set Window and App Icon
        icon_path = os.path.join(RESOURCES_DIR, "logo.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(RESOURCES_DIR, "logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._init_menu_and_toolbar()
        self._init_ui()
        self._init_tray()

        self.engine.add_listener(self._on_engine_update)

        # Periodic table refresh timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_table)
        self.refresh_timer.start(500)

        # Clipboard auto-monitor timer
        self.clip_timer = QTimer(self)
        self.clip_timer.timeout.connect(self._check_clipboard_link)
        self.clip_timer.start(1000)

        # Background Scheduler & Queue Automation Daemon (IDM Feature)
        from core.scheduler_service import SchedulerService
        self.scheduler = SchedulerService(self.engine, on_exit_requested=self.close)
        self.scheduler.start()

        self._load_table_data()

    def closeEvent(self, event):
        if not getattr(self, "_force_quit", False):
            event.ignore()
            self.hide()
            if hasattr(self, "tray") and self.tray.isVisible():
                if not getattr(self, "_tray_notified", False):
                    self._tray_notified = True
                    self.tray.showMessage(
                        "P-Downloader",
                        "Application minimized to tray. Click the tray icon to restore.",
                        QSystemTrayIcon.MessageIcon.Information,
                        2000
                    )
            return

        if hasattr(self, "scheduler"):
            self.scheduler.stop()
        event.accept()

    def _exit_app(self):
        self._force_quit = True
        if hasattr(self, "scheduler"):
            self.scheduler.stop()
        QApplication.instance().quit()

    def _init_menu_and_toolbar(self):
        menubar = self.menuBar()

        # ================= Tasks Menu =================
        menu_tasks = menubar.addMenu("&Tasks")
        
        act_add = QAction("➕ &Add New Download...", self)
        act_add.setShortcut("Ctrl+N")
        act_add.triggered.connect(self.show_add_dialog)
        menu_tasks.addAction(act_add)

        act_batch = QAction("📋 Add &Batch Downloads...", self)
        act_batch.setShortcut("Ctrl+B")
        act_batch.triggered.connect(self.show_batch_dialog)
        menu_tasks.addAction(act_batch)

        act_grabber = QAction("🕸️ &Site Grabber...", self)
        act_grabber.triggered.connect(self.show_grabber_dialog)
        menu_tasks.addAction(act_grabber)

        menu_tasks.addSeparator()

        act_resume_all = QAction("▶️ &Resume All", self)
        act_resume_all.triggered.connect(self.engine.resume_all)
        menu_tasks.addAction(act_resume_all)

        act_pause_all = QAction("⏸️ &Pause All", self)
        act_pause_all.triggered.connect(self.engine.pause_all)
        menu_tasks.addAction(act_pause_all)

        act_stop_all = QAction("⏹️ &Stop All", self)
        act_stop_all.triggered.connect(self.engine.pause_all)
        menu_tasks.addAction(act_stop_all)

        menu_tasks.addSeparator()

        act_exit = QAction("E&xit", self)
        act_exit.setShortcut("Alt+F4")
        act_exit.triggered.connect(self._exit_app)
        menu_tasks.addAction(act_exit)

        # ================= File Menu =================
        menu_file = menubar.addMenu("&File")

        act_open_dir = QAction("📁 Open Default Downloads Folder", self)
        act_open_dir.triggered.connect(self._open_default_folder)
        menu_file.addAction(act_open_dir)

        act_clear_done = QAction("🧹 Clear Completed from List", self)
        act_clear_done.triggered.connect(self._clear_completed)
        menu_file.addAction(act_clear_done)

        menu_file.addSeparator()

        act_export = QAction("📤 Export Download List to Text...", self)
        act_export.triggered.connect(self._export_list)
        menu_file.addAction(act_export)

        # ================= Downloads Menu =================
        menu_downloads = menubar.addMenu("&Downloads")

        act_res_sel = QAction("▶️ Resume", self)
        act_res_sel.setShortcut("Ctrl+R")
        act_res_sel.triggered.connect(self._resume_selected)
        menu_downloads.addAction(act_res_sel)

        act_pause_sel = QAction("⏸️ Pause", self)
        act_pause_sel.triggered.connect(self._pause_selected)
        menu_downloads.addAction(act_pause_sel)

        act_del_sel = QAction("❌ Delete", self)
        act_del_sel.setShortcut("Del")
        act_del_sel.triggered.connect(self._delete_selected)
        menu_downloads.addAction(act_del_sel)

        menu_downloads.addSeparator()

        act_refresh_addr = QAction("🔄 &Refresh Download Address...", self)
        act_refresh_addr.setShortcut("Ctrl+U")
        act_refresh_addr.triggered.connect(self._refresh_selected_address)
        menu_downloads.addAction(act_refresh_addr)

        menu_downloads.addSeparator()

        self.act_speed_limit = QAction("⚡ Speed Limiter: Off", self)
        self.act_speed_limit.triggered.connect(self._toggle_speed_limiter)
        menu_downloads.addAction(self.act_speed_limit)

        # ================= Options Menu =================
        menu_options = menubar.addMenu("&Options")

        act_scheduler = QAction("⏰ &Scheduler & Queues...", self)
        act_scheduler.setShortcut("Ctrl+S")
        act_scheduler.triggered.connect(self.show_scheduler_dialog)
        menu_options.addAction(act_scheduler)

        act_site_logins = QAction("🔑 &Site Logins & Passwords...", self)
        act_site_logins.triggered.connect(self.show_site_logins_dialog)
        menu_options.addAction(act_site_logins)

        act_settings = QAction("⚙️ &Preferences / Options...", self)
        act_settings.setShortcut("Ctrl+O")
        act_settings.triggered.connect(self.show_settings_dialog)
        menu_options.addAction(act_settings)

        # ================= View Menu =================
        menu_view = menubar.addMenu("&View")
        act_refresh_view = QAction("🔄 &Refresh List", self)
        act_refresh_view.setShortcut("F5")
        act_refresh_view.triggered.connect(self._load_table_data)
        menu_view.addAction(act_refresh_view)

        # ================= Help Menu =================
        menu_help = menubar.addMenu("&Help")

        act_about = QAction("ℹ️ &About P-Downloader", self)
        act_about.triggered.connect(self._show_about)
        menu_help.addAction(act_about)

        # ================= Top Ribbon ToolBar =================
        toolbar = QToolBar("Main Controls", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        btn_add = toolbar.addAction("➕ Add URL")
        btn_add.setToolTip("Add new download URL (Ctrl+N)")
        btn_add.triggered.connect(self.show_add_dialog)

        btn_batch = toolbar.addAction("📋 Batch Add")
        btn_batch.setToolTip("Add multiple URLs simultaneously (Ctrl+B)")
        btn_batch.triggered.connect(self.show_batch_dialog)

        toolbar.addSeparator()

        btn_resume = toolbar.addAction("▶️ Resume")
        btn_resume.setToolTip("Resume selected download")
        btn_resume.triggered.connect(self._resume_selected)

        btn_pause = toolbar.addAction("⏸️ Pause")
        btn_pause.setToolTip("Pause selected download")
        btn_pause.triggered.connect(self._pause_selected)

        btn_refresh = toolbar.addAction("🔄 Refresh Link")
        btn_refresh.setToolTip("Refresh expired download address without losing progress (IDM feature)")
        btn_refresh.triggered.connect(self._refresh_selected_address)

        btn_stop_all = toolbar.addAction("⏹️ Stop All")
        btn_stop_all.setToolTip("Stop all active downloads")
        btn_stop_all.triggered.connect(self.engine.pause_all)

        btn_delete = toolbar.addAction("❌ Delete")
        btn_delete.setToolTip("Remove selected download (Del)")
        btn_delete.triggered.connect(self._delete_selected)

        btn_clear = toolbar.addAction("🧹 Clear Done")
        btn_clear.setToolTip("Clear completed downloads from list")
        btn_clear.triggered.connect(self._clear_completed)

        toolbar.addSeparator()

        btn_sched = toolbar.addAction("⏰ Scheduler")
        btn_sched.setToolTip("Schedule timed downloads and queues")
        btn_sched.triggered.connect(self.show_scheduler_dialog)

        btn_grab = toolbar.addAction("🕸️ Grabber")
        btn_grab.setToolTip("Explore website to sniff media and files")
        btn_grab.triggered.connect(self.show_grabber_dialog)

        toolbar.addSeparator()

        btn_settings = toolbar.addAction("⚙️ Options")
        btn_settings.setToolTip("Configure application preferences")
        btn_settings.triggered.connect(self.show_settings_dialog)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # Horizontal Splitter (Sidebar + Downloads Table)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)

        # Left Sidebar (TreeWidget)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setMinimumWidth(215)
        self.tree.setIndentation(12)
        self.tree.setAnimated(True)

        header_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        header_color = QColor("#64748b")

        # Tree: Categories
        root_cat = QTreeWidgetItem(self.tree, ["CATEGORIES"])
        root_cat.setExpanded(True)
        root_cat.setFont(0, header_font)
        root_cat.setForeground(0, header_color)
        root_cat.setFlags(root_cat.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        self.item_all = QTreeWidgetItem(root_cat, ["All Downloads"])
        self.item_all.setIcon(0, get_sidebar_icon("all"))
        self.item_all.setData(0, Qt.ItemDataRole.UserRole, "all")

        self.item_comp = QTreeWidgetItem(root_cat, ["Compressed"])
        self.item_comp.setIcon(0, get_sidebar_icon("compressed"))
        self.item_comp.setData(0, Qt.ItemDataRole.UserRole, "compressed")

        self.item_doc = QTreeWidgetItem(root_cat, ["Documents"])
        self.item_doc.setIcon(0, get_sidebar_icon("documents"))
        self.item_doc.setData(0, Qt.ItemDataRole.UserRole, "documents")

        self.item_music = QTreeWidgetItem(root_cat, ["Music"])
        self.item_music.setIcon(0, get_sidebar_icon("music"))
        self.item_music.setData(0, Qt.ItemDataRole.UserRole, "music")

        self.item_prog = QTreeWidgetItem(root_cat, ["Programs"])
        self.item_prog.setIcon(0, get_sidebar_icon("programs"))
        self.item_prog.setData(0, Qt.ItemDataRole.UserRole, "programs")

        self.item_vid = QTreeWidgetItem(root_cat, ["Video"])
        self.item_vid.setIcon(0, get_sidebar_icon("video"))
        self.item_vid.setData(0, Qt.ItemDataRole.UserRole, "video")

        # Tree: Status
        root_status = QTreeWidgetItem(self.tree, ["STATUS"])
        root_status.setExpanded(True)
        root_status.setFont(0, header_font)
        root_status.setForeground(0, header_color)
        root_status.setFlags(root_status.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        self.item_downloading = QTreeWidgetItem(root_status, ["Downloading"])
        self.item_downloading.setIcon(0, get_sidebar_icon("downloading"))
        self.item_downloading.setData(0, Qt.ItemDataRole.UserRole, "downloading")

        self.item_finished = QTreeWidgetItem(root_status, ["Finished"])
        self.item_finished.setIcon(0, get_sidebar_icon("finished"))
        self.item_finished.setData(0, Qt.ItemDataRole.UserRole, "finished")

        self.item_paused = QTreeWidgetItem(root_status, ["Paused"])
        self.item_paused.setIcon(0, get_sidebar_icon("paused"))
        self.item_paused.setData(0, Qt.ItemDataRole.UserRole, "paused")

        self.item_error = QTreeWidgetItem(root_status, ["Error / Expired"])
        self.item_error.setIcon(0, get_sidebar_icon("error"))
        self.item_error.setData(0, Qt.ItemDataRole.UserRole, "error")

        # Tree: Queues
        root_queues = QTreeWidgetItem(self.tree, ["QUEUES"])
        root_queues.setExpanded(True)
        root_queues.setFont(0, header_font)
        root_queues.setForeground(0, header_color)
        root_queues.setFlags(root_queues.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        self.item_queue_main = QTreeWidgetItem(root_queues, ["Main Queue"])
        self.item_queue_main.setIcon(0, get_sidebar_icon("queue_main"))
        self.item_queue_main.setData(0, Qt.ItemDataRole.UserRole, "queue_main")

        self.item_queue_sync = QTreeWidgetItem(root_queues, ["Sync Queue"])
        self.item_queue_sync.setIcon(0, get_sidebar_icon("queue_sync"))
        self.item_queue_sync.setData(0, Qt.ItemDataRole.UserRole, "queue_sync")

        self.tree.setCurrentItem(self.item_all)
        self.tree.itemClicked.connect(self._on_tree_selected)

        splitter.addWidget(self.tree)

        # Right Main Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "File Name", "Size", "Status", "Progress", "Speed", "Time Left", "Category", "URL"
        ])
        
        # Table Styling & Formatting
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.verticalHeader().setVisible(False)  # Clean IDM table without row index numbers!
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._on_table_double_clicked)

        self.table.setColumnWidth(0, 260)
        self.table.setColumnWidth(1, 95)
        self.table.setColumnWidth(2, 95)
        self.table.setColumnWidth(3, 160)
        self.table.setColumnWidth(4, 95)
        self.table.setColumnWidth(5, 85)
        self.table.setColumnWidth(6, 95)

        splitter.addWidget(self.table)
        splitter.setSizes([230, 920])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        main_layout.addWidget(splitter)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.lbl_net_status = QLabel("🌐 Bonding: Active  ")
        self.lbl_net_status.setStyleSheet("color: #10b981; font-weight: bold;")
        self.status_bar.addPermanentWidget(self.lbl_net_status)

        self.lbl_speed_limiter_status = QLabel("⚡ Speed Limiter: OFF  ")
        self.lbl_speed_limiter_status.setStyleSheet("color: #64748b; font-weight: bold;")
        self.status_bar.addPermanentWidget(self.lbl_speed_limiter_status)
        self.status_bar.showMessage("Ready. P-Downloader is waiting for downloads.")

    def _init_tray(self):
        icon_path = os.path.join(RESOURCES_DIR, "logo.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(RESOURCES_DIR, "logo.png")
            
        self.tray = QSystemTrayIcon(self)
        if os.path.exists(icon_path):
            self.tray.setIcon(QIcon(icon_path))
        self.tray.setToolTip("P-Downloader - Pure Download Accelerator")

        tray_menu = QMenu()
        act_show = tray_menu.addAction("Show P-Downloader")
        act_show.triggered.connect(self.showNormal)

        act_add_t = tray_menu.addAction("Add Download...")
        act_add_t.triggered.connect(self.show_add_dialog)

        tray_menu.addSeparator()

        act_pause_all_t = tray_menu.addAction("Pause All Downloads")
        act_pause_all_t.triggered.connect(self.engine.pause_all)

        act_resume_all_t = tray_menu.addAction("Resume All Downloads")
        act_resume_all_t.triggered.connect(self.engine.resume_all)

        tray_menu.addSeparator()

        act_quit = tray_menu.addAction("Exit P-Downloader")
        act_quit.triggered.connect(self._exit_app)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            if self.isVisible() and not self.isMinimized():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()
                self.raise_()

    # ================= Dialog Invocations =================
    def show_add_dialog(
        self,
        initial_url: str = "",
        initial_filename: str = "",
        referer: str = "",
        headers: dict = None,
        start_now: bool = False,
        page_url: str = "",
        quality: str = ""
    ):
        # Check if URL is an HLS master playlist with selectable qualities
        if initial_url and ".m3u8" in initial_url.lower():
            try:
                import requests
                from core.hls_downloader import HLSParser
                from gui.video_quality_dialog import VideoQualityDialog
                req_hdrs = headers or {}
                if referer and "referer" not in [k.lower() for k in req_hdrs]:
                    req_hdrs["Referer"] = referer
                resp = requests.get(initial_url, headers=req_hdrs, timeout=5)
                if resp.status_code == 200 and HLSParser.is_master_playlist(resp.text):
                    variants = HLSParser.parse_master_playlist(resp.text, initial_url)
                    if variants:
                        default_dir = self.engine.db.get_setting("default_download_path", os.path.expanduser("~/Downloads"))
                        v_dlg = VideoQualityDialog(initial_filename or "HLS Stream Video", variants, default_dir, self)
                        if v_dlg.exec():
                            sel = v_dlg.selected_variant
                            task = self.engine.create_download(
                                url=sel["url"],
                                save_path=v_dlg.output_path,
                                auto_start=v_dlg.start_immediately
                            )
                            self._load_table_data()
                            if v_dlg.start_immediately and self.engine.db.get_setting("show_dlg", "1") == "1":
                                self.open_transfer_dialog(task)
                            return
            except Exception:
                pass

        if start_now and initial_url:
            fn = initial_filename or None
            task = self.engine.create_download(
                url=initial_url,
                filename=fn,
                auto_start=True,
                page_url=page_url,
                quality=quality
            )
            self._load_table_data()
            if self.engine.db.get_setting("show_dlg", "1") == "1":
                self.open_transfer_dialog(task)
            return

        dlg = AddDownloadDialog(
            self,
            initial_url=initial_url,
            initial_filename=initial_filename,
            page_url=page_url,
            quality=quality,
            headers=headers,
            referer=referer
        )
        if dlg.exec():
            res = dlg.get_result()
            task = self.engine.create_download(
                url=res["url"],
                filename=res["filename"],
                save_path=res["save_path"],
                category=res["category"],
                connections=res["connections"],
                auto_start=res["auto_start"],
                page_url=res.get("page_url"),
                quality=res.get("quality")
            )
            self._load_table_data()
            if res["auto_start"] and self.engine.db.get_setting("show_dlg", "1") == "1":
                self.open_transfer_dialog(task)

    def show_batch_dialog(self):
        dlg = BatchDownloadDialog(self)
        if dlg.exec():
            res = dlg.get_result()
            for url in res["urls"]:
                self.engine.create_download(
                    url=url,
                    category=res["category"],
                    connections=res["connections"],
                    auto_start=res["auto_start"]
                )
            self._load_table_data()
            QMessageBox.information(self, "Batch Enqueued", f"Successfully added {len(res['urls'])} download(s) to P-Downloader!")

    def show_scheduler_dialog(self):
        dlg = SchedulerDialog(self.engine.db, self)
        dlg.exec()

    def show_grabber_dialog(self):
        dlg = GrabberDialog(self)
        if dlg.exec():
            for url in dlg.selected_urls:
                self.engine.create_download(url=url, auto_start=True)
            self._load_table_data()

    def show_settings_dialog(self):
        dlg = SettingsDialog(self.engine.db, self)
        dlg.exec()
        self._update_speed_limiter_label()

    def open_transfer_dialog(self, task: DownloadTask):
        if task.task_id in self.active_dialogs:
            dlg = self.active_dialogs[task.task_id]
            dlg.show()
            dlg.raise_()
            dlg.activateWindow()
            return

        dlg = DownloadDialog(task, self, self.engine)
        self.active_dialogs[task.task_id] = dlg
        dlg.finished.connect(lambda: self.active_dialogs.pop(task.task_id, None))
        dlg.show()

    # ================= Clipboard Auto-Sniffing =================
    def _check_clipboard_link(self):
        if self.engine.db.get_setting("clipboard_monitor", "1") != "1":
            return
        cb = QApplication.clipboard()
        text = cb.text().strip()
        if not text or text == self.last_clipboard_text:
            return

        # Check if URL ends with common downloadable media extensions or is a magnet link
        lower = text.lower()
        is_magnet = lower.startswith("magnet:?xt=")
        is_media_url = (lower.startswith("http://") or lower.startswith("https://") or lower.startswith("ftp://")) and (
            any(lower.endswith(ext) for ext in [
                ".zip", ".rar", ".7z", ".tar", ".gz", ".iso", ".exe", ".msi",
                ".mp4", ".mkv", ".avi", ".webm", ".mp3", ".wav", ".flac", ".pdf",
                ".m3u8", ".apk", ".dmg"
            ])
            or ".m3u8" in lower
        )

        if is_magnet or is_media_url:
            self.last_clipboard_text = text
            try:
                from gui.quick_prompt_dialog import QuickPromptDialog
                prompt = QuickPromptDialog(text, self)
                prompt.download_requested.connect(self._handle_quick_download)
                prompt.show()
            except Exception:
                self.showNormal()
                self.activateWindow()
                self.show_add_dialog(initial_url=text)

    def _handle_quick_download(self, url: str, start_now: bool):
        task = self.engine.create_download(url=url, auto_start=start_now)
        self._load_table_data()
        if start_now:
            self.open_transfer_dialog(task)

    # ================= Table Loading & Rendering =================
    def _load_table_data(self):
        items = self.engine.db.get_all_downloads()
        filter_key = self._get_current_filter()

        filtered = []
        for item in items:
            cat = item.get("category", "")
            st = item.get("status", "")
            if filter_key == "all":
                filtered.append(item)
            elif filter_key == "compressed" and cat == "Compressed":
                filtered.append(item)
            elif filter_key == "documents" and cat == "Documents":
                filtered.append(item)
            elif filter_key == "music" and cat == "Music":
                filtered.append(item)
            elif filter_key == "programs" and cat == "Programs":
                filtered.append(item)
            elif filter_key == "video" and cat == "Video":
                filtered.append(item)
            elif filter_key == "downloading" and st == "downloading":
                filtered.append(item)
            elif filter_key == "finished" and st == "completed":
                filtered.append(item)
            elif filter_key == "paused" and st == "paused":
                filtered.append(item)
            elif filter_key == "error" and st == "error":
                filtered.append(item)
            elif filter_key in ("queue_main", "queue_sync"):
                filtered.append(item)

        self.table.setRowCount(len(filtered))
        for row, item in enumerate(filtered):
            self._set_table_row(row, item)

        self._update_sidebar_counts(items)

    def _get_current_filter(self) -> str:
        current = self.tree.currentItem()
        if not current:
            return "all"
        key = current.data(0, Qt.ItemDataRole.UserRole)
        return key or "all"

    def _update_sidebar_counts(self, items: list = None):
        if items is None:
            items = self.engine.db.get_all_downloads()

        c_all = len(items)
        c_comp = sum(1 for i in items if i.get("category") == "Compressed")
        c_doc = sum(1 for i in items if i.get("category") == "Documents")
        c_music = sum(1 for i in items if i.get("category") == "Music")
        c_prog = sum(1 for i in items if i.get("category") == "Programs")
        c_vid = sum(1 for i in items if i.get("category") == "Video")

        c_down = sum(1 for i in items if i.get("status") == "downloading")
        c_fin = sum(1 for i in items if i.get("status") == "completed")
        c_paused = sum(1 for i in items if i.get("status") == "paused")
        c_err = sum(1 for i in items if i.get("status") == "error")

        self._set_item_count(self.item_all, "All Downloads", c_all)
        self._set_item_count(self.item_comp, "Compressed", c_comp)
        self._set_item_count(self.item_doc, "Documents", c_doc)
        self._set_item_count(self.item_music, "Music", c_music)
        self._set_item_count(self.item_prog, "Programs", c_prog)
        self._set_item_count(self.item_vid, "Video", c_vid)

        self._set_item_count(self.item_downloading, "Downloading", c_down)
        self._set_item_count(self.item_finished, "Finished", c_fin)
        self._set_item_count(self.item_paused, "Paused", c_paused)
        self._set_item_count(self.item_error, "Error / Expired", c_err)

    def _set_item_count(self, item: QTreeWidgetItem, name: str, count: int):
        if count > 0:
            item.setText(0, f"{name} ({count})")
        else:
            item.setText(0, name)

    def _set_table_row(self, row: int, item: dict):
        task_id = item["id"]
        task = self.engine.tasks.get(task_id)

        # Explicit text color #0f172a prevents invisible dark-mode text
        text_color = QColor("#0f172a")

        # 0. File Name
        fn_item = QTableWidgetItem(item["filename"])
        fn_item.setData(Qt.ItemDataRole.UserRole, task_id)
        fn_item.setForeground(text_color)
        fn_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.table.setItem(row, 0, fn_item)

        # 1. Size
        total = task.total_bytes if task else item["total_bytes"]
        down = task.downloaded_bytes if task else item["downloaded_bytes"]
        sz_item = QTableWidgetItem(format_bytes(total))
        sz_item.setForeground(text_color)
        sz_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(row, 1, sz_item)

        # 2. Status
        status = task.status if task else item["status"]
        st_item = QTableWidgetItem(status.capitalize())
        if status == "completed":
            st_item.setForeground(QColor("#059669"))
            st_item.setText("Finished")
        elif status == "downloading":
            st_item.setForeground(QColor("#0284c7"))
            st_item.setText("Downloading")
        elif status == "paused":
            st_item.setForeground(QColor("#d97706"))
            st_item.setText("Paused")
        elif status == "error":
            st_item.setForeground(QColor("#dc2626"))
            st_item.setText("Error")
        else:
            st_item.setForeground(text_color)
        st_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.table.setItem(row, 2, st_item)

        # 3. Progress Bar Widget
        pbar = self.table.cellWidget(row, 3)
        if not isinstance(pbar, QProgressBar):
            pbar = QProgressBar()
            pbar.setFixedHeight(16)
            self.table.setCellWidget(row, 3, pbar)

        if total > 0:
            pct = int((down / total) * 100)
            pbar.setValue(min(100, max(0, pct)))
            pbar.setFormat(f"{pct}% ({format_bytes(down)})")
        else:
            pbar.setValue(100 if status == "completed" else 0)
            pbar.setFormat("Complete" if status == "completed" else "0%")

        # 4. Speed
        spd = task.speed if task and status == "downloading" else 0.0
        spd_item = QTableWidgetItem(format_speed(spd) if spd > 0 else "")
        spd_item.setForeground(QColor("#059669") if spd > 0 else text_color)
        spd_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(row, 4, spd_item)

        # 5. Time Left
        if task and status == "downloading" and total > down and spd > 0:
            eta = format_eta(total - down, spd)
        else:
            eta = ""
        eta_item = QTableWidgetItem(eta)
        eta_item.setForeground(text_color)
        eta_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 5, eta_item)

        # 6. Category
        cat_item = QTableWidgetItem(item.get("category", "General"))
        cat_item.setForeground(text_color)
        self.table.setItem(row, 6, cat_item)

        # 7. URL
        url_item = QTableWidgetItem(item["url"])
        url_item.setForeground(QColor("#64748b"))
        self.table.setItem(row, 7, url_item)

    def _refresh_table(self):
        active_speed = 0.0
        downloading_count = 0

        for row in range(self.table.rowCount()):
            fn_item = self.table.item(row, 0)
            if not fn_item:
                continue
            task_id = fn_item.data(Qt.ItemDataRole.UserRole)
            task = self.engine.tasks.get(task_id)
            if task and task.status == "downloading":
                active_speed += task.speed
                downloading_count += 1
                total = task.total_bytes
                down = task.downloaded_bytes

                # Status
                st_item = self.table.item(row, 2)
                if st_item:
                    st_item.setText("Downloading")
                    st_item.setForeground(QColor("#0284c7"))

                # Progress
                pbar = self.table.cellWidget(row, 3)
                if pbar and total > 0:
                    pct = int((down / total) * 100)
                    pbar.setValue(min(100, max(0, pct)))
                    pbar.setFormat(f"{pct}% ({format_bytes(down)})")

                # Speed & ETA
                spd_item = self.table.item(row, 4)
                if spd_item:
                    spd_item.setText(format_speed(task.speed))
                    spd_item.setForeground(QColor("#059669"))

                eta_item = self.table.item(row, 5)
                if eta_item:
                    eta_item.setText(format_eta(total - down, task.speed) if total > down and task.speed > 0 else "")

        summary = f"Active Downloads: {downloading_count}  |  Total Bandwidth: {format_speed(active_speed)}"
        self.status_bar.showMessage(summary)

        nm = NetworkManager()
        active_count = len(nm.get_active_interfaces()) if nm.bonding_enabled else 1
        self.lbl_net_status.setText(f"🌐 Bonding: {active_count} Adapter(s)  ")

    def _on_tree_selected(self, item: QTreeWidgetItem, column: int):
        self._load_table_data()

    def _on_table_double_clicked(self, index):
        row = index.row()
        fn_item = self.table.item(row, 0)
        if not fn_item:
            return
        task_id = fn_item.data(Qt.ItemDataRole.UserRole)
        task = self.engine.tasks.get(task_id)
        if task:
            if task.status == "error" and ("Link Expired" in task.error_message or "403" in task.error_message):
                self.show_refresh_dialog(task_id)
            else:
                self.open_transfer_dialog(task)
        else:
            item = self.engine.db.get_download(task_id)
            if item:
                if item.get("status") == "error":
                    self.show_refresh_dialog(task_id)
                elif os.path.exists(item["save_path"]):
                    os.startfile(item["save_path"])

    def _get_selected_task_ids(self) -> list:
        selected_rows = set(index.row() for index in self.table.selectedIndexes())
        task_ids = []
        for r in selected_rows:
            fn_item = self.table.item(r, 0)
            if fn_item:
                task_ids.append(fn_item.data(Qt.ItemDataRole.UserRole))
        return task_ids

    def _resume_selected(self):
        for task_id in self._get_selected_task_ids():
            self.engine.resume_download(task_id)
        self._load_table_data()

    def _pause_selected(self):
        for task_id in self._get_selected_task_ids():
            self.engine.pause_download(task_id)
        self._load_table_data()

    def _delete_selected(self):
        task_ids = self._get_selected_task_ids()
        if not task_ids:
            return
        res = QMessageBox.question(
            self, "Confirm Delete",
            f"Remove {len(task_ids)} download(s) from the list?\n(Downloaded files on disk will not be deleted)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            for task_id in task_ids:
                self.engine.delete_download(task_id, delete_file=False)
            self._load_table_data()

    def _clear_completed(self):
        items = self.engine.db.get_all_downloads()
        completed = [item["id"] for item in items if item["status"] == "completed"]
        for cid in completed:
            self.engine.delete_download(cid, delete_file=False)
        self._load_table_data()
        self.status_bar.showMessage(f"Cleared {len(completed)} completed download(s) from list.", 3000)

    def _toggle_speed_limiter(self):
        current = self.engine.db.get_setting("limit_speed_enabled", "0")
        new_val = "1" if current == "0" else "0"
        self.engine.db.set_setting("limit_speed_enabled", new_val)
        self._update_speed_limiter_label()

    def _update_speed_limiter_label(self):
        enabled = self.engine.db.get_setting("limit_speed_enabled", "0") == "1"
        speed = self.engine.db.get_setting("speed_limit_kb", "1024")
        if enabled:
            self.lbl_speed_limiter_status.setText(f"⚡ Speed Limiter: ON ({speed} KB/s)  ")
            self.lbl_speed_limiter_status.setStyleSheet("color: #059669; font-weight: bold;")
            self.act_speed_limit.setText(f"⚡ Speed Limiter: ON ({speed} KB/s)")
        else:
            self.lbl_speed_limiter_status.setText("⚡ Speed Limiter: OFF  ")
            self.lbl_speed_limiter_status.setStyleSheet("color: #64748b; font-weight: bold;")
            self.act_speed_limit.setText("⚡ Speed Limiter: OFF")

    def _open_default_folder(self):
        from core.categories import DEFAULT_DOWNLOADS_DIR
        def_dir = self.engine.db.get_setting("default_dir", DEFAULT_DOWNLOADS_DIR)
        os.makedirs(def_dir, exist_ok=True)
        os.startfile(def_dir)

    def _export_list(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Download List", "downloads.txt", "Text Files (*.txt)")
        if path:
            items = self.engine.db.get_all_downloads()
            with open(path, "w", encoding="utf-8") as f:
                for item in items:
                    f.write(f"{item['url']}\n")
            QMessageBox.information(self, "Exported", f"Saved {len(items)} URL(s) to {path}")

    def _show_context_menu(self, pos):
        task_ids = self._get_selected_task_ids()
        if not task_ids:
            return

        menu = QMenu(self)
        act_resume = menu.addAction("▶️ Resume")
        act_pause = menu.addAction("⏸️ Pause")
        act_refresh_addr = menu.addAction("🔄 Refresh Download Address...")
        menu.addSeparator()

        act_open_file = menu.addAction("📄 Open File")
        act_open_folder = menu.addAction("📁 Open Folder in Explorer")
        act_copy_link = menu.addAction("🔗 Copy Download Link")
        menu.addSeparator()

        act_remove_list = menu.addAction("🧹 Remove from List")
        act_delete_disk = menu.addAction("🗑️ Delete File from Disk")

        first_item = self.engine.db.get_download(task_ids[0])
        save_path = first_item["save_path"] if first_item else ""
        file_exists = os.path.exists(save_path) if save_path else False

        act_open_file.setEnabled(file_exists)
        act_open_folder.setEnabled(bool(save_path and os.path.exists(os.path.dirname(save_path))))

        action = menu.exec(QCursor.pos())
        if action == act_resume:
            self._resume_selected()
        elif action == act_pause:
            self._pause_selected()
        elif action == act_refresh_addr:
            self.show_refresh_dialog(task_ids[0])
        elif action == act_open_file and file_exists:
            os.startfile(save_path)
        elif action == act_open_folder:
            subprocess.run(f'explorer /select,"{save_path}"')
        elif action == act_copy_link and first_item:
            QApplication.clipboard().setText(first_item["url"])
        elif action == act_remove_list:
            self._delete_selected()
        elif action == act_delete_disk:
            c = QMessageBox.warning(
                self, "Confirm Permanent Delete",
                f"Permanently delete {len(task_ids)} file(s) from disk?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if c == QMessageBox.StandardButton.Yes:
                for tid in task_ids:
                    self.engine.delete_download(tid, delete_file=True)
                self._load_table_data()

    def _show_about(self):
        icon_path = os.path.join(RESOURCES_DIR, "logo.png")
        QMessageBox.about(
            self, "About P-Downloader",
            "<h2>P-Downloader (Pure Downloader)</h2>"
            f"<p><b>Version {__version__} (High-Speed Acceleration Engine)</b></p>"
            "<p>A modern, clean-room download manager built from scratch with Python & PyQt6.</p>"
            "<hr>"
            "<p><b>Key Capabilities:</b></p>"
            "<ul>"
            "<li>Dynamic multi-connection segmentation (up to 32 parallel connections)</li>"
            "<li>HTTP Range request byte-slicing with zero-copy file assembly</li>"
            "<li>Persistent SQLite database with pause & error recovery</li>"
            "<li>IDM-style Scheduler, Queue management, and Site Grabber</li>"
            "<li>Browser extension integration (Chrome, Edge, Firefox, Brave)</li>"
            "<li>Speed Limiter bandwidth throttling</li>"
            "</ul>"
        )

    def _on_engine_update(self, task: DownloadTask):
        if task.status == "completed":
            if self.engine.db.get_setting("sound_on_finish", "1") == "1":
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass

            if self.engine.db.get_setting("toast_on_finish", "1") == "1":
                self.tray.showMessage(
                    "Download Finished",
                    f"{os.path.basename(task.save_path)} has finished downloading.",
                    QSystemTrayIcon.MessageIcon.Information,
                    4000
                )

    def show_refresh_dialog(self, task_id: str):
        dlg = RefreshDownloadDialog(self, self.engine, task_id)
        if dlg.exec():
            self._load_table_data()

    def show_site_logins_dialog(self):
        dlg = SiteLoginsDialog(self)
        dlg.exec()

    def _refresh_selected_address(self):
        task_ids = self._get_selected_task_ids()
        if not task_ids:
            QMessageBox.information(self, "Select Download", "Please select a download to refresh its address.")
            return
        self.show_refresh_dialog(task_ids[0])
