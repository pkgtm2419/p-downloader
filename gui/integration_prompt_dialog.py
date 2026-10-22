"""
First-Run & Browser Integration Setup Dialog for P-Downloader.
Prompts user to configure Windows startup, background system tray operation,
and registers browser integration for Chrome, Edge, Brave, and Firefox.
"""
import os
import winreg
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QPushButton, QGroupBox, QFrame, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont, QPixmap

from core.db import DownloadDB
from browser_extension.installer import detect_installed_browsers, install_native_manifest

RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources"))

def set_windows_startup(enabled: bool):
    """
    Enables or disables launch on Windows startup in HKCU Run registry.
    """
    reg_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "PDownloader"
    if getattr(sys, "frozen", False):
        exe_path = sys.executable
    else:
        exe_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "P-Downloader.exe"))
        if not os.path.exists(exe_path):
            dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dist", "P-Downloader", "P-Downloader.exe"))
            if os.path.exists(dist_path):
                exe_path = dist_path

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_key, 0, winreg.KEY_SET_VALUE)
        if enabled:
            cmd = f'"{exe_path}" --tray'
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass

class IntegrationPromptDialog(QDialog):
    def __init__(self, db: DownloadDB, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("P-Downloader - Quick Setup & Integration")
        self.resize(520, 420)

        icon_path = os.path.join(RESOURCES_DIR, "logo.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QDialog {
                background-color: #f8fafc;
                color: #0f172a;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                margin-top: 12px;
                padding-top: 16px;
                padding-bottom: 10px;
                color: #1e293b;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 4px;
                color: #059669;
            }
            QCheckBox {
                color: #334155;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #cbd5e1;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #10b981;
                border-color: #059669;
                image: none;
            }
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 9px 20px;
                font-weight: 600;
                font-size: 13px;
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
        """)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header Title
        title_box = QHBoxLayout()
        logo_lbl = QLabel()
        logo_png = os.path.join(RESOURCES_DIR, "logo.png")
        if os.path.exists(logo_png):
            pix = QPixmap(logo_png).scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        title_box.addWidget(logo_lbl)

        header_text = QVBoxLayout()
        h1 = QLabel("<b>Welcome to P-Downloader Ultra</b>")
        h1.setStyleSheet("font-size: 16px; color: #0f172a;")
        h2 = QLabel("Configure browser integration and background acceleration settings.")
        h2.setStyleSheet("font-size: 12px; color: #64748b;")
        header_text.addWidget(h1)
        header_text.addWidget(h2)
        title_box.addLayout(header_text)
        title_box.addStretch()
        layout.addLayout(title_box)

        # Background & Startup Group
        grp_system = QGroupBox("System && Background Operation")
        sys_layout = QVBoxLayout(grp_system)
        sys_layout.setSpacing(10)

        self.chk_startup = QCheckBox("Launch P-Downloader automatically on Windows startup")
        self.chk_startup.setChecked(self.db.get_setting("auto_startup", "1") == "1")
        sys_layout.addWidget(self.chk_startup)

        self.chk_tray = QCheckBox("Keep running in background system tray (for instant browser link catching)")
        self.chk_tray.setChecked(self.db.get_setting("minimize_tray", "1") == "1")
        sys_layout.addWidget(self.chk_tray)

        layout.addWidget(grp_system)

        # Browser Integration Group
        grp_browser = QGroupBox("Browser Extension Integration")
        br_layout = QVBoxLayout(grp_browser)
        br_layout.setSpacing(8)

        br_desc = QLabel(
            "When enabled, downloads started in your web browser will be automatically caught "
            "and accelerated with up to 32 parallel connections."
        )
        br_desc.setWordWrap(True)
        br_desc.setStyleSheet("color: #64748b; font-size: 12px; font-weight: normal;")
        br_layout.addWidget(br_desc)

        detected = detect_installed_browsers()
        self.browser_checkboxes = {}

        for key in ["chrome", "edge", "brave", "firefox"]:
            installed = key in detected
            name = detected[key]["name"] if installed else key.capitalize()
            label_text = f"Integrate with {name} {'(Detected)' if installed else ''}"
            chk = QCheckBox(label_text)
            chk.setChecked(installed)
            self.browser_checkboxes[key] = chk
            br_layout.addWidget(chk)

        layout.addWidget(grp_browser)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_later = QPushButton("Later", self)
        btn_later.setObjectName("secondaryBtn")
        btn_later.clicked.connect(self.reject)
        btn_layout.addWidget(btn_later)

        btn_apply = QPushButton("🚀 Apply && Start P-Downloader", self)
        btn_apply.clicked.connect(self._apply_settings)
        btn_layout.addWidget(btn_apply)

        layout.addLayout(btn_layout)

    def _apply_settings(self):
        # 1. Save system settings
        startup_val = "1" if self.chk_startup.isChecked() else "0"
        tray_val = "1" if self.chk_tray.isChecked() else "0"
        self.db.set_setting("auto_startup", startup_val)
        self.db.set_setting("minimize_tray", tray_val)
        self.db.set_setting("first_run_setup", "1")

        set_windows_startup(self.chk_startup.isChecked())

        # 2. Register native host for selected browsers
        selected = [k for k, chk in self.browser_checkboxes.items() if chk.isChecked()]
        if selected:
            try:
                install_native_manifest(selected)
            except Exception:
                pass

        self.accept()
