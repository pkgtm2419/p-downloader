"""
Local Inter-Process Communication (IPC) for P-Downloader.
Ensures single-instance management and enables browser extension / CLI
to forward download requests securely to the running background instance.
Implements secret token authentication, length-framed requests, and acknowledged responses.
"""
import os
import sys
import time
import socket
import json
import struct
import secrets
import threading
import subprocess
from pathlib import Path
from typing import Callable, Optional, Dict, Any

IPC_HOST = "127.0.0.1"
IPC_PORT = 49152
TOKEN_FILE = Path.home() / ".pdownloader" / ".ipc_token"
MAX_FRAME_SIZE = 256 * 1024  # 256 KiB max frame size to prevent memory exhaustion

def get_or_create_ipc_token() -> str:
    """
    Returns the persistent cryptographically secure IPC authorization token.
    Restricts file access permissions to the current user.
    """
    try:
        if TOKEN_FILE.is_file():
            token = TOKEN_FILE.read_text(encoding="utf-8").strip()
            if len(token) >= 32:
                return token

        token = secrets.token_hex(32)
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(token, encoding="utf-8")
        if sys.platform != "win32":
            try:
                os.chmod(TOKEN_FILE, 0o600)
            except Exception:
                pass
        else:
            try:
                username = os.environ.get("USERNAME")
                if username:
                    subprocess.run(
                        ["icacls", str(TOKEN_FILE), "/inheritance:r", "/grant:r", f"{username}:(R,W)"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                        creationflags=0x08000000 if sys.platform == "win32" else 0
                    )
            except Exception:
                pass
        return token
    except Exception:
        return "pdownloader_fallback_token_local_only"

def send_to_running_instance(
    message: Dict[str, Any],
    timeout: float = 1.0,
    host: str = IPC_HOST,
    port: int = IPC_PORT
) -> bool:
    """
    Fire-and-forget message delivery to existing running instance.
    """
    try:
        res = request_from_running_instance(message, timeout=timeout, host=host, port=port)
        return bool(res and res.get("ok", True))
    except Exception:
        return False

def request_from_running_instance(
    message: Dict[str, Any],
    timeout: float = 3.0,
    host: str = IPC_HOST,
    port: int = IPC_PORT
) -> Optional[Dict[str, Any]]:
    """
    Send length-framed request to running instance and await acknowledged response.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))

        msg_copy = dict(message)
        msg_copy["auth_token"] = get_or_create_ipc_token()

        raw_json = json.dumps(msg_copy).encode("utf-8")
        if len(raw_json) > MAX_FRAME_SIZE:
            s.close()
            return None

        # Send 4-byte length header followed by body
        s.sendall(struct.pack(">I", len(raw_json)) + raw_json)

        # Read response length
        raw_len = s.recv(4)
        if len(raw_len) < 4:
            s.close()
            return None
        resp_len = struct.unpack(">I", raw_len)[0]
        if resp_len > MAX_FRAME_SIZE:
            s.close()
            return None

        resp_data = bytearray()
        while len(resp_data) < resp_len:
            chunk = s.recv(min(4096, resp_len - len(resp_data)))
            if not chunk:
                break
            resp_data.extend(chunk)

        s.close()
        return json.loads(resp_data.decode("utf-8"))
    except Exception:
        return None

class IPCServer:
    def __init__(
        self,
        callback: Callable[[Dict[str, Any]], Optional[Dict[str, Any]]],
        host: str = IPC_HOST,
        port: int = IPC_PORT
    ):
        self.callback = callback
        self.host = host
        self.port = port
        self.running = False
        self._server_socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self.token = get_or_create_ipc_token()

    def start(self, retries: int = 15, retry_delay: float = 0.1) -> bool:
        for attempt in range(retries):
            try:
                self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if hasattr(socket, "SO_REUSEPORT"):
                    try:
                        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                    except OSError:
                        pass
                self._server_socket.bind((self.host, self.port))
                self._server_socket.listen(10)
                self._server_socket.settimeout(0.5)
                self.running = True

                self._thread = threading.Thread(target=self._listen_loop, daemon=True)
                self._thread.start()
                return True
            except OSError:
                if self._server_socket:
                    try:
                        self._server_socket.close()
                    except Exception:
                        pass
                    self._server_socket = None
                if attempt < retries - 1:
                    time.sleep(retry_delay)
                else:
                    return False
            except Exception:
                return False
        return False

    def _listen_loop(self):
        while self.running and self._server_socket:
            try:
                try:
                    client_sock, _ = self._server_socket.accept()
                except socket.timeout:
                    continue
                except (OSError, ValueError):
                    if not self.running:
                        break
                    continue

                client_sock.settimeout(3.0)

                # Peek or read length prefix
                header = client_sock.recv(4)
                if len(header) < 4:
                    client_sock.close()
                    continue

                length = struct.unpack(">I", header)[0]
                if length > MAX_FRAME_SIZE:
                    client_sock.close()
                    continue

                raw_data = bytearray()
                while len(raw_data) < length:
                    chunk = client_sock.recv(min(4096, length - len(raw_data)))
                    if not chunk:
                        break
                    raw_data.extend(chunk)

                if len(raw_data) < length:
                    client_sock.close()
                    continue

                msg = json.loads(raw_data.decode("utf-8"))
                provided_token = msg.get("auth_token", "")
                if not secrets.compare_digest(provided_token, self.token):
                    # Unauthorized: send error and close
                    err_resp = json.dumps({"ok": False, "code": "AUTH_FAILED", "message": "Unauthorized"}).encode("utf-8")
                    try:
                        client_sock.sendall(struct.pack(">I", len(err_resp)) + err_resp)
                    except Exception:
                        pass
                    client_sock.close()
                    continue

                response = None
                try:
                    if self.callback:
                        response = self.callback(msg)
                except Exception as e:
                    response = {"ok": False, "error": str(e)}

                if response is None:
                    response = {"ok": True, "code": "OK"}

                resp_bytes = json.dumps(response).encode("utf-8")
                try:
                    client_sock.sendall(struct.pack(">I", len(resp_bytes)) + resp_bytes)
                except Exception:
                    pass
                client_sock.close()

            except Exception:
                if not self.running:
                    break

    def stop(self):
        self.running = False
        sock = self._server_socket
        self._server_socket = None
        if sock:
            try:
                dummy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                dummy.settimeout(0.2)
                dummy.connect((self.host, self.port))
                dummy.close()
            except Exception:
                pass
            try:
                sock.close()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None
