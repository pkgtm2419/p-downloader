"""
Installer script for P-Downloader Native Messaging Host.
Registers the host in the Windows Registry for Chrome, Edge, and Chromium browsers.
"""
import os
import sys
import json
import winreg
from pathlib import Path

HOST_NAME = "com.pdownloader.host"

def install_native_manifest():
    python_exe = sys.executable
    script_path = str(Path(__file__).parent / "pdownloader_native_host.py")
    manifest_dir = Path.home() / ".pdownloader"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = manifest_dir / "com.pdownloader.host.json"

    # Wrapper batch file for Windows native messaging
    bat_file = manifest_dir / "pdownloader_host.bat"
    with open(bat_file, "w") as f:
        f.write(f'@echo off\n"{python_exe}" "{script_path}"\n')

    manifest_data = {
        "name": HOST_NAME,
        "description": "P-Downloader Native Messaging Host",
        "path": str(bat_file),
        "type": "stdio",
        "allowed_origins": [
            "chrome-extension://*/"
        ]
    }

    with open(manifest_file, "w") as f:
        json.dump(manifest_data, f, indent=2)

    # Register in Windows Registry for Chrome and Edge
    reg_paths = [
        rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}",
        rf"Software\Microsoft\Edge\NativeMessagingHosts\{HOST_NAME}"
    ]

    for reg_path in reg_paths:
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(manifest_file))
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Warning: Could not register in {reg_path}: {e}")

    print(f"Native host registered successfully at {manifest_file}")
    return str(manifest_file)

if __name__ == "__main__":
    install_native_manifest()
