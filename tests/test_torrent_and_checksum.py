"""
Tests for BitTorrent Swarm Task, RSS Watcher, and Checksum Verification (Phase 2).
"""
import os
import unittest
import tempfile
import shutil
from unittest.mock import MagicMock, patch

from core.torrent import TorrentDownloadTask
from core.torrent_rss import parse_rss_feed, filter_rss_items, TorrentRSSWatcher, TorrentRSSFeed
from core.transfer_store import compute_file_checksum, verify_file_checksum
from core.engine import DownloadEngine
from core.db import DownloadDB

SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Linux ISO Tracker</title>
    <link>https://tracker.example.com</link>
    <item>
      <title>Ubuntu 24.04 Desktop AMD64 ISO</title>
      <link>magnet:?xt=urn:btih:ubuntu2404desktopiso&amp;dn=Ubuntu+24.04</link>
      <guid>ubuntu-24-04-iso</guid>
    </item>
    <item>
      <title>Debian 12 Bookworm Netinst</title>
      <link>magnet:?xt=urn:btih:debian12netinst&amp;dn=Debian+12</link>
      <guid>debian-12-netinst</guid>
    </item>
    <item>
      <title>Arch Linux 2026.04 x86_64</title>
      <link>magnet:?xt=urn:btih:archlinux2026&amp;dn=Arch+Linux</link>
      <guid>arch-2026-iso</guid>
    </item>
  </channel>
</rss>
"""


class TestTorrentAndChecksum(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="pdl_test_torrent_")
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.db = DownloadDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_torrent_task_lifecycle(self):
        task = TorrentDownloadTask(
            task_id="tor001",
            url="magnet:?xt=urn:btih:abcdef1234567890&dn=Test+Torrent",
            save_path=self.temp_dir
        )
        task.prepare()
        self.assertEqual(task.name, "Test Torrent")
        self.assertTrue(task.is_torrent)
        self.assertEqual(task.status, "queued")

        task.set_sequential(True)
        self.assertTrue(task.sequential)

        task.pause()
        self.assertEqual(task.status, "paused")

        task.cancel()
        self.assertEqual(task.status, "cancelled")

    def test_rss_feed_parsing_and_filtering(self):
        items = parse_rss_feed(SAMPLE_RSS_XML)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0].title, "Ubuntu 24.04 Desktop AMD64 ISO")
        self.assertTrue(items[0].link.startswith("magnet:?"))

        # Match Ubuntu releases
        matched_ubuntu = filter_rss_items(items, r"Ubuntu.*ISO")
        self.assertEqual(len(matched_ubuntu), 1)
        self.assertEqual(matched_ubuntu[0].guid, "ubuntu-24-04-iso")

        # Match Debian or Arch
        matched_multi = filter_rss_items(items, r"(Debian|Arch)")
        self.assertEqual(len(matched_multi), 2)

    def test_rss_watcher_check_feed_deduplication(self):
        watcher = TorrentRSSWatcher()
        feed = TorrentRSSFeed(
            feed_id="f1",
            name="Linux Feed",
            url="https://tracker.example.com/rss",
            filter_pattern=r"Ubuntu"
        )

        with patch.object(watcher, "fetch_feed", return_value=parse_rss_feed(SAMPLE_RSS_XML)):
            # First run detects new item
            new_items = watcher.check_feed(feed)
            self.assertEqual(len(new_items), 1)
            self.assertEqual(new_items[0].title, "Ubuntu 24.04 Desktop AMD64 ISO")

            # Second run with same seen GUID returns empty
            dup_items = watcher.check_feed(feed)
            self.assertEqual(len(dup_items), 0)

    def test_file_checksum_computation_and_verification(self):
        test_file = os.path.join(self.temp_dir, "sample_payload.bin")
        payload = b"P-Downloader Verified Chunk Data Block" * 50
        with open(test_file, "wb") as f:
            f.write(payload)

        # Expected SHA-256
        import hashlib
        expected_sha256 = hashlib.sha256(payload).hexdigest()
        expected_md5 = hashlib.md5(payload).hexdigest()
        expected_sha1 = hashlib.sha1(payload).hexdigest()

        # Test compute
        self.assertEqual(compute_file_checksum(test_file, "sha256"), expected_sha256)
        self.assertEqual(compute_file_checksum(test_file, "md5"), expected_md5)

        # Test verify
        ok_sha, actual, algo = verify_file_checksum(test_file, expected_sha256)
        self.assertTrue(ok_sha)
        self.assertEqual(algo, "sha256")

        ok_md5, actual, algo = verify_file_checksum(test_file, expected_md5)
        self.assertTrue(ok_md5)
        self.assertEqual(algo, "md5")

        ok_sha1, actual, algo = verify_file_checksum(test_file, expected_sha1)
        self.assertTrue(ok_sha1)
        self.assertEqual(algo, "sha1")

        # Test mismatch
        bad_sha, _, _ = verify_file_checksum(test_file, "0000000000000000000000000000000000000000000000000000000000000000")
        self.assertFalse(bad_sha)

    def test_engine_routes_and_resumes_torrent(self):
        engine = DownloadEngine(self.db)
        save_path = os.path.join(self.temp_dir, "my_torrent")

        task = engine.create_download(
            url="magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567&dn=SampleVideo.mp4",
            filename="SampleVideo.mp4",
            save_path=save_path,
            auto_start=False
        )

        self.assertTrue(getattr(task, "is_torrent", False))
        row = self.db.get_download(task.task_id)
        self.assertEqual(row["kind"], "torrent")

        # Resume restores TorrentDownloadTask
        engine.tasks.clear()
        engine.resume_download(task.task_id)
        resumed = engine.tasks[task.task_id]
        self.assertTrue(getattr(resumed, "is_torrent", False))


if __name__ == "__main__":
    unittest.main()
