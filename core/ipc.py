"""
Local Inter-Process Communication (IPC) for P-Downloader.
Ensures single-instance management and enables browser extension / CLI
to forward download requests securely to the running background instance.
Implements secret token authentication to prevent unauthorized localhost socket exploitation.
"""
import os
import sys
import socket
import json
import secrets
import threading
from pathlib import Path
from typing import Callable, Optional, Dict, Any

IPC_HOST = "127.0.0.1"
IPC_PORT = 49152
TOKEN_FILE = Path.home() / ".pdownloader" / ".ipc_token"

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
        return token
    except Exception:
        return "pdownloader_fallback_token_local_only"

def send_to_running_instance(message: Dict[str, Any], timeout: float = 1.0) -> bool:
    """
    Attempts to connect to an existing running P-Downloader instance.
    Automatically attaches authentication token. Returns True if accepted.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((IPC_HOST, IPC_PORT))
        
        # Attach authentication token
        msg_copy = dict(message)
        msg_copy["auth_token"] = get_or_create_ipc_token()
        
        raw = json.dumps(msg_copy).encode("utf-8")
        s.sendall(raw)
        s.close()
        return True
    except Exception:
        return False

class IPCServer:
    def __init__(self, callback: Callable[[Dict[str, Any]], None]):
        self.callback = callback
        self.running = False
        self._server_socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self.token = get_or_create_ipc_token()

    def start(self) -> bool:
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((IPC_HOST, IPC_PORT))
            self._server_socket.listen(5)
            self.running = True

            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()
            return True
        except Exception:
            return False

    def _listen_loop(self):
        while self.running and self._server_socket:
            try:
                client_sock, _ = self._server_socket.accept()
                client_sock.settimeout(2.0)
                data = b""
                while True:
                    chunk = client_sock.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                client_sock.close()

                if data:
                    try:
                        msg = json.loads(data.decode("utf-8"))
                        # Verify security token
                        provided_token = msg.get("auth_token", "")
                        if not secrets.compare_digest(provided_token, self.token):
                            # Unauthorized request rejected silently
                            continue
                        
                        if self.callback:
                            self.callback(msg)
                    except Exception:
                        pass
            except Exception:
                if not self.running:
                    break

    def stop(self):
        self.running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None
