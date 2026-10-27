"""
Comprehensive Full-Featured IDM-Style Preferences and Options Dialog.
Includes General, File Types/Save To, Connection, Logins, Proxy, and Sounds.
"""
import os
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QCheckBox, QTabWidget, QWidget,
    QFileDialog, QGroupBox, QGridLayout, QMessageBox, QTextEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from core.db import DownloadDB
from core.categories import DEFAULT_DOWNLOADS_DIR, CATEGORY_EXTENSIONS
from core.network_binder import NetworkManager

DEFAULT_AUTO_FILE_TYPES = (
    "3GP 7Z AAC ACE AIF ARJ ASF AVI BIN BZ2 EXE GZ GZIP IMG ISO LZH M4A M4V "
    "MKV MOV MP3 MP4 MPA MPE MPEG MPG MSI MSU OGG OGV PDF PLJ PPS PPT PPTX "
    "QT R0* R1* RA RAR RM RMVB SEA SIT SITX TAR TIF TIFF TS WAV WMA WMV Z ZIP"
)

class SettingsDialog(QDialog):
    def __init__(self, db: DownloadDB, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Configuration & Options")
        self.resize(640, 520)
        
        icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "logo.ico")
        if os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))
        
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        tabs = QTabWidget()

        # ==========================================
        # Tab 1: General
        # ==========================================
        tab_gen = QWidget()
        gen_vbox = QVBoxLayout(tab_gen)

        grp_start = QGroupBox("System & Integration")
        start_vbox = QVBoxLayout(grp_start)
        self.chk_startup = QCheckBox("Launch P-Downloader on Windows startup")
        self.chk_clipboard = QCheckBox("Automatically capture download links copied to Clipboard")
        self.chk_show_dlg = QCheckBox("Show download transfer progress window automatically")
        self.chk_tray = QCheckBox("Minimize to system tray on close")
        self.chk_av = QCheckBox("Scan completed downloads with Windows Defender automatically")

        start_vbox.addWidget(self.chk_startup)
        start_vbox.addWidget(self.chk_clipboard)
        start_vbox.addWidget(self.chk_show_dlg)
        start_vbox.addWidget(self.chk_tray)
        start_vbox.addWidget(self.chk_av)
        gen_vbox.addWidget(grp_start)

        grp_types = QGroupBox("Automatically Start Downloading the Following File Types")
        types_vbox = QVBoxLayout(grp_types)
        self.txt_file_types = QLineEdit(DEFAULT_AUTO_FILE_TYPES)
        types_vbox.addWidget(self.txt_file_types)
        types_vbox.addWidget(QLabel("<span style='color:#64748b; font-size:11px;'>Separate extensions by spaces (e.g. ZIP RAR EXE MP4 PDF)</span>"))
        gen_vbox.addWidget(grp_types)

        grp_ex = QGroupBox("Don't Start Download Automatically from Following Sites")
        ex_vbox = QVBoxLayout(grp_ex)
        self.txt_exceptions = QLineEdit()
        self.txt_exceptions.setPlaceholderText("*.example.com, download.mysite.org")
        ex_vbox.addWidget(self.txt_exceptions)
        gen_vbox.addWidget(grp_ex)
        gen_vbox.addStretch()

        tabs.addTab(tab_gen, "General")

        # ==========================================
        # Tab 2: Save To / Categories
        # ==========================================
        tab_dirs = QWidget()
        dirs_vbox = QVBoxLayout(tab_dirs)

        grp_def_dir = QGroupBox("Default Download Directory")
        dd_layout = QHBoxLayout(grp_def_dir)
        self.txt_def_dir = QLineEdit()
        btn_br_def = QPushButton("Browse...")
        btn_br_def.setObjectName("secondaryBtn")
        btn_br_def.clicked.connect(lambda: self._browse_dir(self.txt_def_dir))
        dd_layout.addWidget(self.txt_def_dir)
        dd_layout.addWidget(btn_br_def)
        dirs_vbox.addWidget(grp_def_dir)

        grp_cats = QGroupBox("Category Save Folders")
        cats_grid = QGridLayout(grp_cats)
        self.cat_inputs = {}
        for row, cat in enumerate(["Compressed", "Documents", "Music", "Programs", "Video"]):
            cats_grid.addWidget(QLabel(f"{cat}:"), row, 0)
            txt = QLineEdit()
            btn = QPushButton("Browse...")
            btn.setObjectName("secondaryBtn")
            btn.clicked.connect(lambda _, t=txt: self._browse_dir(t))
            cats_grid.addWidget(txt, row, 1)
            cats_grid.addWidget(btn, row, 2)
            self.cat_inputs[cat] = txt

        dirs_vbox.addWidget(grp_cats)

        grp_temp = QGroupBox("Temporary Folder")
        tmp_layout = QHBoxLayout(grp_temp)
        self.txt_temp_dir = QLineEdit()
        btn_br_tmp = QPushButton("Browse...")
        btn_br_tmp.setObjectName("secondaryBtn")
        btn_br_tmp.clicked.connect(lambda: self._browse_dir(self.txt_temp_dir))
        tmp_layout.addWidget(self.txt_temp_dir)
        tmp_layout.addWidget(btn_br_tmp)
        dirs_vbox.addWidget(grp_temp)
        dirs_vbox.addStretch()

        tabs.addTab(tab_dirs, "Save To")

        # ==========================================
        # Tab 3: Connection & Speed Limiter
        # ==========================================
        tab_conn = QWidget()
        conn_vbox = QVBoxLayout(tab_conn)

        grp_net = QGroupBox("Connection Type / Speed")
        net_grid = QGridLayout(grp_net)

        net_grid.addWidget(QLabel("Connection Type:"), 0, 0)
        self.cmb_conn_type = QComboBox()
        self.cmb_conn_type.addItems([
            "High Speed: Direct / Broadband / 4G / 5G / Fiber",
            "Medium Speed: DSL / Standard Cable",
            "Low Speed: Dial-up / Mobile Edge"
        ])
        net_grid.addWidget(self.cmb_conn_type, 0, 1)

        net_grid.addWidget(QLabel("Max Connection Number per File:"), 1, 0)
        self.cmb_max_conns = QComboBox()
        self.cmb_max_conns.addItems(["1", "2", "4", "8", "16", "24", "32"])
        self.cmb_max_conns.setCurrentText("8")
        net_grid.addWidget(self.cmb_max_conns, 1, 1)

        net_grid.addWidget(QLabel("Max Simultaneous Downloads:"), 2, 0)
        self.spin_simultaneous = QSpinBox()
        self.spin_simultaneous.setRange(1, 10)
        self.spin_simultaneous.setValue(2)
        net_grid.addWidget(self.spin_simultaneous, 2, 1)

        net_grid.addWidget(QLabel("Connection Timeout:"), 3, 0)
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(5, 120)
        self.spin_timeout.setValue(15)
        self.spin_timeout.setSuffix(" sec")
        net_grid.addWidget(self.spin_timeout, 3, 1)
        conn_vbox.addWidget(grp_net)

        grp_speed = QGroupBox("Speed Limiter (Bandwidth Throttling)")
        spd_layout = QGridLayout(grp_speed)
        self.chk_speed_limit = QCheckBox("Enable Speed Limiter")
        self.spin_speed_limit = QSpinBox()
        self.spin_speed_limit.setRange(10, 1000000)
        self.spin_speed_limit.setValue(1024)
        self.spin_speed_limit.setSuffix(" KB/s")

        spd_layout.addWidget(self.chk_speed_limit, 0, 0)
        spd_layout.addWidget(self.spin_speed_limit, 0, 1)
        conn_vbox.addWidget(grp_speed)
        conn_vbox.addStretch()

        tabs.addTab(tab_conn, "Connection")

        # ==========================================
        # Tab 4: Site Logins & Authentication
        # ==========================================
        tab_auth = QWidget()
        auth_vbox = QVBoxLayout(tab_auth)
        auth_vbox.addWidget(QLabel("Manage HTTP Basic, Digest, or Server Logins per Domain:"))

        self.table_auth = QTableWidget()
        self.table_auth.setColumnCount(3)
        self.table_auth.setHorizontalHeaderLabels(["Server / Domain", "User Name", "Password"])
        self.table_auth.horizontalHeader().setStretchLastSection(True)
        auth_vbox.addWidget(self.table_auth)

        auth_btn_layout = QHBoxLayout()
        btn_add_auth = QPushButton("Add Login")
        btn_add_auth.clicked.connect(self._add_auth_row)
        btn_del_auth = QPushButton("Remove Login")
        btn_del_auth.setObjectName("secondaryBtn")
        btn_del_auth.clicked.connect(self._del_auth_row)
        auth_btn_layout.addWidget(btn_add_auth)
        auth_btn_layout.addWidget(btn_del_auth)
        auth_btn_layout.addStretch()
        auth_vbox.addLayout(auth_btn_layout)

        tabs.addTab(tab_auth, "Site Logins")

        # ==========================================
        # Tab 5: Proxy / SOCKS
        # ==========================================
        tab_proxy = QWidget()
        prx_vbox = QVBoxLayout(tab_proxy)
        
        grp_prx = QGroupBox("Proxy Configuration")
        p_grid = QGridLayout(grp_prx)
        self.chk_use_proxy = QCheckBox("Use Proxy Server")
        p_grid.addWidget(self.chk_use_proxy, 0, 0, 1, 2)

        p_grid.addWidget(QLabel("Proxy Protocol:"), 1, 0)
        self.cmb_proxy_proto = QComboBox()
        self.cmb_proxy_proto.addItems(["HTTP", "HTTPS", "SOCKS5"])
        p_grid.addWidget(self.cmb_proxy_proto, 1, 1)

        p_grid.addWidget(QLabel("Proxy Host / IP:"), 2, 0)
        self.txt_proxy_host = QLineEdit()
        p_grid.addWidget(self.txt_proxy_host, 2, 1)

        p_grid.addWidget(QLabel("Port:"), 3, 0)
        self.spin_proxy_port = QSpinBox()
        self.spin_proxy_port.setRange(1, 65535)
        self.spin_proxy_port.setValue(8080)
        p_grid.addWidget(self.spin_proxy_port, 3, 1)

        prx_vbox.addWidget(grp_prx)
        prx_vbox.addStretch()

        tabs.addTab(tab_proxy, "Proxy / Socks")

        # ==========================================
        # Tab 6: Browser Integration
        # ==========================================
        tab_br = QWidget()
        br_vbox = QVBoxLayout(tab_br)
        grp_br = QGroupBox("Browser Extension Integration")
        br_inner = QVBoxLayout(grp_br)
        br_inner.addWidget(QLabel(
            "<b>P-Downloader Integration Module</b> hooks directly into Chrome, Edge, Brave, and Firefox.<br>"
            "It captures video streaming, media links, and browser downloads automatically."
        ))
        btn_inst_host = QPushButton("Register Native Host in Windows Registry")
        btn_inst_host.clicked.connect(self._register_native_host)
        br_inner.addWidget(btn_inst_host)
        br_vbox.addWidget(grp_br)
        br_vbox.addStretch()

        tabs.addTab(tab_br, "Browser")

        # ==========================================
        # Tab 7: Multi-Network Bonding (Plexo)
        # ==========================================
        tab_bonding = QWidget()
        bonding_vbox = QVBoxLayout(tab_bonding)
        bonding_vbox.setSpacing(10)

        grp_bond = QGroupBox("Multi-Network Adapter Bandwidth Aggregation")
        b_layout = QVBoxLayout(grp_bond)
        self.chk_bonding = QCheckBox("Enable Multi-Network Adapter Bonding (Aggregate Bandwidth)")
        self.chk_bonding.setChecked(True)
        b_layout.addWidget(self.chk_bonding)

        lbl_desc = QLabel(
            "Download segments simultaneously across all active network connections "
            "(e.g., Home Wi-Fi + Mobile 5G Hotspot + Ethernet) to achieve combined download speeds."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        b_layout.addWidget(lbl_desc)

        self.table_adapters = QTableWidget()
        self.table_adapters.setColumnCount(4)
        self.table_adapters.setHorizontalHeaderLabels(["Interface Name", "IP Address", "Status", "Bonding Active"])
        self.table_adapters.horizontalHeader().setStretchLastSection(True)
        b_layout.addWidget(self.table_adapters)

        btn_refresh_adapters = QPushButton("🔄 Scan & Refresh Network Adapters")
        btn_refresh_adapters.setObjectName("secondaryBtn")
        btn_refresh_adapters.clicked.connect(self._refresh_adapters_table)
        b_layout.addWidget(btn_refresh_adapters)

        bonding_vbox.addWidget(grp_bond)
        bonding_vbox.addStretch()
        tabs.addTab(tab_bonding, "Network Bonding")

        # ==========================================
        # Tab 8: Sounds & Notifications
        # ==========================================
        tab_sounds = QWidget()
        snd_vbox = QVBoxLayout(tab_sounds)
        grp_snd = QGroupBox("Sound & Desktop Notifications")
        s_layout = QVBoxLayout(grp_snd)

        self.chk_sound_finish = QCheckBox("Play notification chime when a download completes")
        self.chk_sound_finish.setChecked(True)
        s_layout.addWidget(self.chk_sound_finish)

        self.chk_toast_finish = QCheckBox("Display Windows system notification banner on completion")
        self.chk_toast_finish.setChecked(True)
        s_layout.addWidget(self.chk_toast_finish)

        snd_vbox.addWidget(grp_snd)
        snd_vbox.addStretch()
        tabs.addTab(tab_sounds, "Sounds")

        main_layout.addWidget(tabs)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save Settings")
        btn_save.clicked.connect(self._save_settings)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondaryBtn")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        main_layout.addLayout(btn_layout)

    def _load_settings(self):
        # General
        self.chk_startup.setChecked(self.db.get_setting("auto_startup", "0") == "1")
        self.chk_clipboard.setChecked(self.db.get_setting("clipboard_monitor", "1") == "1")
        self.chk_show_dlg.setChecked(self.db.get_setting("show_dlg", "1") == "1")
        self.chk_tray.setChecked(self.db.get_setting("minimize_tray", "1") == "1")
        self.chk_av.setChecked(self.db.get_setting("antivirus_enabled", "1") == "1")
        self.txt_file_types.setText(self.db.get_setting("auto_file_types", DEFAULT_AUTO_FILE_TYPES))
        self.txt_exceptions.setText(self.db.get_setting("exception_sites", ""))

        # Save To
        self.txt_def_dir.setText(self.db.get_setting("default_dir", DEFAULT_DOWNLOADS_DIR))
        self.txt_temp_dir.setText(self.db.get_setting("temp_dir", os.path.join(DEFAULT_DOWNLOADS_DIR, "Temp")))
        for cat, txt in self.cat_inputs.items():
            txt.setText(self.db.get_setting(f"dir_{cat}", os.path.join(DEFAULT_DOWNLOADS_DIR, cat)))

        # Connection
        self.cmb_max_conns.setCurrentText(self.db.get_setting("default_connections", "8"))
        self.spin_simultaneous.setValue(int(self.db.get_setting("simultaneous_downloads", "2")))
        self.spin_timeout.setValue(int(self.db.get_setting("timeout", "15")))
        self.chk_speed_limit.setChecked(self.db.get_setting("limit_speed_enabled", "0") == "1")
        self.spin_speed_limit.setValue(int(self.db.get_setting("speed_limit_kb", "1024")))

        # Proxy
        self.chk_use_proxy.setChecked(self.db.get_setting("use_proxy", "0") == "1")
        self.cmb_proxy_proto.setCurrentText(self.db.get_setting("proxy_proto", "HTTP"))
        self.txt_proxy_host.setText(self.db.get_setting("proxy_host", ""))
        self.spin_proxy_port.setValue(int(self.db.get_setting("proxy_port", "8080")))

        # Bonding & Sounds
        self.chk_bonding.setChecked(self.db.get_setting("network_bonding", "1") == "1")
        self.chk_sound_finish.setChecked(self.db.get_setting("sound_on_finish", "1") == "1")
        self.chk_toast_finish.setChecked(self.db.get_setting("toast_on_finish", "1") == "1")
        self._refresh_adapters_table()

    def _refresh_adapters_table(self):
        nm = NetworkManager()
        adapters = nm.refresh_interfaces()
        self.table_adapters.setRowCount(len(adapters))
        for row, iface in enumerate(adapters):
            self.table_adapters.setItem(row, 0, QTableWidgetItem(iface.alias))
            self.table_adapters.setItem(row, 1, QTableWidgetItem(iface.ip))
            role = "Default Gateway" if iface.is_default else "Secondary / Tethering"
            self.table_adapters.setItem(row, 2, QTableWidgetItem(role))
            status = "Active & Bonded" if iface.enabled else "Disabled"
            self.table_adapters.setItem(row, 3, QTableWidgetItem(status))

    def _save_settings(self):
        # General
        self.db.set_setting("auto_startup", "1" if self.chk_startup.isChecked() else "0")
        self.db.set_setting("clipboard_monitor", "1" if self.chk_clipboard.isChecked() else "0")
        self.db.set_setting("show_dlg", "1" if self.chk_show_dlg.isChecked() else "0")
        self.db.set_setting("minimize_tray", "1" if self.chk_tray.isChecked() else "0")
        self.db.set_setting("antivirus_enabled", "1" if self.chk_av.isChecked() else "0")
        self.db.set_setting("auto_file_types", self.txt_file_types.text().strip())
        self.db.set_setting("exception_sites", self.txt_exceptions.text().strip())

        # Save To
        self.db.set_setting("default_dir", self.txt_def_dir.text().strip())
        self.db.set_setting("temp_dir", self.txt_temp_dir.text().strip())
        for cat, txt in self.cat_inputs.items():
            self.db.set_setting(f"dir_{cat}", txt.text().strip())

        # Connection
        self.db.set_setting("default_connections", self.cmb_max_conns.currentText())
        self.db.set_setting("simultaneous_downloads", str(self.spin_simultaneous.value()))
        self.db.set_setting("timeout", str(self.spin_timeout.value()))
        self.db.set_setting("limit_speed_enabled", "1" if self.chk_speed_limit.isChecked() else "0")
        self.db.set_setting("speed_limit_kb", str(self.spin_speed_limit.value()))

        # Proxy
        self.db.set_setting("use_proxy", "1" if self.chk_use_proxy.isChecked() else "0")
        self.db.set_setting("proxy_proto", self.cmb_proxy_proto.currentText())
        self.db.set_setting("proxy_host", self.txt_proxy_host.text().strip())
        self.db.set_setting("proxy_port", str(self.spin_proxy_port.value()))

        # Bonding & Sounds
        self.db.set_setting("network_bonding", "1" if self.chk_bonding.isChecked() else "0")
        self.db.set_setting("sound_on_finish", "1" if self.chk_sound_finish.isChecked() else "0")
        self.db.set_setting("toast_on_finish", "1" if self.chk_toast_finish.isChecked() else "0")

        # Update NetworkManager singleton
        nm = NetworkManager()
        nm.bonding_enabled = self.chk_bonding.isChecked()

        self.accept()

    def _browse_dir(self, line_edit: QLineEdit):
        path = QFileDialog.getExistingDirectory(self, "Select Folder", line_edit.text())
        if path:
            line_edit.setText(path)

    def _add_auth_row(self):
        r = self.table_auth.rowCount()
        self.table_auth.insertRow(r)
        self.table_auth.setItem(r, 0, QTableWidgetItem("example.com"))
        self.table_auth.setItem(r, 1, QTableWidgetItem("admin"))
        self.table_auth.setItem(r, 2, QTableWidgetItem("password"))

    def _del_auth_row(self):
        curr = self.table_auth.currentRow()
        if curr >= 0:
            self.table_auth.removeRow(curr)

    def _register_native_host(self):
        from browser_extension.installer import install_native_manifest
        try:
            install_native_manifest()
            QMessageBox.information(self, "Success", "Browser native host registered successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to register native host: {e}")
