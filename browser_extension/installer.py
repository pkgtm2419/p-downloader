"""
Installer script for P-Downloader Native Messaging Host.
Registers the host for Chrome, Edge, Brave, and Firefox across Windows, Linux, and macOS.
"""
import os
import sys
import json
import stat
from pathlib import Path
from typing import List, Dict

try:
    import winreg
except ImportError:
    winreg = None

HOST_NAME = "com.pdownloader.host"

WINDOWS_BROWSERS = {
    "chrome": {
        "name": "Google Chrome",
        "reg_path": rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}",
        "check_paths": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
    },
    "edge": {
        "name": "Microsoft Edge",
        "reg_path": rf"Software\Microsoft\Edge\NativeMessagingHosts\{HOST_NAME}",
        "check_paths": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        ]
    },
    "brave": {
        "name": "Brave Browser",
        "reg_path": rf"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\{HOST_NAME}",
        "check_paths": [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe")
        ]
    },
    "firefox": {
        "name": "Mozilla Firefox",
        "reg_path": rf"Software\Mozilla\NativeMessagingHosts\{HOST_NAME}",
        "check_paths": [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
        ]
    }
}

LINUX_MANIFEST_DIRS = [
    Path.home() / ".config" / "google-chrome" / "NativeMessagingHosts",
    Path.home() / ".config" / "chromium" / "NativeMessagingHosts",
    Path.home() / ".config" / "BraveSoftware" / "Brave-Browser" / "NativeMessagingHosts",
    Path.home() / ".config" / "microsoft-edge" / "NativeMessagingHosts",
    Path.home() / ".mozilla" / "native-messaging-hosts",
]

MACOS_MANIFEST_DIRS = [
    Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "NativeMessagingHosts",
    Path.home() / "Library" / "Application Support" / "Chromium" / "NativeMessagingHosts",
    Path.home() / "Library" / "Application Support" / "BraveSoftware" / "Brave-Browser" / "NativeMessagingHosts",
    Path.home() / "Library" / "Application Support" / "Microsoft Edge" / "NativeMessagingHosts",
    Path.home() / "Library" / "Application Support" / "Mozilla" / "NativeMessagingHosts",
]


def detect_installed_browsers() -> Dict[str, Dict]:
    detected = {}
    if sys.platform == "win32" and winreg:
        for key, info in WINDOWS_BROWSERS.items():
            installed = False
            for p in info["check_paths"]:
                if os.path.exists(p):
                    installed = True
                    break
            if not installed:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Clients\StartMenuInternet\{key.upper()}.EXE"):
                        installed = True
                except Exception:
                    pass
            if installed or key in ("chrome", "edge"):
                detected[key] = info
    else:
        # Linux / macOS
        detected = {
            "chrome": {"name": "Google Chrome / Chromium"},
            "brave": {"name": "Brave Browser"},
            "edge": {"name": "Microsoft Edge"},
            "firefox": {"name": "Mozilla Firefox"}
        }
    return detected


def install_native_manifest(selected_browsers: List[str] = None):
    project_root = Path(__file__).parent.parent
    manifest_dir = Path.home() / ".pdownloader"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = manifest_dir / f"{HOST_NAME}.json"

    # Identify executable or wrapper script
    is_win = (sys.platform == "win32")
    launcher_path = manifest_dir / ("pdownloader_host.bat" if is_win else "pdownloader_host.sh")

    app_dir = Path(sys.executable).parent
    p_exe = app_dir / ("P-Downloader.exe" if is_win else "P-Downloader")
    if not p_exe.exists():
        p_exe = project_root / "dist" / "P-Downloader" / ("P-Downloader.exe" if is_win else "P-Downloader")

    if is_win:
        if p_exe.exists():
            with open(launcher_path, "w", encoding="utf-8") as f:
                f.write(f'@echo off\n"{p_exe}" --native-host\n')
        else:
            python_exe = sys.executable
            script_path = str(Path(__file__).parent / "pdownloader_native_host.py")
            with open(launcher_path, "w", encoding="utf-8") as f:
                f.write(f'@echo off\n"{python_exe}" "{script_path}"\n')
    else:
        python_exe = sys.executable
        script_path = str(Path(__file__).parent / "pdownloader_native_host.py")
        with open(launcher_path, "w", encoding="utf-8") as f:
            f.write(f'#!/bin/bash\nexec "{python_exe}" "{script_path}" "$@"\n')
        # Make script executable
        current_stat = os.stat(launcher_path)
        os.chmod(launcher_path, current_stat.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    manifest_data = {
        "name": HOST_NAME,
        "description": "P-Downloader Ultra Native Messaging Host",
        "path": str(launcher_path),
        "type": "stdio",
        "allowed_origins": [
            "chrome-extension://*/"
        ],
        "allowed_extensions": [
            "pdownloader@ultra.download"
        ]
    }

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    # Register in Windows Registry
    if is_win and winreg:
        browsers_to_reg = selected_browsers if selected_browsers else list(WINDOWS_BROWSERS.keys())
        for b_key in browsers_to_reg:
            if b_key in WINDOWS_BROWSERS:
                reg_path = WINDOWS_BROWSERS[b_key]["reg_path"]
                try:
                    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(manifest_file))
                    winreg.CloseKey(key)
                except Exception as e:
                    print(f"Warning: Could not register in {reg_path}: {e}")
    else:
        # Register on Linux / macOS via file copy into browser target directories
        target_dirs = MACOS_MANIFEST_DIRS if sys.platform == "darwin" else LINUX_MANIFEST_DIRS
        for target_dir in target_dirs:
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                dest = target_dir / f"{HOST_NAME}.json"
                with open(dest, "w", encoding="utf-8") as f:
                    json.dump(manifest_data, f, indent=2)
                print(f"Registered native manifest at: {dest}")
            except Exception as e:
                # Browser might not be installed; ignore non-existent browser dirs
                pass

    return str(manifest_file)


if __name__ == "__main__":
    installed_path = install_native_manifest()
    print(f"Native host registered successfully: {installed_path}")
