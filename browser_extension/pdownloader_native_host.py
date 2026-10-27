"""
Native Messaging Host for P-Downloader.
Communicates with Chrome / Edge / Brave / Firefox WebExtensions via stdin/stdout binary framing.
"""
import sys
import json
import struct
import os
import subprocess
from pathlib import Path

# Set binary mode on Windows to prevent CRLF line-ending translation
if sys.platform == "win32":
    try:
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    except Exception:
        pass

LOG_FILE = Path.home() / ".pdownloader" / "native_host.log"

def log_debug(msg: str):
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    except Exception:
        pass

def send_message(message: dict):
    try:
        raw_json = json.dumps(message).encode('utf-8')
        sys.stdout.buffer.write(struct.pack('@I', len(raw_json)))
        sys.stdout.buffer.write(raw_json)
        sys.stdout.buffer.flush()
        log_debug(f"[SENT] {message}")
    except Exception as e:
        log_debug(f"[ERROR SENDING] {e}")

def read_bytes(count: int) -> bytes:
    data = bytearray()
    while len(data) < count:
        try:
            chunk = sys.stdin.buffer.read(count - len(data))
        except Exception as e:
            log_debug(f"[READ EXCEPTION] {e}")
            break
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)

def read_message() -> dict:
    raw_length = read_bytes(4)
    if len(raw_length) < 4:
        return {}
    length = struct.unpack('@I', raw_length)[0]
    raw_data = read_bytes(length)
    if len(raw_data) < length:
        return {}
    msg = json.loads(raw_data.decode('utf-8'))
    log_debug(f"[RECEIVED] {msg}")
    return msg

def main():
    log_debug("--- P-Downloader Native Host Started ---")
    project_root = str(Path(__file__).parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    try:
        from core.ipc import send_to_running_instance
    except Exception as e:
        log_debug(f"[IPC IMPORT ERROR] {e}")
        send_to_running_instance = None

    while True:
        try:
            msg = read_message()
            if not msg:
                break

            action = msg.get("action")
            url = msg.get("url")
            filename = msg.get("filename", "")
            referer = msg.get("referer", "")

            if action == "download" and url:
                delivered = False
                payload = {"action": "download", "url": url, "filename": filename, "referer": referer}
                if send_to_running_instance:
                    delivered = send_to_running_instance(payload)

                if not delivered:
                    # Launch P-Downloader in background tray mode with the URL
                    exe_same_dir = Path(sys.executable).parent / "P-Downloader.exe"
                    exe_candidate = Path(project_root) / "P-Downloader.exe"
                    dist_candidate = Path(project_root) / "dist" / "P-Downloader" / "P-Downloader.exe"

                    launch_cmd = ["--tray", "--url", url]
                    if exe_same_dir.exists():
                        subprocess.Popen([str(exe_same_dir)] + launch_cmd)
                    elif exe_candidate.exists():
                        subprocess.Popen([str(exe_candidate)] + launch_cmd)
                    elif dist_candidate.exists():
                        subprocess.Popen([str(dist_candidate)] + launch_cmd)
                    else:
                        python_exe = sys.executable
                        main_py = str(Path(project_root) / "main.py")
                        subprocess.Popen([python_exe, main_py] + launch_cmd)

                send_message({"status": "success", "message": "Download routed to P-Downloader Ultra"})
            elif action == "ping":
                try:
                    from core import __version__ as app_version
                except Exception:
                    app_version = "1.0.1"
                send_message({"status": "pong", "app": "P-Downloader", "version": app_version})
            else:
                send_message({"status": "error", "message": f"Unknown action: {action}"})

        except Exception as e:
            log_debug(f"[LOOP EXCEPTION] {e}")
            send_message({"status": "error", "error": str(e)})
            break

if __name__ == "__main__":
    main()
