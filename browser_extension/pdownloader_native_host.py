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
    while True:
        try:
            msg = read_message()
            if not msg:
                break
            
            action = msg.get("action")
            url = msg.get("url")

            if action == "download" and url:
                # Launch main.py with the URL or pass to running instance
                python_exe = sys.executable
                main_py = str(Path(__file__).parent.parent / "main.py")
                subprocess.Popen([python_exe, main_py, "--url", url])
                send_message({"status": "success", "message": "Download sent to P-Downloader"})
            elif action == "ping":
                send_message({"status": "pong", "app": "P-Downloader"})
            else:
                send_message({"status": "error", "message": f"Unknown action: {action}"})

        except Exception as e:
            send_message({"status": "error", "error": str(e)})
            break

if __name__ == "__main__":
    main()
