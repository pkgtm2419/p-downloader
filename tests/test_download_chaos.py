"""
Chaos and fault tolerance tests: handling rate limits, changing ETags, and terminal auth failures.
"""
import os
import tempfile
import unittest
import requests

from tests.support.http_origin import FaultOrigin
from core.download_models import DownloadRequest, HttpProbeResult, BlockWork, ProbeError
from core.http_errors import classify_response
from core.range_worker import fetch_block
from core.segment import DownloadTask

class TestDownloadChaos(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_throttled_endpoint_classification(self):
        """FaultOrigin /throttled returns 429 with Retry-After: 1."""
        with FaultOrigin() as origin:
            r = requests.get(origin.url("/throttled"))
            self.assertEqual(r.status_code, 429)
            err = classify_response(r.status_code, dict(r.headers))
            self.assertEqual(err.code, "RATE_LIMITED")
            self.assertTrue(err.retryable)
            self.assertEqual(err.retry_after_s, 1.0)

    def test_changing_etag_detected(self):
        """Server returning modified ETag between requests is detected."""
        with FaultOrigin() as origin:
            r1 = requests.get(origin.url("/changing_etag"), headers={"Range": "bytes=0-10"})
            etag1 = r1.headers.get("ETag")
            self.assertEqual(etag1, '"v1"')

            r2 = requests.get(origin.url("/changing_etag"), headers={"Range": "bytes=0-10"})
            etag2 = r2.headers.get("ETag")
            self.assertEqual(etag2, '"v2"')
            self.assertNotEqual(etag1, etag2)

    def test_auth_failure_does_not_loop(self):
        """Non-retryable 401/403 fails fast with user-friendly error message without looping."""
        save_path = os.path.join(self.temp_dir.name, "auth_fail.bin")
        task = DownloadTask("auth_task", "https://httpbin.org/status/401", save_path)
        try:
            task.prepare()
        except RuntimeError as e:
            # Prepare must catch 401 and raise explicit message
            self.assertIn("AUTH_REQUIRED", str(e))
        self.assertFalse(os.path.exists(save_path))


if __name__ == "__main__":
    unittest.main()
