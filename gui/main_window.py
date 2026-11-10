"""
Comprehensive Modern IDM-Grade Main Dashboard Window for P-Downloader.
Features Modern Light Theme, Collapsible Sidebar (collapsed by default),
IDM-style central download table with per-row Three-Dot action menus,
and thread-safe live progress/status synchronization.
"""
import os
import sys
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView, QToolBar, QMenuBar, QMenu, QStatusBar,
    QProgressBar, QMessageBox, QApplication, QSystemTrayIcon,
    QLabel, QPushButton, QFileDialog, QToolButton, QStackedWidget
)
from PyQt6.QtGui import (  # pylint: disable=no-name-in-module
    QAction, QIcon, QCursor, QColor, QFont, QPixmap
)
from PyQt6.QtCore import (  # pylint: disable=no-name-in-module
    Qt, QTimer, QPoint, QSize
)

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
from .icons import (
    get_icon, get_sidebar_icon, get_file_type_icon, render_lucide_pixmap,
    COLOR_PRIMARY, COLOR_SLATE, COLOR_DARK, COLOR_DANGER,
    COLOR_WHITE, COLOR_SUCCESS, COLOR_WARNING
)
try:
    import winsound
except ImportError:
    winsound = None

RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources"))


class MainWindow(QMainWindow):
    def __init__(self, engine: DownloadEngine):
        super().__init__()
        self.engine = engine
        self.active_dialogs = {}
        self.last_clipboard_text = ""
        self.sidebar_is_collapsed = True
        self._force_quit = False

        self.setWindowTitle(f"P-Downloader - Pure Download Accelerator (v{__version__})")
        self.resize(1180, 700)
        self.setMinimumSize(850, 480)
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

        # Connect engine update listener
        self.engine.add_listener(self._on_engine_update)

        # UI Refresh loop for live bandwidth & progress bars (throttled to 500ms)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_table)
        self.refresh_timer.start(500)

        # Clipboard Auto-Monitor Timer
        self.clip_timer = QTimer(self)
        self.clip_timer.timeout.connect(self._check_clipboard_link)
        self.clip_timer.start(1000)

        # Load initial download table
        self._load_table_data()

    def _add_toolbar_button(self, toolbar: QToolBar, text: str, icon: QIcon, tooltip: str, callback, object_name: str = None) -> QAction:
        act = QAction(icon, text, self)
        act.setToolTip(tooltip)
        act.triggered.connect(callback)
        btn = QToolButton(toolbar)
        btn.setDefaultAction(act)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        btn.setIconSize(QSize(18, 18))
        btn.setFixedHeight(34)
        if object_name:
            btn.setObjectName(object_name)
        toolbar.addWidget(btn)
        return act

    def _init_menu_and_toolbar(self):
        menubar = self.menuBar()

        # ================= Tasks Menu =================
        menu_tasks = menubar.addMenu("&Tasks")

        act_add_url = QAction(get_icon("plus", COLOR_DARK, 16), "&Add New Download...", self)
        act_add_url.setShortcut("Ctrl+N")
        act_add_url.triggered.connect(self.show_add_dialog)
        menu_tasks.addAction(act_add_url)

        act_batch = QAction(get_icon("layers", COLOR_DARK, 16), "&Batch Add URLs...", self)
        act_batch.setShortcut("Ctrl+B")
        act_batch.triggered.connect(self.show_batch_dialog)
        menu_tasks.addAction(act_batch)

        act_yt = QAction(get_icon("video", COLOR_DARK, 16), "&YouTube / Stream Downloader...", self)
        act_yt.setShortcut("Ctrl+Y")
        act_yt.triggered.connect(lambda: self.show_youtube_dialog())
        menu_tasks.addAction(act_yt)

        act_grabber = QAction(get_icon("search", COLOR_DARK, 16), "Run Site &Grabber...", self)
        act_grabber.setShortcut("Ctrl+G")
        act_grabber.triggered.connect(self.show_grabber_dialog)
        menu_tasks.addAction(act_grabber)

        menu_tasks.addSeparator()

        act_ext = QAction(get_icon("globe", COLOR_DARK, 16), "Browser &Extension Integration...", self)
        act_ext.triggered.connect(self.show_extension_dialog)
        menu_tasks.addAction(act_ext)

        menu_tasks.addSeparator()

        act_exit = QAction(get_icon("square", COLOR_DARK, 16), "E&xit", self)
        act_exit.setShortcut("Alt+F4")
        act_exit.triggered.connect(self._exit_app)
        menu_tasks.addAction(act_exit)

        # ================= File Menu =================
        menu_file = menubar.addMenu("&File")

        act_open_dir = QAction(get_icon("folder", COLOR_DARK, 16), "Open Default Downloads Folder", self)
        act_open_dir.triggered.connect(self._open_default_folder)
        menu_file.addAction(act_open_dir)

        act_clear_done = QAction(get_icon("check-check", COLOR_DARK, 16), "Clear Completed from List", self)
        act_clear_done.triggered.connect(self._clear_completed)
        menu_file.addAction(act_clear_done)

        menu_file.addSeparator()

        act_export = QAction(get_icon("external-link", COLOR_DARK, 16), "Export Download List to Text...", self)
        act_export.triggered.connect(self._export_list)
        menu_file.addAction(act_export)

        # ================= Downloads Menu =================
        menu_downloads = menubar.addMenu("&Downloads")

        act_res_sel = QAction(get_icon("play", COLOR_DARK, 16), "Resume", self)
        act_res_sel.setShortcut("Ctrl+R")
        act_res_sel.triggered.connect(self._resume_selected)
        menu_downloads.addAction(act_res_sel)

        act_pause_sel = QAction(get_icon("pause", COLOR_DARK, 16), "Pause", self)
        act_pause_sel.triggered.connect(self._pause_selected)
        menu_downloads.addAction(act_pause_sel)

        act_del_sel = QAction(get_icon("trash-2", COLOR_DANGER, 16), "Delete", self)
        act_del_sel.setShortcut("Del")
        act_del_sel.triggered.connect(self._delete_selected)
        menu_downloads.addAction(act_del_sel)

        menu_downloads.addSeparator()

        act_refresh_addr = QAction(get_icon("rotate-cw", COLOR_DARK, 16), "&Refresh Download Address...", self)
        act_refresh_addr.setShortcut("Ctrl+U")
        act_refresh_addr.triggered.connect(self._refresh_selected_address)
        menu_downloads.addAction(act_refresh_addr)

        menu_downloads.addSeparator()

        self.act_speed_limit = QAction(get_icon("gauge", COLOR_DARK, 16), "Speed Limiter: Off", self)
        self.act_speed_limit.triggered.connect(self._toggle_speed_limiter)
        menu_downloads.addAction(self.act_speed_limit)

        # ================= Options Menu =================
        menu_options = menubar.addMenu("&Options")

        act_scheduler = QAction(get_icon("clock", COLOR_DARK, 16), "&Scheduler & Queues...", self)
        act_scheduler.setShortcut("Ctrl+S")
        act_scheduler.triggered.connect(self.show_scheduler_dialog)
        menu_options.addAction(act_scheduler)

        act_site_logins = QAction(get_icon("shield", COLOR_DARK, 16), "&Site Logins & Passwords...", self)
        act_site_logins.triggered.connect(self.show_site_logins_dialog)
        menu_options.addAction(act_site_logins)

        act_settings = QAction(get_icon("settings", COLOR_DARK, 16), "&Preferences / Options...", self)
        act_settings.setShortcut("Ctrl+O")
        act_settings.triggered.connect(self.show_settings_dialog)
        menu_options.addAction(act_settings)

        # ================= View Menu =================
        menu_view = menubar.addMenu("&View")

        act_toggle_side = QAction(get_icon("panel-left", COLOR_DARK, 16), "Toggle Sidebar", self)
        act_toggle_side.setShortcut("Ctrl+B")
        act_toggle_side.triggered.connect(self._toggle_sidebar)
        menu_view.addAction(act_toggle_side)

        act_refresh_view = QAction(get_icon("rotate-cw", COLOR_DARK, 16), "&Refresh List", self)
        act_refresh_view.setShortcut("F5")
        act_refresh_view.triggered.connect(self._load_table_data)
        menu_view.addAction(act_refresh_view)

        # ================= Help Menu =================
        menu_help = menubar.addMenu("&Help")

        act_about = QAction(get_icon("info", COLOR_DARK, 16), "&About P-Downloader", self)
        act_about.triggered.connect(self._show_about)
        menu_help.addAction(act_about)

        # ================= Top Modern Ribbon ToolBar =================
        toolbar = QToolBar("Main Controls", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 1. Primary Action: Add URL
        self._add_toolbar_button(
            toolbar, "Add URL",
            get_icon("plus", COLOR_WHITE, 18),
            "Add new download URL (Ctrl+N)",
            self.show_add_dialog,
            object_name="primaryBtn"
        )

        # 2. Secondary Input Actions
        self._add_toolbar_button(
            toolbar, "Batch Add",
            get_icon("layers", COLOR_DARK, 18),
            "Add multiple URLs simultaneously",
            self.show_batch_dialog
        )

        self._add_toolbar_button(
            toolbar, "YouTube Streams",
            get_icon("video", COLOR_DARK, 18),
            "Download YouTube single video or entire playlist (Ctrl+Y)",
            lambda: self.show_youtube_dialog()
        )

        self._add_toolbar_button(
            toolbar, "Browser Extension",
            get_icon("globe", COLOR_DARK, 18),
            "Manage / Create Browser Extension for Chrome, Edge, Firefox",
            self.show_extension_dialog
        )

        toolbar.addSeparator()

        # 3. Transfer Control Actions
        self._add_toolbar_button(
            toolbar, "Resume",
            get_icon("play", COLOR_DARK, 18),
            "Resume selected download (Ctrl+R)",
            self._resume_selected
        )

        self._add_toolbar_button(
            toolbar, "Pause",
            get_icon("pause", COLOR_DARK, 18),
            "Pause selected download",
            self._pause_selected
        )

        self._add_toolbar_button(
            toolbar, "Refresh Link",
            get_icon("rotate-cw", COLOR_DARK, 18),
            "Refresh expired download address without losing progress (IDM feature)",
            self._refresh_selected_address
        )

        self._add_toolbar_button(
            toolbar, "Stop All",
            get_icon("square", COLOR_DARK, 18),
            "Stop all active downloads",
            self.engine.pause_all
        )

        toolbar.addSeparator()

        # 4. Cleanup & Deletion Actions
        self._add_toolbar_button(
            toolbar, "Delete",
            get_icon("trash-2", COLOR_DANGER, 18),
            "Remove selected download from list (Del)",
            self._delete_selected,
            object_name="dangerBtn"
        )

        self._add_toolbar_button(
            toolbar, "Clear Completed",
            get_icon("check-check", COLOR_DARK, 18),
            "Clear completed downloads from list",
            self._clear_completed
        )

        toolbar.addSeparator()

        # 5. Tools & Utilities
        self._add_toolbar_button(
            toolbar, "Scheduler",
            get_icon("clock", COLOR_DARK, 18),
            "Schedule timed downloads and queues (Ctrl+S)",
            self.show_scheduler_dialog
        )

        self._add_toolbar_button(
            toolbar, "Grabber",
            get_icon("search", COLOR_DARK, 18),
            "Explore website to sniff media and files (Ctrl+G)",
            self.show_grabber_dialog
        )

        toolbar.addSeparator()

        # 6. Preferences
        self._add_toolbar_button(
            toolbar, "Options",
            get_icon("settings", COLOR_DARK, 18),
            "Configure application preferences (Ctrl+O)",
            self.show_settings_dialog
        )

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # Horizontal Splitter (Sidebar + Downloads Workspace)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(2)

        # ================= Collapsible Left Sidebar =================
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setObjectName("sidebarContainer")
        sidebar_layout = QVBoxLayout(self.sidebar_widget)
        sidebar_layout.setContentsMargins(4, 6, 4, 6)
        sidebar_layout.setSpacing(4)

        # Sidebar Header Bar with Toggle Button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(4, 4, 4, 4)
        header_layout.setSpacing(6)

        self.btn_toggle_sidebar = QPushButton()
        self.btn_toggle_sidebar.setObjectName("secondaryBtn")
        self.btn_toggle_sidebar.setFixedSize(32, 28)
        self.btn_toggle_sidebar.setIcon(get_icon("panel-left", COLOR_SLATE, 16))
        self.btn_toggle_sidebar.setToolTip("Expand / Collapse Sidebar (Ctrl+B)")
        self.btn_toggle_sidebar.clicked.connect(self._toggle_sidebar)

        self.lbl_sidebar_title = QLabel("NAVIGATION")
        self.lbl_sidebar_title.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.lbl_sidebar_title.setStyleSheet("color: #64748B; letter-spacing: 0.5px;")

        header_layout.addWidget(self.btn_toggle_sidebar)
        header_layout.addWidget(self.lbl_sidebar_title)
        header_layout.addStretch()
        sidebar_layout.addWidget(header_widget)

        # TreeWidget
        self.tree = QTreeWidget()
        self.tree.setObjectName("sidebarTree")
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(8)
        self.tree.setAnimated(True)

        header_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        header_color = QColor("#64748B")

        # Tree: Categories
        self.root_cat = QTreeWidgetItem(self.tree, ["CATEGORIES"])
        self.root_cat.setExpanded(True)
        self.root_cat.setFont(0, header_font)
        self.root_cat.setForeground(0, header_color)
        self.root_cat.setFlags(self.root_cat.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        self.item_all = QTreeWidgetItem(self.root_cat, ["All Downloads"])
        self.item_all.setIcon(0, get_sidebar_icon("all"))
        self.item_all.setData(0, Qt.ItemDataRole.UserRole, "all")
        self.item_all.setToolTip(0, "All Downloads")

        self.item_comp = QTreeWidgetItem(self.root_cat, ["Compressed"])
        self.item_comp.setIcon(0, get_sidebar_icon("compressed"))
        self.item_comp.setData(0, Qt.ItemDataRole.UserRole, "compressed")
        self.item_comp.setToolTip(0, "Compressed Archives")

        self.item_doc = QTreeWidgetItem(self.root_cat, ["Documents"])
        self.item_doc.setIcon(0, get_sidebar_icon("documents"))
        self.item_doc.setData(0, Qt.ItemDataRole.UserRole, "documents")
        self.item_doc.setToolTip(0, "Documents")

        self.item_music = QTreeWidgetItem(self.root_cat, ["Music"])
        self.item_music.setIcon(0, get_sidebar_icon("music"))
        self.item_music.setData(0, Qt.ItemDataRole.UserRole, "music")
        self.item_music.setToolTip(0, "Music & Audio")

        self.item_prog = QTreeWidgetItem(self.root_cat, ["Programs"])
        self.item_prog.setIcon(0, get_sidebar_icon("programs"))
        self.item_prog.setData(0, Qt.ItemDataRole.UserRole, "programs")
        self.item_prog.setToolTip(0, "Programs & Installers")

        self.item_vid = QTreeWidgetItem(self.root_cat, ["Video"])
        self.item_vid.setIcon(0, get_sidebar_icon("video"))
        self.item_vid.setData(0, Qt.ItemDataRole.UserRole, "video")
        self.item_vid.setToolTip(0, "Videos & Movies")

        # Tree: Status
        self.root_status = QTreeWidgetItem(self.tree, ["STATUS"])
        self.root_status.setExpanded(True)
        self.root_status.setFont(0, header_font)
        self.root_status.setForeground(0, header_color)
        self.root_status.setFlags(self.root_status.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        self.item_downloading = QTreeWidgetItem(self.root_status, ["Downloading"])
        self.item_downloading.setIcon(0, get_sidebar_icon("downloading"))
        self.item_downloading.setData(0, Qt.ItemDataRole.UserRole, "downloading")
        self.item_downloading.setToolTip(0, "Active Transfers")

        self.item_finished = QTreeWidgetItem(self.root_status, ["Finished"])
        self.item_finished.setIcon(0, get_sidebar_icon("finished"))
        self.item_finished.setData(0, Qt.ItemDataRole.UserRole, "finished")
        self.item_finished.setToolTip(0, "Completed Downloads")

        self.item_paused = QTreeWidgetItem(self.root_status, ["Paused"])
        self.item_paused.setIcon(0, get_sidebar_icon("paused"))
        self.item_paused.setData(0, Qt.ItemDataRole.UserRole, "paused")
        self.item_paused.setToolTip(0, "Paused Downloads")

        self.item_error = QTreeWidgetItem(self.root_status, ["Error / Expired"])
        self.item_error.setIcon(0, get_sidebar_icon("error"))
        self.item_error.setData(0, Qt.ItemDataRole.UserRole, "error")
        self.item_error.setToolTip(0, "Failed / Expired Downloads")

        # Tree: Queues
        self.root_queues = QTreeWidgetItem(self.tree, ["QUEUES"])
        self.root_queues.setExpanded(True)
        self.root_queues.setFont(0, header_font)
        self.root_queues.setForeground(0, header_color)
        self.root_queues.setFlags(self.root_queues.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        self.item_queue_main = QTreeWidgetItem(self.root_queues, ["Main Queue"])
        self.item_queue_main.setIcon(0, get_sidebar_icon("queue_main"))
        self.item_queue_main.setData(0, Qt.ItemDataRole.UserRole, "queue_main")
        self.item_queue_main.setToolTip(0, "Main Download Queue")

        self.item_queue_sync = QTreeWidgetItem(self.root_queues, ["Sync Queue"])
        self.item_queue_sync.setIcon(0, get_sidebar_icon("queue_sync"))
        self.item_queue_sync.setData(0, Qt.ItemDataRole.UserRole, "queue_sync")
        self.item_queue_sync.setToolTip(0, "Synchronization Queue")

        self.tree.setCurrentItem(self.item_all)
        self.tree.itemClicked.connect(self._on_tree_selected)
        sidebar_layout.addWidget(self.tree)

        self.splitter.addWidget(self.sidebar_widget)

        # ================= Right Workspace: Stack (Table or Empty State) =================
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "File Name", "Size", "Status", "Progress", "Speed", "Time Left", "Category", "Actions"
        ])

        # Table Styling & Formatting
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._on_table_double_clicked)

        self.table.setColumnWidth(0, 310)
        self.table.setColumnWidth(1, 95)
        self.table.setColumnWidth(2, 95)
        self.table.setColumnWidth(3, 175)
        self.table.setColumnWidth(4, 95)
        self.table.setColumnWidth(5, 85)
        self.table.setColumnWidth(6, 95)
        self.table.setColumnWidth(7, 65)

        # Empty State Overlay Container
        self.empty_widget = QWidget()
        self.empty_widget.setObjectName("emptyStateContainer")
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(14)
        empty_layout.setContentsMargins(30, 40, 30, 40)

        lbl_empty_icon = QLabel()
        lbl_empty_icon.setPixmap(render_lucide_pixmap("inbox", COLOR_SLATE, 56))
        lbl_empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(lbl_empty_icon)

        lbl_empty_title = QLabel("No downloads yet")
        lbl_empty_title.setObjectName("emptyStateTitle")
        lbl_empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(lbl_empty_title)

        lbl_empty_sub = QLabel("Add a download link or browser stream to get started.")
        lbl_empty_sub.setObjectName("emptyStateSubtitle")
        lbl_empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(lbl_empty_sub)

        btn_empty_add = QPushButton("Add Download")
        btn_empty_add.setIcon(get_icon("plus", COLOR_WHITE, 16))
        btn_empty_add.setFixedWidth(160)
        btn_empty_add.setFixedHeight(36)
        btn_empty_add.clicked.connect(self.show_add_dialog)
        empty_layout.addWidget(btn_empty_add, alignment=Qt.AlignmentFlag.AlignCenter)

        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.table)        # Page 0: Table
        self.content_stack.addWidget(self.empty_widget) # Page 1: Empty state

        self.splitter.addWidget(self.content_stack)
        main_layout.addWidget(self.splitter)

        # Apply default collapsed state (collapsed by default!)
        saved_collapsed = (self.engine.db.get_setting("sidebar_collapsed", "1") == "1")
        self._apply_sidebar_state(saved_collapsed)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.lbl_net_status = QLabel("Bonding: Active  ")
        self.lbl_net_status.setStyleSheet("color: #16A34A; font-weight: bold;")
        self.status_bar.addPermanentWidget(self.lbl_net_status)

        self.lbl_speed_limiter_status = QLabel("Speed Limiter: OFF  ")
        self.lbl_speed_limiter_status.setStyleSheet("color: #64748B; font-weight: bold;")
        self.status_bar.addPermanentWidget(self.lbl_speed_limiter_status)

    def _init_tray(self):
        self.tray = QSystemTrayIcon(self)
        icon_path = os.path.join(RESOURCES_DIR, "logo.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(RESOURCES_DIR, "logo.png")
        if os.path.exists(icon_path):
            self.tray.setIcon(QIcon(icon_path))

        tray_menu = QMenu(self)
        act_show = tray_menu.addAction(get_icon("external-link", COLOR_DARK, 16), "Show P-Downloader")
        act_show.triggered.connect(lambda: (self.showNormal(), self.activateWindow(), self.raise_()))

        act_add = tray_menu.addAction(get_icon("plus", COLOR_DARK, 16), "Add New Download...")
        act_add.triggered.connect(self.show_add_dialog)

        tray_menu.addSeparator()

        act_stop = tray_menu.addAction(get_icon("square", COLOR_DARK, 16), "Stop All Downloads")
        act_stop.triggered.connect(self.engine.pause_all)

        tray_menu.addSeparator()

        act_quit = tray_menu.addAction(get_icon("square", COLOR_DANGER, 16), "Exit")
        act_quit.triggered.connect(self._exit_app)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()
            self.activateWindow()
            self.raise_()

    # ================= Collapsible Sidebar =================
    def _toggle_sidebar(self):
        self._apply_sidebar_state(not self.sidebar_is_collapsed)

    def _apply_sidebar_state(self, collapsed: bool):
        self.sidebar_is_collapsed = collapsed
        self.engine.db.set_setting("sidebar_collapsed", "1" if collapsed else "0")

        if collapsed:
            self.sidebar_widget.setFixedWidth(68)
            self.lbl_sidebar_title.setVisible(False)
            self.btn_toggle_sidebar.setIcon(get_icon("panel-left", COLOR_SLATE, 16))
            self.btn_toggle_sidebar.setToolTip("Expand Sidebar (Ctrl+B)")

            # Hide section header labels
            self.root_cat.setHidden(True)
            self.root_status.setHidden(True)
            self.root_queues.setHidden(True)

            # Clear visible text from child items so only icons show centered
            for itm in (
                self.item_all, self.item_comp, self.item_doc, self.item_music,
                self.item_prog, self.item_vid, self.item_downloading,
                self.item_finished, self.item_paused, self.item_error,
                self.item_queue_main, self.item_queue_sync
            ):
                itm.setText(0, "")
            self.splitter.setSizes([68, 1100])
        else:
            self.sidebar_widget.setFixedWidth(230)
            self.lbl_sidebar_title.setVisible(True)
            self.btn_toggle_sidebar.setIcon(get_icon("panel-left", COLOR_PRIMARY, 16))
            self.btn_toggle_sidebar.setToolTip("Collapse Sidebar (Ctrl+B)")

            # Show section header labels
            self.root_cat.setHidden(False)
            self.root_status.setHidden(False)
            self.root_queues.setHidden(False)

            # Restore full text labels with counts
            self._update_sidebar_counts()
            self.splitter.setSizes([230, 950])

    # ================= Dialog Openers =================
    def show_add_dialog(self, initial_url: str = "", page_url: str = "", quality: str = "",
                        initial_filename: str = "", referer: str = "", headers: dict = None, start_now: bool = False):
        if start_now and initial_url:
            self.engine.create_download(
                url=initial_url,
                filename=initial_filename or None,
                page_url=page_url or None,
                quality=quality or None,
                auto_start=True,
                headers=headers
            )
            self._load_table_data()
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
            self.engine.create_download(
                url=res["url"],
                filename=res["filename"],
                save_path=res["save_path"],
                category=res["category"],
                connections=res["connections"],
                auto_start=res["auto_start"],
                page_url=res.get("page_url"),
                quality=res.get("quality"),
                headers=res.get("headers")
            )
            self._load_table_data()

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
        """Opens separate detailed transfer dialog only on explicit user request."""
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

    def show_extension_dialog(self):
        from gui.extension_dialog import ExtensionDialog
        dlg = ExtensionDialog(self)
        dlg.exec()

    def show_youtube_dialog(self, initial_url: str = ""):
        from core.youtube_downloader import is_youtube_url, probe_youtube
        target_url = initial_url
        if not target_url:
            cb = QApplication.clipboard()
            text = cb.text().strip()
            if is_youtube_url(text):
                target_url = text

        if not target_url:
            self.show_add_dialog()
            return

        info = probe_youtube(target_url)
        from core.categories import DEFAULT_DOWNLOADS_DIR
        default_dir = os.path.join(DEFAULT_DOWNLOADS_DIR, "Video")

        from gui.youtube_dialog import YouTubeDownloadDialog
        dlg = YouTubeDownloadDialog(info, self, default_save_dir=default_dir)
        if dlg.exec():
            for item in dlg.selected_items:
                self.engine.create_download(
                    url=item["url"],
                    filename=item["filename"],
                    save_path=item["save_path"],
                    category="Video",
                    quality=dlg.selected_quality,
                    auto_start=dlg.start_immediately
                )
            self._load_table_data()

    # ================= Clipboard Auto-Sniffing =================
    def _check_clipboard_link(self):
        if self.engine.db.get_setting("clipboard_monitor", "1") != "1":
            return
        cb = QApplication.clipboard()
        text = cb.text().strip()
        if not text or text == self.last_clipboard_text:
            return

        from core.youtube_downloader import is_youtube_url
        lower = text.lower()
        is_magnet = lower.startswith("magnet:?xt=")
        is_yt = is_youtube_url(text)
        is_media_url = (lower.startswith("http://") or lower.startswith("https://") or lower.startswith("ftp://")) and (
            any(lower.endswith(ext) for ext in [
                ".zip", ".rar", ".7z", ".tar", ".gz", ".iso", ".exe", ".msi",
                ".mp4", ".mkv", ".avi", ".webm", ".mp3", ".wav", ".flac", ".pdf",
                ".m3u8", ".apk", ".dmg"
            ])
            or ".m3u8" in lower
        )

        if is_yt or is_magnet or is_media_url:
            self.last_clipboard_text = text
            self.show_add_dialog(initial_url=text)

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

        if len(filtered) == 0:
            self.content_stack.setCurrentWidget(self.empty_widget)
        else:
            self.content_stack.setCurrentWidget(self.table)

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
        tooltip = f"{name} ({count})" if count > 0 else name
        item.setToolTip(0, tooltip)
        if not self.sidebar_is_collapsed:
            if count > 0:
                item.setText(0, f"{name} ({count})")
            else:
                item.setText(0, name)
        else:
            item.setText(0, "")

    def _set_table_row(self, row: int, item: dict):
        task_id = item["id"]
        task = self.engine.tasks.get(task_id)

        # High-contrast slate typography for light theme
        text_color = QColor(COLOR_DARK)

        # 0. File Name & File Type Icon
        fn_item = QTableWidgetItem(item["filename"])
        fn_item.setData(Qt.ItemDataRole.UserRole, task_id)
        fn_item.setForeground(text_color)
        fn_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        fn_item.setToolTip(item["filename"])
        file_ext = os.path.splitext(item.get("filename", ""))[1]
        fn_item.setIcon(get_file_type_icon(item.get("category", "") or file_ext, 18))
        self.table.setItem(row, 0, fn_item)

        # 1. Size
        total = task.total_bytes if task and task.total_bytes > 0 else item.get("total_bytes", 0)
        down = task.downloaded_bytes if task else item.get("downloaded_bytes", 0)
        sz_item = QTableWidgetItem(format_bytes(total) if total > 0 else "Unknown")
        sz_item.setForeground(text_color)
        sz_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(row, 1, sz_item)

        # 2. Status
        status = task.status if task else item.get("status", "queued")
        st_item = QTableWidgetItem(status.capitalize())
        if status == "completed":
            st_item.setForeground(QColor(COLOR_SUCCESS))
            st_item.setText("Finished")
        elif status == "downloading":
            st_item.setForeground(QColor(COLOR_PRIMARY))
            st_item.setText("Downloading")
        elif status == "paused":
            st_item.setForeground(QColor(COLOR_WARNING))
            st_item.setText("Paused")
        elif status == "error":
            st_item.setForeground(QColor(COLOR_DANGER))
            st_item.setText("Error")
        else:
            st_item.setForeground(text_color)
        st_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.table.setItem(row, 2, st_item)

        # 3. Progress Bar Widget
        pbar = self.table.cellWidget(row, 3)
        if not isinstance(pbar, QProgressBar):
            pbar = QProgressBar()
            pbar.setFixedHeight(18)
            self.table.setCellWidget(row, 3, pbar)

        if total > 0:
            pct = int((down / total) * 100)
            pbar.setValue(min(100, max(0, pct)))
            pbar.setFormat(f"{pct}% ({format_bytes(down)})")
        else:
            pbar.setValue(100 if status == "completed" else 0)
            pbar.setFormat("Complete (100%)" if status == "completed" else "0%")

        # 4. Speed
        spd = task.speed if task and status == "downloading" else 0.0
        spd_item = QTableWidgetItem(format_speed(spd) if spd > 0 else "")
        spd_item.setForeground(QColor(COLOR_SUCCESS) if spd > 0 else text_color)
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

        # 7. Actions Menu Button (Three-Dot using Lucide icon)
        action_container = QWidget()
        action_layout = QHBoxLayout(action_container)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_action = QPushButton()
        btn_action.setObjectName("actionMenuBtn")
        btn_action.setIcon(get_icon("more-vertical", COLOR_SLATE, 16))
        btn_action.setFixedSize(28, 24)
        btn_action.setToolTip("Actions for this download")
        btn_action.clicked.connect(lambda _, tid=task_id, btn=btn_action: self._show_row_actions_menu(tid, btn))
        action_layout.addWidget(btn_action)
        self.table.setCellWidget(row, 7, action_container)

    def _show_row_actions_menu(self, task_id: str, anchor_btn: QWidget):
        item = self.engine.db.get_download(task_id)
        if not item:
            return

        task = self.engine.tasks.get(task_id)
        status = task.status if task else item.get("status", "queued")
        save_path = item.get("save_path", "")
        file_exists = os.path.exists(save_path) if save_path else False

        menu = QMenu(self)

        # Dynamic context actions with Lucide icons (no emojis)
        if status == "downloading":
            act_pause = menu.addAction(get_icon("pause", COLOR_SLATE, 16), "Pause Download")
            act_pause.triggered.connect(lambda: (self.engine.pause_download(task_id), self._load_table_data()))
            act_stop = menu.addAction(get_icon("square", COLOR_SLATE, 16), "Stop / Cancel")
            act_stop.triggered.connect(lambda: (self.engine.stop_download(task_id, False), self._load_table_data()))
            act_details = menu.addAction(get_icon("info", COLOR_SLATE, 16), "View Details...")
            if task:
                act_details.triggered.connect(lambda: self.open_transfer_dialog(task))
            act_copy = menu.addAction(get_icon("copy", COLOR_SLATE, 16), "Copy Download Link")
            act_copy.triggered.connect(lambda: QApplication.clipboard().setText(item["url"]))

        elif status == "paused":
            act_resume = menu.addAction(get_icon("play", COLOR_SLATE, 16), "Resume Download")
            act_resume.triggered.connect(lambda: (self.engine.resume_download(task_id), self._load_table_data()))
            act_stop = menu.addAction(get_icon("square", COLOR_SLATE, 16), "Stop / Cancel")
            act_stop.triggered.connect(lambda: (self.engine.stop_download(task_id, False), self._load_table_data()))
            act_refresh = menu.addAction(get_icon("rotate-cw", COLOR_SLATE, 16), "Refresh Link...")
            act_refresh.triggered.connect(lambda: self.show_refresh_dialog(task_id))
            menu.addSeparator()
            act_remove = menu.addAction(get_icon("trash-2", COLOR_SLATE, 16), "Remove from List")
            act_remove.triggered.connect(lambda: (self.engine.delete_download(task_id, False), self._load_table_data()))

        elif status == "completed":
            act_open = menu.addAction(get_icon("external-link", COLOR_SLATE, 16), "Open File")
            act_open.setEnabled(file_exists)
            if file_exists:
                act_open.triggered.connect(lambda: os.startfile(save_path))

            act_folder = menu.addAction(get_icon("folder", COLOR_SLATE, 16), "Open Containing Folder")
            dir_exists = bool(save_path and os.path.exists(os.path.dirname(save_path)))
            act_folder.setEnabled(dir_exists)
            if dir_exists:
                act_folder.triggered.connect(lambda: subprocess.run(["explorer.exe", f"/select,{os.path.normpath(save_path)}"]))

            act_copy = menu.addAction(get_icon("copy", COLOR_SLATE, 16), "Copy Download Link")
            act_copy.triggered.connect(lambda: QApplication.clipboard().setText(item["url"]))
            menu.addSeparator()
            act_remove = menu.addAction(get_icon("trash-2", COLOR_SLATE, 16), "Remove from List")
            act_remove.triggered.connect(lambda: (self.engine.delete_download(task_id, False), self._load_table_data()))
            act_del_file = menu.addAction(get_icon("trash", COLOR_DANGER, 16), "Delete File from Disk")
            act_del_file.triggered.connect(lambda: self._confirm_delete_disk(task_id))

        else:  # Error or queued
            act_retry = menu.addAction(get_icon("rotate-cw", COLOR_SLATE, 16), "Retry Download")
            act_retry.triggered.connect(lambda: (self.engine.resume_download(task_id), self._load_table_data()))
            act_refresh = menu.addAction(get_icon("rotate-cw", COLOR_SLATE, 16), "Refresh Link...")
            act_refresh.triggered.connect(lambda: self.show_refresh_dialog(task_id))
            menu.addSeparator()
            act_remove = menu.addAction(get_icon("trash-2", COLOR_SLATE, 16), "Remove from List")
            act_remove.triggered.connect(lambda: (self.engine.delete_download(task_id, False), self._load_table_data()))
            if file_exists:
                act_del_file = menu.addAction(get_icon("trash", COLOR_DANGER, 16), "Delete File from Disk")
                act_del_file.triggered.connect(lambda: self._confirm_delete_disk(task_id))

        pos = anchor_btn.mapToGlobal(QPoint(0, anchor_btn.height()))
        menu.exec(pos)

    def _confirm_delete_disk(self, task_id: str):
        c = QMessageBox.warning(
            self, "Confirm Permanent Delete",
            "Are you sure you want to delete this file from disk permanently?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if c == QMessageBox.StandardButton.Yes:
            self.engine.delete_download(task_id, delete_file=True)
            self._load_table_data()

    def _refresh_table(self):
        active_speed = 0.0
        downloading_count = 0

        for row in range(self.table.rowCount()):
            fn_item = self.table.item(row, 0)
            if not fn_item:
                continue
            task_id = fn_item.data(Qt.ItemDataRole.UserRole)
            task = self.engine.tasks.get(task_id)

            if task:
                total = task.total_bytes
                down = task.downloaded_bytes

                if task.status == "downloading":
                    active_speed += task.speed
                    downloading_count += 1

                    # Status
                    st_item = self.table.item(row, 2)
                    if st_item:
                        st_item.setText("Downloading")
                        st_item.setForeground(QColor("#2563eb"))

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
                        spd_item.setForeground(QColor("#16a34a"))

                    eta_item = self.table.item(row, 5)
                    if eta_item:
                        eta_item.setText(format_eta(total - down, task.speed) if total > down and task.speed > 0 else "")

                elif task.status == "completed":
                    st_item = self.table.item(row, 2)
                    if st_item and st_item.text() != "Finished":
                        st_item.setText("Finished")
                        st_item.setForeground(QColor("#16a34a"))
                    pbar = self.table.cellWidget(row, 3)
                    if pbar and pbar.value() < 100:
                        pbar.setValue(100)
                        pbar.setFormat("Complete (100%)")
                    spd_item = self.table.item(row, 4)
                    if spd_item and spd_item.text():
                        spd_item.setText("")
                    eta_item = self.table.item(row, 5)
                    if eta_item and eta_item.text():
                        eta_item.setText("")

        summary = f"Active Downloads: {downloading_count}  |  Total Bandwidth: {format_speed(active_speed)}"
        self.status_bar.showMessage(summary)

        nm = NetworkManager()
        active_count = len(nm.get_active_interfaces()) if nm.bonding_enabled else 1
        self.lbl_net_status.setText(f"Bonding: {active_count} Adapter(s)  ")

    def _on_engine_update(self, task: DownloadTask):
        """Thread-safe handler for engine lifecycle events."""
        QTimer.singleShot(0, lambda t=task: self._handle_engine_update_on_gui(t))

    def _handle_engine_update_on_gui(self, task: DownloadTask):
        # Look up row in table
        found_row = None
        for r in range(self.table.rowCount()):
            fn_item = self.table.item(r, 0)
            if fn_item and fn_item.data(Qt.ItemDataRole.UserRole) == task.task_id:
                found_row = r
                break

        if found_row is not None:
            st_item = self.table.item(found_row, 2)
            pbar = self.table.cellWidget(found_row, 3)
            spd_item = self.table.item(found_row, 4)
            eta_item = self.table.item(found_row, 5)

            if task.status == "completed":
                if st_item:
                    st_item.setText("Finished")
                    st_item.setForeground(QColor("#16a34a"))
                if pbar:
                    pbar.setValue(100)
                    pbar.setFormat("Complete (100%)")
                if spd_item:
                    spd_item.setText("")
                if eta_item:
                    eta_item.setText("")

                if self.engine.db.get_setting("sound_on_finish", "1") == "1":
                    try:
                        if winsound:
                            winsound.MessageBeep(winsound.MB_ICONASTERISK)
                    except Exception:
                        pass

                if self.engine.db.get_setting("toast_on_finish", "1") == "1":
                    fn = os.path.basename(task.save_path)
                    self.tray.showMessage(
                        "Download Finished",
                        f"{fn} has finished downloading.",
                        QSystemTrayIcon.MessageIcon.Information,
                        3000
                    )
            elif task.status == "paused":
                if st_item:
                    st_item.setText("Paused")
                    st_item.setForeground(QColor("#d97706"))
                if spd_item:
                    spd_item.setText("")
                if eta_item:
                    eta_item.setText("")
            elif task.status == "error":
                if st_item:
                    st_item.setText("Error")
                    st_item.setForeground(QColor("#dc2626"))
                if spd_item:
                    spd_item.setText("")
                if eta_item:
                    eta_item.setText("")

        self._update_sidebar_counts()

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
            if task.status == "completed" and os.path.exists(task.save_path):
                os.startfile(task.save_path)
            elif task.status == "error" and ("Link Expired" in task.error_message or "403" in task.error_message):
                self.show_refresh_dialog(task_id)
            else:
                self.open_transfer_dialog(task)
        else:
            item = self.engine.db.get_download(task_id)
            if item:
                if item.get("status") == "completed" and os.path.exists(item["save_path"]):
                    os.startfile(item["save_path"])
                elif item.get("status") == "error":
                    self.show_refresh_dialog(task_id)

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

    def _refresh_selected_address(self):
        task_ids = self._get_selected_task_ids()
        if task_ids:
            self.show_refresh_dialog(task_ids[0])

    def show_refresh_dialog(self, task_id: str):
        dlg = RefreshDownloadDialog(self, self.engine, task_id)
        if dlg.exec():
            self._load_table_data()

    def _toggle_speed_limiter(self):
        current = self.engine.db.get_setting("limit_speed_enabled", "0")
        new_val = "1" if current == "0" else "0"
        self.engine.db.set_setting("limit_speed_enabled", new_val)
        self._update_speed_limiter_label()

    def _update_speed_limiter_label(self):
        enabled = self.engine.db.get_setting("limit_speed_enabled", "0") == "1"
        speed = self.engine.db.get_setting("speed_limit_kb", "1024")
        if enabled:
            self.lbl_speed_limiter_status.setText(f"Speed Limiter: ON ({speed} KB/s)  ")
            self.lbl_speed_limiter_status.setStyleSheet("color: #16A34A; font-weight: bold;")
            self.act_speed_limit.setText(f"Speed Limiter: ON ({speed} KB/s)")
        else:
            self.lbl_speed_limiter_status.setText("Speed Limiter: OFF  ")
            self.lbl_speed_limiter_status.setStyleSheet("color: #64748B; font-weight: bold;")
            self.act_speed_limit.setText("Speed Limiter: OFF")

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
        act_resume = menu.addAction(get_icon("play", COLOR_DARK, 16), "Resume")
        act_pause = menu.addAction(get_icon("pause", COLOR_DARK, 16), "Pause")
        act_refresh_addr = menu.addAction(get_icon("rotate-cw", COLOR_DARK, 16), "Refresh Download Address...")
        menu.addSeparator()

        act_open_file = menu.addAction(get_icon("external-link", COLOR_DARK, 16), "Open File")
        act_open_folder = menu.addAction(get_icon("folder", COLOR_DARK, 16), "Open Folder in Explorer")
        act_copy_link = menu.addAction(get_icon("copy", COLOR_DARK, 16), "Copy Download Link")
        menu.addSeparator()

        act_remove_list = menu.addAction(get_icon("trash-2", COLOR_DARK, 16), "Remove from List")
        act_delete_disk = menu.addAction(get_icon("trash", COLOR_DANGER, 16), "Delete File from Disk")

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
            subprocess.run(["explorer.exe", f"/select,{os.path.normpath(save_path)}"])
        elif action == act_copy_link and first_item:
            QApplication.clipboard().setText(first_item["url"])
        elif action == act_remove_list:
            self._delete_selected()
        elif action == act_delete_disk:
            self._confirm_delete_disk(task_ids[0])

    def show_site_logins_dialog(self):
        dlg = SiteLoginsDialog(self)
        dlg.exec()

    def _show_about(self):
        icon_path = os.path.join(RESOURCES_DIR, "logo.png")
        QMessageBox.about(
            self, "About P-Downloader",
            "<h2>P-Downloader (Pure Download Accelerator)</h2>"
            f"<p><b>Version {__version__} (High-Speed Acceleration Engine)</b></p>"
            "<p>A modern, clean-room download manager built from scratch with Python & PyQt6.</p>"
            "<hr>"
            "<p><b>Key Capabilities:</b></p>"
            "<ul>"
            "<li>Dynamic multi-connection segmentation (up to 32 parallel connections)</li>"
            "<li>HTTP Range request byte-slicing with zero-copy file assembly</li>"
            "<li>YouTube single video and full playlist downloader with format selection</li>"
            "<li>Modern light interface with collapsible sidebar and three-dot action menus</li>"
            "<li>Persistent SQLite database with pause & error recovery</li>"
            "<li>IDM-style Scheduler, Queue management, and Site Grabber</li>"
            "<li>Browser extension integration (Chrome, Edge, Firefox, Brave)</li>"
            "</ul>"
        )

    def _exit_app(self):
        self._force_quit = True
        self.tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        minimize_to_tray = self.engine.db.get_setting("minimize_to_tray", "1") == "1"
        if minimize_to_tray and self.tray.isVisible():
            self.hide()
            self.tray.showMessage(
                "P-Downloader",
                "P-Downloader is still running in the Windows system tray.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            event.ignore()
        else:
            self.tray.hide()
            event.accept()
