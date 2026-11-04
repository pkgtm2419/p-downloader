"""
Browser Extension Creation & Integration Manager for P-Downloader.
Allows users to package/export the browser extension, register native messaging hosts,
and easily load the extension into Chrome, Edge, Brave, and Firefox.
"""
import os
import sys
import shutil
import zipfile
import subprocess
from typing import Dict, Any, List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFrame, QCheckBox, QMessageBox, QFileDialog,
    QProgressBar, QApplication
)
from PyQt6.QtGui import QIcon, QFont, QPixmap
from PyQt6.QtCore import Qt

from browser_extension.installer import detect_installed_browsers, install_native_manifest
from .icons import get_icon, COLOR_SLATE, COLOR_WHITE

RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources"))
EXTENSION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "browser_extension"))


class ExtensionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("P-Downloader - Browser Extension & Integration Manager")
        self.resize(580, 500)
        self.setMinimumSize(520, 440)

        icon_path = os.path.join(RESOURCES_DIR, "logo.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(18, 18, 18, 18)

        # Header
        header = QHBoxLayout()
        header.setSpacing(12)
        icon_lbl = QLabel()
        logo_png = os.path.join(RESOURCES_DIR, "logo.png")
        if os.path.exists(logo_png):
            pix = QPixmap(logo_png).scaled(42, 42, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_lbl.setPixmap(pix)
        header.addWidget(icon_lbl)

        txt_vbox = QVBoxLayout()
        txt_vbox.setSpacing(2)
        h1 = QLabel("<b>Browser Extension & Integration</b>")
        h1.setStyleSheet("font-size: 15px; color: #38bdf8;")
        h2 = QLabel("Intercept downloads and sniff in-page streaming video directly from your browser.")
        h2.setStyleSheet("font-size: 12px; color: #94a3b8;")
        txt_vbox.addWidget(h1)
        txt_vbox.addWidget(h2)
        header.addLayout(txt_vbox)
        header.addStretch()
        main_layout.addLayout(header)

        # 1. Native Messaging Host Registration Group
        grp_host = QGroupBox("1. Native Messaging Host (Desktop Bridge)")
        host_layout = QVBoxLayout(grp_host)
        host_layout.setSpacing(8)

        desc_host = QLabel(
            "Registers the secure desktop bridge in the Windows registry so browsers can communicate "
            "directly with P-Downloader at maximum speed."
        )
        desc_host.setWordWrap(True)
        desc_host.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        host_layout.addWidget(desc_host)

        self.browser_boxes = {}
        detected = detect_installed_browsers()
        for key in ["chrome", "edge", "brave", "firefox"]:
            is_inst = key in detected
            name = detected[key]["name"] if is_inst else key.capitalize()
            chk = QCheckBox(f"{name} {'(Detected)' if is_inst else '(Not Installed)'}")
            chk.setChecked(is_inst)
            self.browser_boxes[key] = chk
            host_layout.addWidget(chk)

        btn_install_host = QPushButton("Register / Re-Install Native Host")
        btn_install_host.setIcon(get_icon("globe", COLOR_WHITE, 16))
        btn_install_host.clicked.connect(self._install_host)
        host_layout.addWidget(btn_install_host)

        main_layout.addWidget(grp_host)

        # 2. Package / Create Extension Group
        grp_package = QGroupBox("2. Extension Creation & Package Export")
        pkg_layout = QVBoxLayout(grp_package)
        pkg_layout.setSpacing(8)

        desc_pkg = QLabel(
            "Package the browser extension into a production-ready ZIP archive for manual loading, "
            "sharing, or publishing to the Chrome Web Store / Firefox Addons."
        )
        desc_pkg.setWordWrap(True)
        desc_pkg.setStyleSheet("color: #64748B; font-size: 11px;")
        pkg_layout.addWidget(desc_pkg)

        pkg_btn_bar = QHBoxLayout()
        btn_build_zip = QPushButton("Export Extension Package (.zip)...")
        btn_build_zip.setIcon(get_icon("archive", COLOR_WHITE, 16))
        btn_build_zip.clicked.connect(self._create_extension_zip)
        pkg_btn_bar.addWidget(btn_build_zip)

        btn_open_folder = QPushButton("Open Extension Folder")
        btn_open_folder.setObjectName("secondaryBtn")
        btn_open_folder.setIcon(get_icon("folder", COLOR_SLATE, 16))
        btn_open_folder.clicked.connect(self._open_extension_dir)
        pkg_btn_bar.addWidget(btn_open_folder)

        pkg_layout.addLayout(pkg_btn_bar)
        main_layout.addWidget(grp_package)

        # 3. How to load guide
        guide_box = QFrame()
        guide_box.setObjectName("card")
        g_layout = QVBoxLayout(guide_box)
        g_layout.setContentsMargins(10, 8, 10, 8)
        guide_lbl = QLabel(
            "<b>Quick Installation Steps:</b><br>"
            "1. Open <b>chrome://extensions</b> or <b>edge://extensions</b> in your browser.<br>"
            "2. Turn ON <b>Developer mode</b> toggle in the top-right corner.<br>"
            "3. Click <b>Load unpacked</b> and select the extension folder above.<br>"
            "4. The P-Downloader icon will appear in your browser toolbar!"
        )
        guide_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; line-height: 1.4;")
        g_layout.addWidget(guide_lbl)
        main_layout.addWidget(guide_box)

        # Bottom close button
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_bar.addWidget(btn_close)
        main_layout.addLayout(btn_bar)

    def _install_host(self):
        selected = [k for k, chk in self.browser_boxes.items() if chk.isChecked()]
        if not selected:
            QMessageBox.warning(self, "No Browser Selected", "Please select at least one browser.")
            return

        try:
            results = install_native_manifest(selected)
            successes = [r.browser for r in results if r.success]
            if successes:
                QMessageBox.information(
                    self,
                    "Registration Successful",
                    f"Successfully registered native messaging bridge for: {', '.join(successes)}!\n\n"
                    "Restart your browser if it was already open."
                )
            else:
                QMessageBox.critical(self, "Registration Error", "Failed to register native host for selected browsers.")
        except Exception as e:
            QMessageBox.critical(self, "Registration Exception", f"Error during registration: {e}")

    def _create_extension_zip(self):
        default_name = "pdownloader-browser-extension.zip"
        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Extension Package",
            os.path.join(os.path.expanduser("~/Downloads"), default_name),
            "ZIP Files (*.zip)"
        )
        if not target_path:
            return

        try:
            with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as z:
                for root, dirs, files in os.walk(EXTENSION_DIR):
                    for f in files:
                        full_p = os.path.join(root, f)
                        rel_p = os.path.relpath(full_p, EXTENSION_DIR)
                        # Exclude cache or temp files
                        if "__pycache__" in rel_p or rel_p.endswith((".pyc", ".tmp")):
                            continue
                        z.write(full_p, rel_p)

            QMessageBox.information(
                self,
                "Extension Created",
                f"Successfully exported browser extension package to:\n{target_path}\n\n"
                f"Size: {os.path.getsize(target_path):,} bytes"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not create extension package: {e}")

    def _open_extension_dir(self):
        try:
            if sys.platform == "win32":
                os.startfile(EXTENSION_DIR)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", EXTENSION_DIR])
            else:
                subprocess.Popen(["xdg-open", EXTENSION_DIR])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open directory: {e}")

