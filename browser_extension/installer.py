"""
Installer script for P-Downloader Native Messaging Host.
Registers the host in the Windows Registry for Chrome, Edge, Brave, and Firefox.
"""
import os
import sys
import json
import winreg
from pathlib import Path
from typing import List, Dict

HOST_NAME = "com.pdownloader.host"

BROWSERS = {
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

def detect_installed_browsers() -> Dict[str, Dict]:
    detected = {}
    for key, info in BROWSERS.items():
        installed = False
        for p in info["check_paths"]:
            if os.path.exists(p):
                installed = True
                break
        # Also check registry
        if not installed:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Clients\StartMenuInternet\{key.upper()}.EXE"):
                    installed = True
            except Exception:
                pass
        if installed or key in ("chrome", "edge"):  # Edge is always present on modern Windows
            detected[key] = info
    return detected

def install_native_manifest(selected_browsers: List[str] = None):
    project_root = Path(__file__).parent.parent
    manifest_dir = Path.home() / ".pdownloader"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = manifest_dir / "com.pdownloader.host.json"

    # Find P-Downloader executable or fallback to python script
    app_dir = Path(sys.executable).parent
    p_exe = app_dir / "P-Downloader.exe"
    if not p_exe.exists():
        p_exe = project_root / "dist" / "P-Downloader" / "P-Downloader.exe"

    bat_file = manifest_dir / "pdownloader_host.bat"
    if p_exe.exists():
        with open(bat_file, "w") as f:
            f.write(f'@echo off\n"{p_exe}" --native-host\n')
    else:
        python_exe = sys.executable
        script_path = str(Path(__file__).parent / "pdownloader_native_host.py")
        with open(bat_file, "w") as f:
            f.write(f'@echo off\n"{python_exe}" "{script_path}"\n')

    manifest_data = {
        "name": HOST_NAME,
        "description": "P-Downloader Ultra Native Messaging Host",
        "path": str(bat_file),
        "type": "stdio",
        "allowed_origins": [
            "chrome-extension://*/"
        ],
        "allowed_extensions": [
            "pdownloader@ultra.download"
        ]
    }

    with open(manifest_file, "w") as f:
        json.dump(manifest_data, f, indent=2)

    # Register in Windows Registry
    browsers_to_reg = selected_browsers if selected_browsers else list(BROWSERS.keys())
    for b_key in browsers_to_reg:
        if b_key in BROWSERS:
            reg_path = BROWSERS[b_key]["reg_path"]
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(manifest_file))
                winreg.CloseKey(key)
            except Exception as e:
                print(f"Warning: Could not register in {reg_path}: {e}")

    return str(manifest_file)

if __name__ == "__main__":
    install_native_manifest()
