"""
Deterministic local HTTP test origin with fault injection capabilities.
No external network dependencies.
"""
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

class FaultOriginHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress logging in test runner
        pass

    @property
    def server_obj(self):
        return self.server

    def do_HEAD(self):
        self._handle_request(is_head=True)

    def do_GET(self):
        self._handle_request(is_head=False)

    def _handle_request(self, is_head=False):
        server = self.server_obj
        with server.lock:
            server.request_history.append({
                "method": self.command,
                "path": self.path,
                "headers": dict(self.headers)
            })

        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/range_ignored":
            # Server returns 200 OK regardless of Range header
            data = server.payload_normal
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Accept-Ranges", "bytes")  # Server lies!
            self.send_header("ETag", '"constant-etag"')
            self.end_headers()
            if not is_head:
                self.wfile.write(data)

        elif path == "/wrong_content_range":
            # Server returns 206 but with bogus Content-Range
            data = server.payload_normal
            self.send_response(206)
            self.send_header("Content-Type", "application/octet-stream")
            # Return a Content-Range header that contradicts what was asked
            self.send_header("Content-Range", f"bytes 9999-10009/{len(data) + 10000}")
            self.send_header("Content-Length", "10")
            self.send_header("ETag", '"constant-etag"')
            self.end_headers()
            if not is_head:
                self.wfile.write(b"0123456789")

        elif path == "/unknown_length":
            # Server returns 200 without Content-Length, streaming to EOF
            data = server.payload_normal
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            # Omit Content-Length and Accept-Ranges
            self.end_headers()
            if not is_head:
                self.wfile.write(data)

        elif path == "/empty":
            # 0-byte file
            range_header = self.headers.get("Range")
            if range_header:
                self.send_response(416)
                self.send_header("Content-Range", "bytes */0")
                self.send_header("Content-Length", "0")
                self.end_headers()
            else:
                self.send_response(200)
                self.send_header("Content-Length", "0")
                self.send_header("Content-Type", "application/octet-stream")
                self.end_headers()

        elif path == "/interrupted":
            # Interrupts connection halfway through on attempt 1, succeeds on resume
            data = server.payload_normal
            range_header = self.headers.get("Range")
            server.interrupted_attempts += 1
            if server.interrupted_attempts == 1 and not is_head:
                # Send half and abruptly close connection
                half = len(data) // 2
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                self.wfile.write(data[:half])
                self.wfile.flush()
                # Close raw socket abruptly
                self.close_connection = True
                return

            # Resume attempt or subsequent attempts
            if range_header and range_header.startswith("bytes="):
                spec = range_header.replace("bytes=", "").strip()
                parts = spec.split("-")
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if parts[1] else len(data) - 1
                end = min(end, len(data) - 1)
                chunk = data[start:end + 1]

                self.send_response(206)
                self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
                self.send_header("Content-Length", str(len(chunk)))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                if not is_head:
                    self.wfile.write(chunk)
            else:
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                if not is_head:
                    self.wfile.write(data)

        elif path == "/changing_etag":
            # First request returns v1, subsequent requests return v2 with different content
            server.etag_request_count += 1
            if server.etag_request_count == 1:
                data = b"VERSION_1_ORIGINAL_DATA_CONTENT_0123456789"
                etag = '"v1"'
            else:
                data = b"VERSION_2_MODIFIED_DATA_CONTENT_DIFFERENT"
                etag = '"v2"'

            range_header = self.headers.get("Range")
            if range_header and range_header.startswith("bytes="):
                spec = range_header.replace("bytes=", "").strip()
                parts = spec.split("-")
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if parts[1] else len(data) - 1
                chunk = data[start:end + 1]
                self.send_response(206)
                self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
                self.send_header("Content-Length", str(len(chunk)))
                self.send_header("ETag", etag)
                self.end_headers()
                if not is_head:
                    self.wfile.write(chunk)
            else:
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("ETag", etag)
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                if not is_head:
                    self.wfile.write(data)

        elif path == "/throttled":
            # Returns 429 Too Many Requests
            self.send_response(429)
            self.send_header("Retry-After", "1")
            self.send_header("Content-Length", "0")
            self.end_headers()

        else:
            # /normal default
            data = server.payload_normal
            range_header = self.headers.get("Range")
            if range_header and range_header.startswith("bytes="):
                spec = range_header.replace("bytes=", "").strip()
                parts = spec.split("-")
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if parts[1] else len(data) - 1
                end = min(end, len(data) - 1)
                chunk = data[start:end + 1]

                self.send_response(206)
                self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
                self.send_header("Content-Length", str(len(chunk)))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("ETag", '"v1-clean"')
                self.end_headers()
                if not is_head:
                    self.wfile.write(chunk)
            else:
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("ETag", '"v1-clean"')
                self.end_headers()
                if not is_head:
                    self.wfile.write(data)


class FaultOriginServer(HTTPServer):
    def __init__(self, host="127.0.0.1", port=0):
        super().__init__((host, port), FaultOriginHandler)
        self.lock = threading.Lock()
        self.request_history = []
        self.interrupted_attempts = 0
        self.etag_request_count = 0
        # Deterministic 512KB payload
        self.payload_normal = bytes((i % 256) for i in range(524288))

    def reset_stats(self):
        with self.lock:
            self.request_history.clear()
            self.interrupted_attempts = 0
            self.etag_request_count = 0


class FaultOrigin:
    """Context manager for running FaultOriginServer on a local background thread."""
    def __init__(self, host="127.0.0.1"):
        self.host = host
        self.server = None
        self.thread = None
        self.port = 0

    def __enter__(self):
        self.server = FaultOriginServer(self.host, 0)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=2)

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def payload_normal(self) -> bytes:
        return self.server.payload_normal

    @property
    def request_history(self):
        with self.server.lock:
            return list(self.server.request_history)

    def url(self, endpoint: str) -> str:
        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{endpoint}"
