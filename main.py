"""
P-Downloader Main Entry Point.
Supports native desktop GUI mode and headless CLI acceleration mode.
"""
import sys
import os
import argparse
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

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

def run_gui(initial_url: str = ""):
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon
    from gui.main_window import MainWindow

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
    window.show()

    if initial_url:
        window.show_add_dialog(initial_url=initial_url)

    sys.exit(app.exec())

def main():
    parser = argparse.ArgumentParser(description="P-Downloader: High-speed multi-part download accelerator.")
    parser.add_argument("--url", type=str, help="Target URL to download")
    parser.add_argument("--connections", type=int, default=8, help="Number of parallel connections (1-32)")
    parser.add_argument("--output", type=str, help="Target file save path")
    parser.add_argument("--cli", action="store_true", help="Run in headless terminal/CLI mode")

    args = parser.parse_args()

    if args.cli and args.url:
        run_cli(args)
    else:
        run_gui(initial_url=args.url or "")

if __name__ == "__main__":
    main()
