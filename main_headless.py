"""
P-Downloader Headless Server Daemon for NAS, Linux Servers, and Docker.
Runs the high-performance download engine, REST remote API, and IPC without X11 or PyQt6 dependencies.
"""
import os
import sys
import time
import signal
import argparse

from core.db import DownloadDB
from core.engine import DownloadEngine
from core.remote_server import RemoteServer
from core.ipc import LocalIPCServer


def main():
    parser = argparse.ArgumentParser(description="P-Downloader Headless Server Daemon")
    parser.add_argument("--port", type=int, default=8463, help="Web remote server port (default: 8463)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Web remote bind host (default: 0.0.0.0)")
    parser.add_argument("--tls", action="store_true", help="Enable self-signed HTTPS encryption")
    parser.add_argument("--ipc-port", type=int, default=54321, help="Local IPC control port (default: 54321)")
    args = parser.parse_args()

    print("==================================================")
    print("      P-Downloader Headless Daemon v1.1.0        ")
    print("==================================================")

    db = DownloadDB()
    engine = DownloadEngine(db)

    # Start Web Remote
    remote = RemoteServer(engine=engine, host=args.host, port=args.port, use_tls=args.tls)
    remote.start()
    protocol = "https" if args.tls else "http"
    print(f"[*] Web Remote running at {protocol}://{args.host}:{args.port}/")
    print(f"[*] Pairing PIN: {remote.pin}")

    # Start Local IPC Server
    ipc = LocalIPCServer(engine=engine, port=args.ipc_port)
    if ipc.start():
        print(f"[*] Local IPC Server active on port {args.ipc_port}")

    def shutdown(signum, frame):
        print("\n[*] Shutting down headless services...")
        remote.stop()
        ipc.stop()
        db.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    print("[*] Headless daemon initialized. Running background workers...")
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
