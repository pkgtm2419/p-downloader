"""
Tests for RFC 959 / RFC 3659 FTP Downloader Engine (REQ-FIX-02).
"""
import os
import unittest
import tempfile
import shutil
from unittest.mock import MagicMock, patch

from core.ftp_downloader import parse_ftp_url, probe_ftp, FTPDownloadTask
from core.engine import DownloadEngine
from core.db import DownloadDB


class TestFTPDownloader(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="pdl_test_ftp_")
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.db = DownloadDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_ftp_url(self):
        # Default anonymous
        is_tls, host, port, user, pw, path = parse_ftp_url("ftp://ftp.example.com/pub/linux/kernel.iso")
        self.assertFalse(is_tls)
        self.assertEqual(host, "ftp.example.com")
        self.assertEqual(port, 21)
        self.assertEqual(user, "anonymous")
        self.assertEqual(pw, "anonymous@")
        self.assertEqual(path, "pub/linux/kernel.iso")

        # Custom user, pass, port, and FTPS
        is_tls, host, port, user, pw, path = parse_ftp_url("ftps://alice:secret123@secure.ftp.org:990/files/archive.tar.gz")
        self.assertTrue(is_tls)
        self.assertEqual(host, "secure.ftp.org")
        self.assertEqual(port, 990)
        self.assertEqual(user, "alice")
        self.assertEqual(pw, "secret123")
        self.assertEqual(path, "files/archive.tar.gz")

    @patch("core.ftp_downloader.ftplib.FTP")
    def test_probe_ftp(self, mock_ftp_cls):
        mock_ftp = MagicMock()
        mock_ftp_cls.return_value = mock_ftp

        def mock_sendcmd(cmd):
            if cmd.startswith("SIZE"):
                return "213 1048576"  # 1 MB
            elif cmd.startswith("REST"):
                return "350 Restarting at 0"
            return "200 Command okay"

        mock_ftp.sendcmd.side_effect = mock_sendcmd

        res = probe_ftp("ftp://ftp.gnu.org/gnu/emacs/emacs-29.1.tar.xz")
        self.assertEqual(res["total_bytes"], 1048576)
        self.assertTrue(res["supports_range"])
        self.assertEqual(res["filename"], "emacs-29.1.tar.xz")
        self.assertTrue(res["is_ftp"])

    @patch("core.ftp_downloader.ftplib.FTP")
    def test_ftp_download_task_run_and_complete(self, mock_ftp_cls):
        mock_ftp = MagicMock()
        mock_ftp_cls.return_value = mock_ftp

        test_data = b"Hello from FTP test stream!" * 100

        def mock_retrbinary(cmd, callback, blocksize=65536, rest=None):
            callback(test_data)
            return "226 Transfer complete"

        mock_ftp.retrbinary.side_effect = mock_retrbinary

        save_path = os.path.join(self.temp_dir, "test_ftp_file.txt")
        task = FTPDownloadTask(
            task_id="ftp001",
            url="ftp://ftp.example.com/test_ftp_file.txt",
            save_path=save_path
        )

        task.prepare()
        task._run_download()

        self.assertEqual(task.status, "completed")
        self.assertTrue(os.path.exists(save_path))
        with open(save_path, "rb") as f:
            self.assertEqual(f.read(), test_data)

    def test_engine_routes_and_resumes_ftp(self):
        engine = DownloadEngine(self.db)
        save_path = os.path.join(self.temp_dir, "engine_ftp.bin")

        with patch("core.ftp_downloader.probe_ftp") as mock_probe:
            mock_probe.return_value = {
                "url": "ftp://mirror.cs.uchicago.edu/debian/doc/FAQ.txt",
                "final_url": "ftp://mirror.cs.uchicago.edu/debian/doc/FAQ.txt",
                "filename": "FAQ.txt",
                "total_bytes": 45000,
                "supports_range": True,
                "is_ftp": True
            }

            task = engine.create_download(
                url="ftp://mirror.cs.uchicago.edu/debian/doc/FAQ.txt",
                filename="FAQ.txt",
                save_path=save_path,
                auto_start=False
            )

            self.assertTrue(getattr(task, "is_ftp", False))
            self.assertEqual(task.url, "ftp://mirror.cs.uchicago.edu/debian/doc/FAQ.txt")

            # Check DB persistence
            row = self.db.get_download(task.task_id)
            self.assertIsNotNone(row)
            self.assertEqual(row["kind"], "ftp")

            # Test resume
            engine.tasks.clear()
            engine.resume_download(task.task_id)
            resumed_task = engine.tasks[task.task_id]
            self.assertTrue(getattr(resumed_task, "is_ftp", False))


if __name__ == "__main__":
    unittest.main()
