"""
Local Inter-Process Communication (IPC) for P-Downloader.
Ensures single-instance management and enables browser extension / CLI
to forward download requests instantly to the running background tray instance.
"""
import socket
import json
import threading
from typing import Callable, Optional, Dict, Any

IPC_HOST = "127.0.0.1"
IPC_PORT = 49152

def send_to_running_instance(message: Dict[str, Any], timeout: float = 1.0) -> bool:
    """
    Attempts to connect to an existing running P-Downloader instance.
    Returns True if message was successfully delivered.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((IPC_HOST, IPC_PORT))
        raw = json.dumps(message).encode("utf-8")
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
