"""
P-Downloader Main Entry Point.
Supports native desktop GUI mode, background tray execution,
single-instance IPC handover, and headless CLI acceleration mode.
"""
import sys
import os
import argparse
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core import __version__
from core.engine import DownloadEngine
from core.segment import DownloadTask
from gui.styles import format_bytes, format_speed

def run_cli(args):
    url = args.url
    connections = args.connections or 8
    output = args.output
    
    print("=" * 60)
    print("  P-Downloader (Pure Downloader) - CLI Engine")
    print(f"  Target URL: {url}")
    print(f"  Connections: {connections}")
    print("=" * 60)

    engine = DownloadEngine()
    task = engine.create_download(
        url=url,
        save_path=output,
        connections=connections,
        auto_start=True
    )

    print(f"File: {os.path.basename(task.save_path)}")
    print(f"Total Size: {format_bytes(task.total_bytes)}")
    print(f"Resume Support: {'Yes' if task.supports_range else 'No'}")
    print("-" * 60)

    done = False
    while not done:
        time.sleep(0.5)
        if task.status == "completed":
            print(f"\n[100%] Download finished successfully: {task.save_path}")
            done = True
        elif task.status == "error":
            print(f"\n[ERROR] Download failed: {task.error_message}")
            done = True
        else:
            pct = (task.downloaded_bytes / task.total_bytes * 100) if task.total_bytes > 0 else 0
            print(
                f"\r[{pct:5.1f}%] {format_bytes(task.downloaded_bytes)} of {format_bytes(task.total_bytes)} "
                f"at {format_speed(task.speed)} ({len(task.segments)} conns)",
                end="", flush=True
            )

def run_gui(initial_url: str = "", start_tray: bool = False):
    from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
    from PyQt6.QtGui import QIcon
    from PyQt6.QtCore import QTimer
    from gui.main_window import MainWindow
    from gui.integration_prompt_dialog import IntegrationPromptDialog
    from core.ipc import IPCServer

    app = QApplication(sys.argv)
    app.setApplicationName("P-Downloader")
    app.setOrganizationName("PDownloader")

    icon_path = os.path.join(os.path.dirname(__file__), "resources", "logo.ico")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(os.path.dirname(__file__), "resources", "logo.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    engine = DownloadEngine()
    window = MainWindow(engine)

    # IPC Server for handling single-instance requests from browser or subsequent launches
    def handle_ipc(msg: dict):
        action = msg.get("action")
        url = msg.get("url")
        if action in ("download", "add_download") and url:
            QTimer.singleShot(0, lambda u=url: window.show_add_dialog(initial_url=u))
        elif action == "restore":
            QTimer.singleShot(0, lambda: (window.showNormal(), window.activateWindow(), window.raise_()))

    ipc_server = IPCServer(handle_ipc)
    ipc_server.start()

    # First-run setup check
    if engine.db.get_setting("first_run_setup") != "1":
        dlg = IntegrationPromptDialog(engine.db, window)
        dlg.exec()

    if start_tray:
        window.hide()
        window.tray.showMessage(
            "P-Downloader Ultra",
            "Running in background system tray. Ready to capture browser downloads at ultra speed.",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )
    else:
        window.show()

    if initial_url:
        window.show_add_dialog(initial_url=initial_url)

    ret = app.exec()
    ipc_server.stop()
    sys.exit(ret)

def main():
    # Native messaging host mode (invoked by browser extension)
    if "--native-host" in sys.argv or any(arg.startswith("chrome-extension://") or arg.startswith("edge-extension://") for arg in sys.argv):
        from browser_extension.pdownloader_native_host import main as host_main
        host_main()
        return

    parser = argparse.ArgumentParser(description="P-Downloader: High-speed multi-part download accelerator.")
    parser.add_argument("--version", "-v", action="version", version=f"P-Downloader {__version__}")
    parser.add_argument("--url", type=str, help="Target URL to download")
    parser.add_argument("--connections", type=int, default=8, help="Number of parallel connections (1-32)")
    parser.add_argument("--output", type=str, help="Target file save path")
    parser.add_argument("--cli", action="store_true", help="Run in headless terminal/CLI mode")
    parser.add_argument("--tray", action="store_true", help="Start minimized in Windows system tray")
    parser.add_argument("--minimized", action="store_true", help="Start minimized in Windows system tray")

    args = parser.parse_args()

    if args.cli and args.url:
        run_cli(args)
        return

    # Check if instance is already running
    from core.ipc import send_to_running_instance
    if args.url:
        if send_to_running_instance({"action": "download", "url": args.url}):
            print("[IPC] Forwarded download to running P-Downloader instance.")
            sys.exit(0)
    elif not args.tray and not args.minimized:
        if send_to_running_instance({"action": "restore"}):
            print("[IPC] Restored running P-Downloader instance.")
            sys.exit(0)

    run_gui(initial_url=args.url or "", start_tray=args.tray or args.minimized)

if __name__ == "__main__":
    main()
