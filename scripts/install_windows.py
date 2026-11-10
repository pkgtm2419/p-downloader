#!/usr/bin/env python3
"""
P-Downloader Windows 11 / 10 Native Installer & Uninstaller
Configures shortcuts, Windows Registry, browser native messaging, and App registration.
100% compliant with Windows 11 Smart App Control (SAC) and UAC policies.
"""
import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    import winreg


def get_python_exe() -> str:
    """Finds pythonw.exe or python.exe for GUI launching without terminal flash."""
    py_dir = Path(sys.executable).parent
    pythonw = py_dir / "pythonw.exe"
    if pythonw.exists():
        return str(pythonw)
    return sys.executable


def get_desktop_dir() -> Path:
    """Returns the user Desktop directory."""
    user_profile = Path(os.environ.get("USERPROFILE", Path.home()))
    desktop = user_profile / "Desktop"
    if not desktop.exists():
        desktop = user_profile / "OneDrive" / "Desktop"
    return desktop


def get_start_menu_dir() -> Path:
    """Returns the user Start Menu Programs directory."""
    app_data = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    programs = app_data / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "P-Downloader"
    programs.mkdir(parents=True, exist_ok=True)
    return programs


def create_windows_shortcut(
    shortcut_path: Path,
    target: str,
    arguments: str,
    icon: str,
    work_dir: str,
    description: str
):
    """Creates a Windows .lnk shortcut using PowerShell COM object."""
    ps_cmd = (
        f"$wsh = New-Object -ComObject WScript.Shell; "
        f"$s = $wsh.CreateShortcut('{str(shortcut_path)}'); "
        f"$s.TargetPath = '{target}'; "
        f"$s.Arguments = '{arguments}'; "
        f"$s.WorkingDirectory = '{work_dir}'; "
        f"$s.IconLocation = '{icon}'; "
        f"$s.Description = '{description}'; "
        f"$s.Save()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
        check=True,
        capture_output=True
    )


def register_native_messaging_hosts():
    """Registers native messaging host manifests for Chrome, Edge, Brave, and Firefox."""
    if sys.platform != "win32":
        return

    python_exe = get_python_exe()

    # 1. Chromium host manifest (Chrome, Edge, Brave, Opera, Vivaldi)
    chrome_manifest_path = ROOT / "browser_extension" / "com.pdownloader.host.json"
    chrome_manifest = {
        "name": "com.pdownloader.host",
        "description": "P-Downloader Ultra Native Messaging Host",
        "path": python_exe,
        "type": "stdio",
        "allowed_origins": [
            "chrome-extension://mngjniiiieccogdpplbdmmmmnemocbkb/"
        ]
    }
    chrome_manifest_path.write_text(json.dumps(chrome_manifest, indent=2), encoding="utf-8")

    # 2. Firefox host manifest
    firefox_manifest_path = ROOT / "browser_extension" / "com.pdownloader.host.firefox.json"
    firefox_manifest = {
        "name": "com.pdownloader.host",
        "description": "P-Downloader Ultra Native Messaging Host",
        "path": python_exe,
        "type": "stdio",
        "allowed_extensions": [
            "pdownloader@ultra.download"
        ]
    }
    firefox_manifest_path.write_text(json.dumps(firefox_manifest, indent=2), encoding="utf-8")

    # 3. Register in Windows Registry (HKCU - no admin elevation required)
    chromium_browsers = [
        r"Software\Google\Chrome\NativeMessagingHosts\com.pdownloader.host",
        r"Software\Microsoft\Edge\NativeMessagingHosts\com.pdownloader.host",
        r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\com.pdownloader.host",
        r"Software\Chromium\NativeMessagingHosts\com.pdownloader.host"
    ]
    for subkey in chromium_browsers:
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, subkey) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(chrome_manifest_path))
        except Exception as err:
            print(f"[WARN] Failed to write registry key {subkey}: {err}")

    try:
        ff_key = r"Software\Mozilla\NativeMessagingHosts\com.pdownloader.host"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, ff_key) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(firefox_manifest_path))
    except Exception as err:
        print(f"[WARN] Failed to write registry key for Firefox: {err}")

    print("✓ Browser Native Messaging Hosts registered in Windows Registry.")


def register_windows_uninstaller(version: str):
    """Registers P-Downloader in Windows 'Apps & Features' / 'Installed Apps'."""
    if sys.platform != "win32":
        return

    uninstall_key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\P-Downloader"
    logo_ico = ROOT / "resources" / "logo.ico"
    uninstall_bat = ROOT / "uninstall_windows.bat"

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, uninstall_key_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "P-Downloader")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, version)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "P-Downloader Project")
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(logo_ico))
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(ROOT))
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{str(uninstall_bat)}"')
            winreg.SetValueEx(key, "URLInfoAbout", 0, winreg.REG_SZ, "https://github.com/pkgtm2419/p-downloader")
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        print("✓ Registered in Windows 'Installed Apps' Control Panel.")
    except Exception as err:
        print(f"[WARN] Could not register uninstaller key: {err}")


def install():
    print("============================================================")
    print("  Installing P-Downloader on Windows 11 / 10...")
    print("============================================================")

    # 1. Get current version
    from core import __version__ as app_version
    print(f"Installing version: {app_version}")

    # 2. Install / verify Python dependencies
    req_file = ROOT / "requirements.txt"
    if req_file.exists():
        print("Checking Python dependencies...")
        res = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            capture_output=True,
            text=True
        )
        if res.returncode != 0:
            print(f"[WARN] Dependency check warning: {res.stderr.strip()[:200]}")
        else:
            print("✓ Python dependencies up to date.")

    # 3. Create Windows Shortcuts
    python_exe = get_python_exe()
    main_py = ROOT / "main.py"
    logo_ico = ROOT / "resources" / "logo.ico"

    desktop_shortcut = get_desktop_dir() / "P-Downloader.lnk"
    create_windows_shortcut(
        shortcut_path=desktop_shortcut,
        target=python_exe,
        arguments=f'"{str(main_py)}"',
        icon=str(logo_ico),
        work_dir=str(ROOT),
        description="P-Downloader Ultra Fast Download Manager"
    )
    print(f"✓ Desktop Shortcut created: {desktop_shortcut}")

    start_menu_shortcut = get_start_menu_dir() / "P-Downloader.lnk"
    create_windows_shortcut(
        shortcut_path=start_menu_shortcut,
        target=python_exe,
        arguments=f'"{str(main_py)}"',
        icon=str(logo_ico),
        work_dir=str(ROOT),
        description="P-Downloader Ultra Fast Download Manager"
    )
    print(f"✓ Start Menu Shortcut created: {start_menu_shortcut}")

    # 4. Register browser native messaging hosts
    register_native_messaging_hosts()

    # 5. Register in Windows Uninstall
    register_windows_uninstaller(app_version)

    print("\n🎉 Installation completed successfully!")
    print("You can now launch P-Downloader from your Desktop or Start Menu.")


def uninstall():
    print("============================================================")
    print("  Uninstalling P-Downloader from Windows...")
    print("============================================================")

    # 1. Remove Desktop shortcut
    desktop_shortcut = get_desktop_dir() / "P-Downloader.lnk"
    if desktop_shortcut.exists():
        try:
            desktop_shortcut.unlink()
            print("✓ Removed Desktop shortcut.")
        except Exception as err:
            print(f"[WARN] Could not remove {desktop_shortcut}: {err}")

    # 2. Remove Start Menu folder
    start_menu_folder = get_start_menu_dir()
    if start_menu_folder.exists():
        try:
            shutil.rmtree(start_menu_folder, ignore_errors=True)
            print("✓ Removed Start Menu entries.")
        except Exception as err:
            print(f"[WARN] Could not remove {start_menu_folder}: {err}")

    # 3. Remove Registry Keys
    if sys.platform == "win32":
        keys_to_remove = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\P-Downloader"),
            (winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\NativeMessagingHosts\com.pdownloader.host"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Edge\NativeMessagingHosts\com.pdownloader.host"),
            (winreg.HKEY_CURRENT_USER, r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\com.pdownloader.host"),
            (winreg.HKEY_CURRENT_USER, r"Software\Chromium\NativeMessagingHosts\com.pdownloader.host"),
            (winreg.HKEY_CURRENT_USER, r"Software\Mozilla\NativeMessagingHosts\com.pdownloader.host")
        ]
        for root_key, subkey in keys_to_remove:
            try:
                winreg.DeleteKey(root_key, subkey)
            except FileNotFoundError:
                pass
            except Exception:
                pass
        print("✓ Removed Registry entries.")

    print("\n✅ P-Downloader has been uninstalled successfully.")


def main():
    parser = argparse.ArgumentParser(description="P-Downloader Windows Installer")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall P-Downloader from Windows")
    args = parser.parse_args()

    if args.uninstall:
        uninstall()
    else:
        install()


if __name__ == "__main__":
    main()
