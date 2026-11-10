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

def run_gui(
    initial_url: str = "",
    initial_filename: str = "",
    initial_dir: str = "",
    start_now: bool = False,
    start_tray: bool = False
):
    from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
    from PyQt6.QtGui import QIcon, QFont
    from PyQt6.QtCore import QTimer
    from gui.main_window import MainWindow
    from gui.integration_prompt_dialog import IntegrationPromptDialog
    from core.ipc import IPCServer

    from gui.styles import MAIN_STYLESHEET
    app = QApplication(sys.argv)
    app.setApplicationName("P-Downloader")
    app.setOrganizationName("PDownloader")
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont('Segoe UI', 10))
    app.setStyleSheet(MAIN_STYLESHEET)

    icon_path = os.path.join(os.path.dirname(__file__), "resources", "logo.ico")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(os.path.dirname(__file__), "resources", "logo.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    engine = DownloadEngine()
    window = MainWindow(engine)

    from core.browser_handoff import HandoffStore
    from core.download_models import DownloadRequest, DownloadKind
    handoff_store = HandoffStore(engine.db.conn)

    # IPC Server for handling single-instance requests from browser or subsequent launches
    def handle_ipc(msg: dict):
        action = msg.get("action")
        url = msg.get("url")

        if action == "reserve" and url:
            req = DownloadRequest(
                url=url,
                filename=msg.get("filename"),
                destination=msg.get("destination"),
                kind=DownloadKind.HTTP
            )
            offer = handoff_store.reserve(req, capture_id=msg.get("captureId"))
            return {
                "ok": True,
                "state": offer.state,
                "handoffId": offer.handoff_id,
                "expiresAt": offer.expires_at_utc
            }

        elif action == "commit":
            handoff_id = msg.get("handoffId")
            if not handoff_id:
                return {"ok": False, "error": "MISSING_HANDOFF_ID"}
            task_id = handoff_store.commit(handoff_id, engine=engine)
            QTimer.singleShot(0, window._load_table_data)
            return {"ok": True, "state": "COMMITTED", "taskId": task_id}

        elif action == "release":
            handoff_id = msg.get("handoffId")
            if handoff_id:
                handoff_store.release(handoff_id)
            return {"ok": True, "state": "RELEASED"}

        elif action == "status":
            handoff_id = msg.get("handoffId")
            offer = handoff_store.get_status(handoff_id) if handoff_id else None
            if offer:
                return {"ok": True, "state": offer.state, "taskId": offer.task_id}
            return {"ok": False, "error": "NOT_FOUND"}

        elif action in ("download", "add_download") and url:
            fn = msg.get("filename", "")
            page_url = msg.get("pageUrl", "")
            quality = msg.get("quality", "")
            ref = msg.get("referer", "")
            hdrs = msg.get("requestHeaders") or {}
            start = msg.get("startNow", False) or msg.get("silent", False)
            QTimer.singleShot(0, lambda u=url, p=page_url, q=quality, f=fn, r=ref, h=hdrs, s=start: window.show_add_dialog(
                initial_url=u,
                page_url=p,
                quality=q,
                initial_filename=f,
                referer=r,
                headers=h,
                start_now=s
            ))
            return {"ok": True, "status": "queued"}

        elif action == "start_queue":
            QTimer.singleShot(0, lambda: engine.resume_all())
            return {"ok": True, "status": "started"}

        elif action == "restore":
            QTimer.singleShot(0, lambda: (window.showNormal(), window.activateWindow(), window.raise_()))
            return {"ok": True}

        return {"ok": False, "error": f"Unknown action: {action}"}

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
        window.show_add_dialog(
            initial_url=initial_url,
            initial_filename=initial_filename,
            start_now=start_now
        )

    ret = app.exec()
    ipc_server.stop()
    sys.exit(ret)


def normalize_idm_args(args_list: list) -> list:
    """
    Translates legacy IDM Windows-style CLI switches (/d, /p, /f, /q, /s, /n, /a, /h)
    into standard P-Downloader flags.
    """
    normalized = []
    i = 0
    while i < len(args_list):
        arg = args_list[i]
        lower_arg = arg.lower()
        if lower_arg in ("/d", "-d"):
            normalized.append("--url")
            if i + 1 < len(args_list):
                i += 1
                normalized.append(args_list[i])
        elif lower_arg in ("/p", "-p"):
            normalized.append("--output-dir")
            if i + 1 < len(args_list):
                i += 1
                normalized.append(args_list[i])
        elif lower_arg in ("/f", "-f"):
            normalized.append("--filename")
            if i + 1 < len(args_list):
                i += 1
                normalized.append(args_list[i])
        elif lower_arg in ("/n", "-n"):
            normalized.append("--silent")
        elif lower_arg in ("/q", "-q"):
            normalized.append("--quit-on-finish")
        elif lower_arg in ("/s", "-s"):
            normalized.append("--start-queue")
        elif lower_arg in ("/a", "-a"):
            normalized.append("--queue-only")
        elif lower_arg == "/h":
            normalized.append("--hangup")
        else:
            normalized.append(arg)
        i += 1
    return normalized


def main():
    # Native messaging host mode (invoked by browser extension)
    if "--native-host" in sys.argv or any(arg.startswith("chrome-extension://") or arg.startswith("edge-extension://") for arg in sys.argv):
        from browser_extension.pdownloader_native_host import main as host_main
        host_main()
        return

    raw_args = sys.argv[1:]
    processed_args = normalize_idm_args(raw_args)

    parser = argparse.ArgumentParser(description="P-Downloader: High-speed multi-part download accelerator.")
    parser.add_argument("--version", "-v", action="version", version=f"P-Downloader {__version__}")
    parser.add_argument("--url", type=str, help="Target URL to download (or IDM /d)")
    parser.add_argument("--connections", type=int, default=8, help="Number of parallel connections (1-32)")
    parser.add_argument("--output", type=str, help="Target file save path")
    parser.add_argument("--output-dir", type=str, help="Directory to save file (or IDM /p)")
    parser.add_argument("--filename", type=str, help="Local file name (or IDM /f)")
    parser.add_argument("--silent", action="store_true", help="Silent mode without add dialog (or IDM /n)")
    parser.add_argument("--queue-only", action="store_true", help="Add to queue without starting immediately (or IDM /a)")
    parser.add_argument("--start-queue", action="store_true", help="Start the download queue (or IDM /s)")
    parser.add_argument("--quit-on-finish", action="store_true", help="Quit application after download finishes (or IDM /q)")
    parser.add_argument("--hangup", action="store_true", help="Hang up / disconnect network after finish (or IDM /h)")
    parser.add_argument("--cli", action="store_true", help="Run in headless terminal/CLI mode")
    parser.add_argument("--tray", action="store_true", help="Start minimized in Windows system tray")
    parser.add_argument("--minimized", action="store_true", help="Start minimized in Windows system tray")
    parser.add_argument("--headless", "--server", action="store_true", help="Run headless background daemon with web remote and local IPC")
    parser.add_argument("--port", type=int, default=8463, help="Web remote server port for headless mode (default: 8463)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Web remote bind host for headless mode (default: 0.0.0.0)")
    parser.add_argument("--tls", action="store_true", help="Enable HTTPS TLS for web remote")

    args = parser.parse_args(processed_args)

    if args.headless:
        from main_headless import main as headless_main
        sys.argv = [sys.argv[0]]
        if args.port:
            sys.argv.extend(["--port", str(args.port)])
        if args.host:
            sys.argv.extend(["--host", str(args.host)])
        if args.tls:
            sys.argv.append("--tls")
        headless_main()
        return

    if args.cli and args.url:
        run_cli(args)
        return

    # Check if instance is already running
    from core.ipc import send_to_running_instance
    if args.url:
        start_now = not args.queue_only
        msg = {
            "action": "download",
            "url": args.url,
            "filename": args.filename,
            "destination": args.output_dir or args.output,
            "startNow": start_now,
            "silent": args.silent
        }
        if send_to_running_instance(msg):
            print("[IPC] Forwarded download to running P-Downloader instance.")
            sys.exit(0)
    elif args.start_queue:
        if send_to_running_instance({"action": "start_queue"}):
            print("[IPC] Forwarded start_queue to running P-Downloader instance.")
            sys.exit(0)
    elif not args.tray and not args.minimized:
        if send_to_running_instance({"action": "restore"}):
            print("[IPC] Restored running P-Downloader instance.")
            sys.exit(0)

    start_now = (not args.queue_only) and args.silent
    run_gui(
        initial_url=args.url or "",
        initial_filename=args.filename or "",
        initial_dir=args.output_dir or "",
        start_now=start_now,
        start_tray=args.tray or args.minimized
    )

if __name__ == "__main__":
    main()
