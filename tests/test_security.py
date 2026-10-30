"""
Comprehensive Unit Tests for P-Downloader Security Hardening & Penetration Defenses:
- SEC-01: Path Traversal and Content-Disposition sanitization
- SEC-02: IPC Token Authentication and loopback protection
- SEC-03: Credentials Encryption at Rest (DPAPI / Fernet)
- SEC-04: Bencode Recursion Depth Limit & Memory Protection
- SEC-05: WebSpider SSRF & Loopback Filtering
"""
import os
import unittest
import tempfile
from pathlib import Path

from core.categories import sanitize_filename, get_default_save_path, DEFAULT_DOWNLOADS_DIR
from core.torrent import bdecode
from core.credentials_manager import CredentialsManager, encrypt_secret, decrypt_secret
from core.db import DownloadDB
from core.ipc import IPCServer, send_to_running_instance, get_or_create_ipc_token
from core.spider import is_safe_external_url

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

    def test_spider_ssrf_filtering(self):
        """SEC-05: Verify that WebSpider blocks loopback, link-local, and private RFC1918 IPs."""
        self.assertFalse(is_safe_external_url("http://127.0.0.1/admin"))
        self.assertFalse(is_safe_external_url("http://localhost:8080/"))
        self.assertFalse(is_safe_external_url("http://169.254.169.254/latest/meta-data/"))
        self.assertFalse(is_safe_external_url("ftp://example.com/file"))
        self.assertTrue(is_safe_external_url("https://example.com/downloads/archive.zip"))

    def test_ipc_token_authentication(self):
        """SEC-02: Verify that IPC server rejects unauthenticated connection attempts."""
        received = []
        server = IPCServer(callback=lambda msg: received.append(msg))
        server.start()

        try:
            # 1. Send legitimate message via send_to_running_instance (attaches token automatically)
            send_to_running_instance({"action": "ping", "test": "auth_ok"})
            import time
            time.sleep(0.3)
            self.assertTrue(any(m.get("test") == "auth_ok" for m in received))

            # 2. Simulate raw unauthorized socket attack without token
            import socket, json
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", 49152))
            s.sendall(json.dumps({"action": "download", "test": "unauthorized_attack"}).encode("utf-8"))
            s.close()
            time.sleep(0.3)

            # Unauthorized message should have been rejected silently
            self.assertFalse(any(m.get("test") == "unauthorized_attack" for m in received))
        finally:
            server.stop()

if __name__ == "__main__":
    unittest.main()
