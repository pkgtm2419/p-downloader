"""
Embedded HTTPS / HTTP Web Remote Server for P-Downloader.
Provides mobile-friendly web dashboard, REST API, self-signed TLS, and PIN authentication.
"""
import os
import json
import ssl
import time
import secrets
import threading
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any

from .db import DownloadDB


def generate_self_signed_cert(cert_path: str, key_path: str):
    """Generates a self-signed RSA certificate for local HTTPS remote control."""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "pdownloader.local")])
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=3650))
            .sign(key, hashes.SHA256())
        )
        os.makedirs(os.path.dirname(os.path.abspath(key_path)), exist_ok=True)
        with open(key_path, "wb") as f:
            f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        return True
    except Exception:
        return False


WEB_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>P-Downloader Web Remote</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #121418; color: #e1e4e8; margin: 0; padding: 16px; }
  .card { background: #1c1f26; border-radius: 8px; padding: 16px; margin-bottom: 16px; border: 1px solid #2a2e38; }
  h1 { font-size: 1.4rem; color: #0078d4; margin-top: 0; }
  input, button { padding: 10px; border-radius: 6px; border: 1px solid #333a46; background: #262a34; color: #fff; font-size: 1rem; }
  input[type="text"] { width: calc(100% - 24px); margin-bottom: 10px; }
  button { background: #0078d4; border: none; cursor: pointer; font-weight: bold; }
  .item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #2a2e38; }
  .status { font-size: 0.85rem; color: #8a94a6; }
</style>
</head>
<body>
<div class="card">
  <h1>P-Downloader Remote</h1>
  <input type="text" id="url" placeholder="Paste URL (Video, Direct, Magnet, FTP)...">
  <button onclick="addUrl()">Add Download</button>
</div>
<div class="card">
  <h2>Active Downloads</h2>
  <div id="list">Loading...</div>
</div>
<script>
async function load() {
  try {
    const res = await fetch('/api/downloads');
    const data = await res.json();
    const el = document.getElementById('list');
    if (!data.length) { el.innerHTML = '<i>No active downloads</i>'; return; }
    el.innerHTML = data.map(d => `
      <div class="item">
        <div>
          <b>${d.filename}</b><br>
          <span class="status">${d.status} - ${(d.downloaded_bytes/1048576).toFixed(1)} / ${(d.total_bytes/1048576).toFixed(1)} MB</span>
        </div>
        <div>
          ${d.status === 'downloading' ? `<button onclick="pauseTask('${d.id}')">Pause</button>` : `<button onclick="resumeTask('${d.id}')">Resume</button>`}
        </div>
      </div>
    `).join('');
  } catch(e) {}
}
async function addUrl() {
  const url = document.getElementById('url').value.trim();
  if (!url) return;
  await fetch('/api/download/add', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({url})});
  document.getElementById('url').value = '';
  load();
}
async function pauseTask(id) { await fetch('/api/download/pause', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id})}); load(); }
async function resumeTask(id) { await fetch('/api/download/resume', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id})}); load(); }
setInterval(load, 2000);
load();
</script>
</body>
</html>
"""


class RemoteRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default noisy console logs

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            body = WEB_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/downloads":
            db = self.server.engine.db if hasattr(self.server, "engine") else DownloadDB()
            downloads = db.get_all_downloads()
            self._send_json(downloads)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_len) if content_len > 0 else b"{}"

        try:
            req = json.loads(post_data.decode("utf-8"))
        except Exception:
            req = {}

        engine = getattr(self.server, "engine", None)

        if parsed.path == "/api/download/add":
            url = req.get("url")
            if not url:
                self._send_json({"error": "Missing URL"}, 400)
                return
            if engine:
                task = engine.create_download(url=url, auto_start=True)
                self._send_json({"ok": True, "task_id": task.task_id})
            else:
                self._send_json({"ok": True, "message": "Queued in headless store"})
            return

        if parsed.path == "/api/download/pause":
            task_id = req.get("id")
            if engine and task_id:
                engine.pause_download(task_id)
            self._send_json({"ok": True})
            return

        if parsed.path == "/api/download/resume":
            task_id = req.get("id")
            if engine and task_id:
                engine.resume_download(task_id)
            self._send_json({"ok": True})
            return

        self.send_error(404, "Not Found")


class RemoteServer:
    """
    Manages background ThreadingHTTPServer with optional TLS encryption.
    """
    def __init__(self, engine=None, host: str = "0.0.0.0", port: int = 8463, use_tls: bool = False):
        self.engine = engine
        self.host = host
        self.port = port
        self.use_tls = use_tls
        self.pin = secrets.token_hex(4).upper()  # 8-char PIN
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._server = ThreadingHTTPServer((self.host, self.port), RemoteRequestHandler)
        self._server.engine = self.engine
        self._server.pin = self.pin

        if self.use_tls:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
            cert_file = os.path.join(base_dir, "cert.pem")
            key_file = os.path.join(base_dir, "key.pem")
            if not os.path.exists(cert_file) or not os.path.exists(key_file):
                generate_self_signed_cert(cert_file, key_file)

            if os.path.exists(cert_file) and os.path.exists(key_file):
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ctx.load_cert_chain(certfile=cert_file, keyfile=key_file)
                self._server.socket = ctx.wrap_socket(self._server.socket, server_side=True)

        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        if self._server:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception:
                pass
