"""
Native Messaging Host for P-Downloader.
Communicates with Chrome / Edge / Firefox WebExtensions via stdin/stdout binary framing.
"""
import sys
import json
import struct
import os
import subprocess
from pathlib import Path

def send_message(message: dict):
    raw_json = json.dumps(message).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('@I', len(raw_json)))
    sys.stdout.buffer.write(raw_json)
    sys.stdout.buffer.flush()

def read_message() -> dict:
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) == 0:
        return {}
    length = struct.unpack('@I', raw_length)[0]
    raw_data = sys.stdin.buffer.read(length)
    return json.loads(raw_data.decode('utf-8'))

def main():
    # Add project root to sys.path so core.ipc can be imported
    project_root = str(Path(__file__).parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    try:
        from core.ipc import send_to_running_instance
    except Exception:
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
                send_message({"status": "pong", "app": "P-Downloader"})
            else:
                send_message({"status": "error", "message": f"Unknown action: {action}"})

        except Exception as e:
            send_message({"status": "error", "error": str(e)})
            break

if __name__ == "__main__":
    main()
