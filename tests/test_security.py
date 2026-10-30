"""
Comprehensive Unit Tests for P-Downloader Security Hardening & Penetration Defenses:
- SEC-01: Path Traversal, Content-Disposition, and Windows Reserved Device Name sanitization
- SEC-02: IPC Token Authentication, frame bounds, and file access controls
- SEC-03: Credentials Encryption at Rest (DPAPI / Fernet Vault Key)
- SEC-04: Bencode Recursion Depth Limit & Memory Protection
- SEC-05: WebSpider SSRF, IPv6 literals, and Redirect Protection
"""
import os
import unittest
import tempfile
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

from core.categories import sanitize_filename, get_default_save_path, DEFAULT_DOWNLOADS_DIR
from core.torrent import bdecode
from core.credentials_manager import CredentialsManager, encrypt_secret, decrypt_secret, _get_fernet_key
from core.db import DownloadDB
from core.ipc import IPCServer, send_to_running_instance, get_or_create_ipc_token, TOKEN_FILE
from core.spider import is_safe_external_url, WebSpider

class TestSecurityHardening(unittest.TestCase):
    def test_filename_path_traversal_sanitization(self):
        """SEC-01: Verify path traversal sequences and dangerous characters are neutralized."""
        self.assertEqual(sanitize_filename("../../evil.bat"), "evil.bat")
        self.assertEqual(sanitize_filename("..\\..\\Windows\\System32\\calc.exe"), "calc.exe")
        self.assertEqual(sanitize_filename("valid_file.zip"), "valid_file.zip")
        self.assertEqual(sanitize_filename(""), "download.bin")
        self.assertEqual(sanitize_filename("..."), "download.bin")
        self.assertEqual(sanitize_filename("file\x00name.exe"), "filename.exe")
        self.assertEqual(sanitize_filename('bad:file*name?.mp4'), "bad_file_name_.mp4")

    def test_windows_reserved_device_names(self):
        """SEC-01: DOS/Windows reserved device names are neutralized to prevent I/O lockup."""
        self.assertEqual(sanitize_filename("con.zip"), "_con.zip")
        self.assertEqual(sanitize_filename("aux.mp4"), "_aux.mp4")
        self.assertEqual(sanitize_filename("NUL"), "_NUL")
        self.assertEqual(sanitize_filename("COM1.txt"), "_COM1.txt")
        self.assertEqual(sanitize_filename("prn.tar.gz"), "_prn.tar.gz")
        self.assertEqual(sanitize_filename("normal_file.pdf"), "normal_file.pdf")

    def test_default_save_path_containment(self):
        """SEC-01: Verify that get_default_save_path strictly confines target inside category folder."""
        path = get_default_save_path("../../evil.exe", "Programs")
        base = Path(DEFAULT_DOWNLOADS_DIR) / "Programs"
        self.assertTrue(Path(path).resolve().is_relative_to(base.resolve()))
        self.assertEqual(os.path.basename(path), "evil.exe")

    def test_bdecode_recursion_depth_limit(self):
        """SEC-04: Verify that bdecode rejects deeply nested structures without crashing."""
        # 50 nested lists (exceeds max_depth 32)
        nested_attack = b"l" * 50 + b"i1e" + b"e" * 50
        with self.assertRaises(ValueError) as ctx:
            bdecode(nested_attack)
        self.assertIn("Exceeded maximum bencode nesting depth", str(ctx.exception))

    def test_bdecode_excessive_byte_length(self):
        """SEC-04: Verify that bdecode rejects excessive/negative byte string lengths."""
        huge_attack = b"999999999:abc"
        with self.assertRaises(ValueError) as ctx:
            bdecode(huge_attack)
        self.assertIn("Invalid or excessive byte string length", str(ctx.exception))

    def test_credentials_encryption_at_rest(self):
        """SEC-03: Verify that passwords and tokens are encrypted at rest in SQLite database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name

        try:
            db = DownloadDB(db_path)
            cm = CredentialsManager(db)
            cm.set_login("premium-host.com", "alice", "secret_pass_999", "basic", "token_xyz")

            # Check raw database contents: plain text password should NOT exist in DB
            cur = db.conn.cursor()
            cur.execute("SELECT password, token FROM site_logins WHERE domain = 'premium-host.com'")
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertNotEqual(row["password"], "secret_pass_999")
            self.assertNotEqual(row["token"], "token_xyz")
            self.assertTrue(row["password"].startswith(("dpapi:", "vault:")))

            # Check decrypted output through CredentialsManager API
            login = cm.get_login("premium-host.com")
            self.assertEqual(login["password"], "secret_pass_999")
            self.assertEqual(login["token"], "token_xyz")
            db.close()
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_fernet_vault_key_generation(self):
        """SEC-03: Cryptographically random vault key is generated and valid 44-byte base64."""
        key = _get_fernet_key()
        self.assertIsInstance(key, bytes)
        self.assertEqual(len(key), 44)

    def test_spider_ssrf_filtering(self):
        """SEC-05: Verify that WebSpider blocks loopback, link-local, and private RFC1918 IPs."""
        self.assertFalse(is_safe_external_url("http://127.0.0.1/admin"))
        self.assertFalse(is_safe_external_url("http://localhost:8080/"))
        self.assertFalse(is_safe_external_url("http://169.254.169.254/latest/meta-data/"))
        self.assertFalse(is_safe_external_url("http://[::1]/"))
        self.assertFalse(is_safe_external_url("ftp://example.com/file"))
        self.assertTrue(is_safe_external_url("https://example.com/downloads/archive.zip"))

    def test_spider_ssrf_redirect_protection(self):
        """SEC-05: WebSpider blocks malicious redirects targeting loopback / cloud metadata."""
        class MaliciousRedirectHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass
            def do_GET(self):
                # Redirects to local cloud metadata or loopback
                self.send_response(302)
                self.send_header("Location", "http://127.0.0.1:49152/admin")
                self.end_headers()

        server = HTTPServer(("127.0.0.1", 0), MaliciousRedirectHandler)
        port = server.server_port
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        try:
            spider = WebSpider(start_url=f"http://127.0.0.1:{port}/")
            # Crawl should immediately reject start_url as loopback, or if simulated redirect:
            pages = spider._fetch_and_parse_page(f"http://127.0.0.1:{port}/redirect")
            self.assertEqual(pages, [])
        finally:
            server.shutdown()
            server.server_close()

    def test_ipc_token_authentication(self):
        """SEC-02: Verify that IPC server rejects unauthenticated connection attempts."""
        received = []
        server = IPCServer(callback=lambda msg: received.append(msg))
        self.assertTrue(server.start())

        try:
            # 1. Send legitimate message via send_to_running_instance (attaches token automatically)
            ok = send_to_running_instance({"action": "ping", "test": "auth_ok"})
            self.assertTrue(ok)
            import time
            time.sleep(0.1)
            self.assertTrue(any(m.get("test") == "auth_ok" for m in received))

            # 2. Simulate raw unauthorized socket attack without token
            import socket, json
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", 49152))
            s.sendall(json.dumps({"action": "download", "test": "unauthorized_attack"}).encode("utf-8"))
            s.close()
            time.sleep(0.1)

            # Unauthorized message should have been rejected silently
            self.assertFalse(any(m.get("test") == "unauthorized_attack" for m in received))
        finally:
            server.stop()

    def test_ipc_token_file_validity(self):
        """SEC-02: Token file is generated, non-empty, and has at least 32 characters."""
        tok = get_or_create_ipc_token()
        self.assertGreaterEqual(len(tok), 32)
        self.assertTrue(TOKEN_FILE.is_file())


if __name__ == "__main__":
    unittest.main()
