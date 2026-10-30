"""
Native Messaging Host for P-Downloader (Protocol v2).
Communicates with Chrome / Edge / Brave / Firefox WebExtensions via stdin/stdout binary framing.
Guarantees transactional desktop acknowledgments and protects browser secrets.
"""
import sys
import json
import struct
import os
import time
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

def redact_sensitive(obj):
    """Sanitize secrets, auth tokens, and cookies before logging."""
    if isinstance(obj, dict):
        clean = {}
        for k, v in obj.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in ("cookie", "auth", "token", "password", "secret", "key")):
                clean[k] = "[REDACTED]"
            else:
                clean[k] = redact_sensitive(v)
        return clean
    elif isinstance(obj, list):
        return [redact_sensitive(x) for x in obj]
    return obj

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
        safe_msg = redact_sensitive(message)
        log_debug(f"[SENT] {safe_msg}")
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
    safe_msg = redact_sensitive(msg)
    log_debug(f"[RECEIVED] {safe_msg}")
    return msg

def launch_desktop_background(project_root: str):
    """Attempt to spawn P-Downloader in background tray mode."""
    exe_same_dir = Path(sys.executable).parent / "P-Downloader.exe"
    exe_candidate = Path(project_root) / "P-Downloader.exe"
    dist_candidate = Path(project_root) / "dist" / "P-Downloader" / "P-Downloader.exe"

    launch_cmd = ["--tray"]
    try:
        flags = 0x08000000 if sys.platform == "win32" else 0
        if exe_same_dir.exists():
            subprocess.Popen([str(exe_same_dir)] + launch_cmd, creationflags=flags)
        elif exe_candidate.exists():
            subprocess.Popen([str(exe_candidate)] + launch_cmd, creationflags=flags)
        elif dist_candidate.exists():
            subprocess.Popen([str(dist_candidate)] + launch_cmd, creationflags=flags)
        else:
            python_exe = sys.executable
            main_py = str(Path(project_root) / "main.py")
            subprocess.Popen([python_exe, main_py] + launch_cmd, creationflags=flags)
    except Exception as e:
        log_debug(f"[LAUNCH ERROR] {e}")

def main():
    log_debug("--- P-Downloader Native Host Started (Protocol v2) ---")
    project_root = str(Path(__file__).parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    try:
        from core.ipc import request_from_running_instance
    except Exception as e:
        log_debug(f"[IPC IMPORT ERROR] {e}")
        request_from_running_instance = None

    while True:
        try:
            msg = read_message()
            if not msg:
                break

            req_id = msg.get("requestId", "")
            action = msg.get("action", "")

            if action == "ping":
                try:
                    from core import __version__ as app_version
                except Exception:
                    app_version = "1.0.6"
                send_message({
                    "requestId": req_id,
                    "ok": True,
                    "protocolVersion": 2,
                    "status": "pong",
                    "app": "P-Downloader",
                    "version": app_version
                })
                continue

            if not request_from_running_instance:
                send_message({
                    "requestId": req_id,
                    "ok": False,
                    "code": "IPC_UNAVAILABLE",
                    "error": "Local IPC module unavailable"
                })
                continue

            # Forward transactional message to desktop IPC
            reply = request_from_running_instance(msg, timeout=2.0)

            # If desktop was not reached on reserve/download, try launching once and retry
            if reply is None and action in ("reserve", "download"):
                launch_desktop_background(project_root)
                time.sleep(1.0)
                reply = request_from_running_instance(msg, timeout=2.0)

            if reply is not None:
                reply["requestId"] = req_id
                send_message(reply)
            else:
                send_message({
                    "requestId": req_id,
                    "ok": False,
                    "code": "APP_UNAVAILABLE",
                    "error": "Desktop app not running or timed out"
                })

        except Exception as e:
            log_debug(f"[LOOP EXCEPTION] {e}")
            send_message({"ok": False, "error": str(e)})
            break

if __name__ == "__main__":
    main()
