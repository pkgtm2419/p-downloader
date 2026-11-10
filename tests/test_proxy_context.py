"""
Tests for Proxy configuration and Browser Context / Header propagation (REQ-FIX-01).
"""
import unittest
import tempfile
import os
import shutil
from core.db import DownloadDB
from core.network_binder import NetworkManager, SourceAddressAdapter
from core.engine import DownloadEngine
from core.download_models import BrowserRequestContext

class TestProxyAndContext(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="pdl_test_proxy_")
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.db = DownloadDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_proxy_config_disabled(self):
        self.db.set_setting("use_proxy", "0")
        self.assertIsNone(self.db.get_proxy_url())
        self.assertIsNone(self.db.get_proxy_config())

    def test_proxy_config_enabled_http(self):
        self.db.set_setting("use_proxy", "1")
        self.db.set_setting("proxy_proto", "HTTP")
        self.db.set_setting("proxy_host", "127.0.0.1")
        self.db.set_setting("proxy_port", "8888")

        self.assertEqual(self.db.get_proxy_url(), "http://127.0.0.1:8888")
        cfg = self.db.get_proxy_config()
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg["http"], "http://127.0.0.1:8888")
        self.assertEqual(cfg["https"], "http://127.0.0.1:8888")

    def test_proxy_config_enabled_socks5(self):
        self.db.set_setting("use_proxy", "1")
        self.db.set_setting("proxy_proto", "SOCKS5")
        self.db.set_setting("proxy_host", "10.0.0.5")
        self.db.set_setting("proxy_port", "1080")

        self.assertEqual(self.db.get_proxy_url(), "socks5://10.0.0.5:1080")
        cfg = self.db.get_proxy_config()
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg["http"], "socks5://10.0.0.5:1080")
        self.assertEqual(cfg["https"], "socks5://10.0.0.5:1080")

    def test_network_manager_session_attaches_proxy(self):
        net_mgr = NetworkManager()
        custom_proxy = {"http": "http://192.168.1.100:3128", "https": "http://192.168.1.100:3128"}
        session = net_mgr.get_session_for_interface(proxies=custom_proxy)
        self.assertEqual(session.proxies.get("http"), "http://192.168.1.100:3128")
        self.assertEqual(session.proxies.get("https"), "http://192.168.1.100:3128")

    def test_source_address_adapter_proxy_manager(self):
        adapter = SourceAddressAdapter("127.0.0.1")
        self.assertEqual(adapter.source_address, ("127.0.0.1", 0))

    def test_engine_creates_download_with_headers_and_persists(self):
        engine = DownloadEngine(self.db)
        save_path = os.path.join(self.temp_dir, "testfile.bin")
        test_headers = {
            "Cookie": "session_id=abcdef123456",
            "Referer": "https://example.com/portal",
            "User-Agent": "P-Downloader Test Agent"
        }

        task = engine.create_download(
            url="https://example.com/file.bin",
            filename="testfile.bin",
            save_path=save_path,
            auto_start=False,
            headers=test_headers
        )

        self.assertEqual(task.headers, test_headers)

        # Verify persisted into SQLite
        row = self.db.get_download(task.task_id)
        self.assertIsNotNone(row)
        self.assertIn("Cookie", row["headers_json"])
        self.assertIn("session_id=abcdef123456", row["headers_json"])

        # Test resume restores headers
        engine.tasks.clear()
        engine.resume_download(task.task_id)
        resumed_task = engine.tasks[task.task_id]
        self.assertEqual(resumed_task.headers, test_headers)

    def test_engine_creates_from_context(self):
        engine = DownloadEngine(self.db)
        save_path = os.path.join(self.temp_dir, "from_ctx.bin")
        ctx = BrowserRequestContext(
            user_agent="Browser Agent 1.0",
            referrer="https://testsite.org/home",
            per_origin_headers={"https://testsite.org": {"Authorization": "Bearer my_secret_token"}}
        )

        task = engine.create_download(
            url="https://testsite.org/data.zip",
            filename="from_ctx.bin",
            save_path=save_path,
            auto_start=False,
            context=ctx
        )

        self.assertEqual(task.headers.get("Authorization"), "Bearer my_secret_token")
        self.assertEqual(task.headers.get("User-Agent"), "Browser Agent 1.0")
        self.assertEqual(task.headers.get("Referer"), "https://testsite.org/home")

if __name__ == "__main__":
    unittest.main()
