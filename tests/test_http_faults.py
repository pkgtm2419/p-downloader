"""
Regression tests for HTTP fault handling, range compliance, and download integrity.
Uses local FaultOrigin fixture without external internet dependencies.
"""
import os
import time
import tempfile
import hashlib
import unittest
import requests

from tests.support.http_origin import FaultOrigin
from core.segment import DownloadTask, probe_url

class TestFaultOriginDirect(unittest.TestCase):
    """Direct validation of the FaultOrigin test fixture behaviors."""

    def test_fixture_normal_range(self):
        with FaultOrigin() as origin:
            r = requests.get(origin.url("/normal"), headers={"Range": "bytes=0-9"})
            self.assertEqual(r.status_code, 206)
            self.assertEqual(r.headers.get("Content-Range"), f"bytes 0-9/{len(origin.payload_normal)}")
            self.assertEqual(len(r.content), 10)
            self.assertEqual(r.content, origin.payload_normal[:10])

    def test_fixture_range_ignored(self):
        with FaultOrigin() as origin:
            r = requests.get(origin.url("/range_ignored"), headers={"Range": "bytes=100-199"})
            # Returns 200 OK with full payload instead of 206
            self.assertEqual(r.status_code, 200)
            self.assertEqual(len(r.content), len(origin.payload_normal))

    def test_fixture_wrong_content_range(self):
        with FaultOrigin() as origin:
            r = requests.get(origin.url("/wrong_content_range"), headers={"Range": "bytes=0-9"})
            self.assertEqual(r.status_code, 206)
            self.assertIn("9999-10009", r.headers.get("Content-Range", ""))

    def test_fixture_empty_body(self):
        with FaultOrigin() as origin:
            r = requests.get(origin.url("/empty"))
            self.assertEqual(r.status_code, 200)
            self.assertEqual(len(r.content), 0)

            r_range = requests.get(origin.url("/empty"), headers={"Range": "bytes=0-0"})
            self.assertEqual(r_range.status_code, 416)


class TestDownloadIntegrityFaults(unittest.TestCase):
    """
    Integration tests against DownloadTask to verify data integrity under fault conditions.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_empty_body_finishes(self):
        """0-byte downloads must complete cleanly with a 0-byte file without hanging."""
        with FaultOrigin() as origin:
            save_path = os.path.join(self.temp_dir.name, "empty.bin")
            task = DownloadTask("empty_test", origin.url("/empty"), save_path, connections=1)
            task.prepare()
            task.start()

            for _ in range(50):
                if task.status in ("completed", "error"):
                    break
                time.sleep(0.05)

            self.assertEqual(task.status, "completed")
            self.assertTrue(os.path.exists(save_path))
            self.assertEqual(os.path.getsize(save_path), 0)

    def test_interrupted_transfer_can_resume(self):
        """Interrupted connection can be resumed without corruption."""
        with FaultOrigin() as origin:
            save_path = os.path.join(self.temp_dir.name, "interrupted.bin")
            expected_sha = hashlib.sha256(origin.payload_normal).hexdigest()

            task = DownloadTask("interrupted_test", origin.url("/interrupted"), save_path, connections=1)
            task.prepare()
            task.start()

            # Wait for disconnect/error on first attempt
            for _ in range(50):
                if task.status in ("error", "paused"):
                    break
                time.sleep(0.05)

            # Now resume
            task.start()
            for _ in range(50):
                if task.status in ("completed", "error"):
                    break
                time.sleep(0.05)

            self.assertEqual(task.status, "completed")
            self.assertTrue(os.path.exists(save_path))
            with open(save_path, "rb") as f:
                actual_sha = hashlib.sha256(f.read()).hexdigest()
            self.assertEqual(actual_sha, expected_sha)

    def test_unknown_length_finishes_at_eof(self):
        """Unknown content length streams to EOF and finishes without corrupting length."""
        with FaultOrigin() as origin:
            save_path = os.path.join(self.temp_dir.name, "stream.bin")
            expected_sha = hashlib.sha256(origin.payload_normal).hexdigest()

            task = DownloadTask("stream_test", origin.url("/unknown_length"), save_path, connections=1)
            task.prepare()
            task.start()

            for _ in range(50):
                if task.status in ("completed", "error"):
                    break
                time.sleep(0.05)

            self.assertEqual(task.status, "completed")
            self.assertTrue(os.path.exists(save_path))
            with open(save_path, "rb") as f:
                actual_sha = hashlib.sha256(f.read()).hexdigest()
            self.assertEqual(actual_sha, expected_sha)


if __name__ == "__main__":
    unittest.main()
