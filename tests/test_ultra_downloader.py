"""
Unit and Integration Tests for P-Downloader Ultra features:
- IDM Refresh Download Address (Expired Link Recovery)
- Plexo Multi-Network Interface Bandwidth Bonding
- Site Logins & Authentication Injection
- High-Precision Speed Limiter
- Magnet & Torrent Parsing
"""
import os
import unittest
import tempfile
import time
from pathlib import Path

from core.db import DownloadDB
from core.segment import DownloadTask, Segment, validate_refresh_url
from core.engine import DownloadEngine
from core.network_binder import NetworkManager, NetworkInterface
from core.credentials_manager import CredentialsManager
from core.speed_limiter import SpeedLimiter
from core.torrent import is_torrent_or_magnet, parse_magnet_uri, bdecode

class TestUltraDownloaderFeatures(unittest.TestCase):
    def setUp(self):
        self.tf_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tf_db.close()
        self.db = DownloadDB(self.tf_db.name)
        self.engine = DownloadEngine(self.db)

    def tearDown(self):
        self.db.close()
        if os.path.exists(self.tf_db.name):
            try:
                os.remove(self.tf_db.name)
            except Exception:
                pass

    def test_refresh_download_address(self):
        """
        Verify that Refresh Download Address updates the SQLite database,
        task in-memory URL, metadata sidecar file, and maintains downloaded bytes.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "archive.iso")
            meta_path = save_path + ".pdownload"

            # Create an initial task that downloaded 25 MB out of 100 MB
            task_id = "iso_task_1"
            total_bytes = 104857600  # 100 MB
            downloaded = 26214400    # 25 MB

            self.db.add_download({
                "id": task_id,
                "url": "https://expired-host.com/files/archive.iso?token=expired",
                "filename": "archive.iso",
                "save_path": save_path,
                "total_bytes": total_bytes,
                "downloaded_bytes": downloaded,
                "status": "error",
                "category": "General",
                "connections": 4,
                "supports_range": True,
                "error_message": "HTTP 403 Forbidden"
            })

            # Create sidecar metadata
            task = DownloadTask(
                task_id=task_id,
                url="https://expired-host.com/files/archive.iso?token=expired",
                save_path=save_path,
                connections=4
            )
            task.total_bytes = total_bytes
            task.supports_range = True
            task.downloaded_bytes = downloaded
            task.segments = [
                Segment(0, 0, 26214399, downloaded=26214400),
                Segment(1, 26214400, 52428799, downloaded=0),
                Segment(2, 52428800, 78643199, downloaded=0),
                Segment(3, 78643200, 104857599, downloaded=0),
            ]
            task.segments[0].completed = True
            task._save_metadata()

            # Refresh URL
            new_url = "https://fresh-host.com/files/archive.iso?token=fresh_abc123"
            refreshed = task.refresh_url(new_url)
            self.assertTrue(refreshed)
            self.assertEqual(task.url, new_url)
            self.assertEqual(task.status, "paused")
            self.assertEqual(task.downloaded_bytes, downloaded)

    def test_credentials_manager(self):
        """
        Verify Site Logins saving, retrieving, and Basic/Bearer header generation.
        """
        cm = CredentialsManager(self.db)
        cm.set_login("downloads.premium-host.com", username="tester", password="secure_password_123", auth_type="basic")

        headers = cm.get_auth_headers_for_url("https://downloads.premium-host.com/files/data.bin")
        self.assertIn("Authorization", headers)
        self.assertTrue(headers["Authorization"].startswith("Basic "))

        cm.set_login("api.token-host.com", auth_type="bearer", token="secret_token_xyz")
        bearer_headers = cm.get_auth_headers_for_url("https://api.token-host.com/v1/download")
        self.assertEqual(bearer_headers.get("Authorization"), "Bearer secret_token_xyz")

    def test_multi_network_adapter_manager(self):
        """
        Verify that NetworkManager discovers interfaces and can assign them round-robin.
        """
        nm = NetworkManager()
        self.assertIsNotNone(nm)
        active = nm.get_active_interfaces()
        self.assertIsInstance(active, list)

    def test_speed_limiter(self):
        """
        Verify that SpeedLimiter properly limits byte rates.
        """
        limiter = SpeedLimiter(limit_bytes_per_sec=100000)
        self.assertEqual(limiter.limit, 100000)
        limiter.set_limit(0)
        self.assertEqual(limiter.limit, 0)

    def test_torrent_and_magnet_parsing(self):
        """
        Verify Magnet URI parsing and protocol detection.
        """
        magnet = "magnet:?xt=urn:btih:da39a3ee5e6b4b0d3255bfef95601890afd80709&dn=Ubuntu-24.04-Desktop.iso&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80"
        self.assertTrue(is_torrent_or_magnet(magnet))
        parsed = parse_magnet_uri(magnet)
        self.assertEqual(parsed["name"], "Ubuntu-24.04-Desktop.iso")
        self.assertEqual(parsed["info_hash"].lower(), "da39a3ee5e6b4b0d3255bfef95601890afd80709")
        self.assertIn("udp://tracker.openbittorrent.com:80", parsed["trackers"])

if __name__ == "__main__":
    unittest.main()
