"""
Unit and integration tests for strict HTTP probing and metadata contracts.
"""
import unittest
from tests.support.http_origin import FaultOrigin
from core.download_models import DownloadRequest, BrowserRequestContext, ProbeError
from core.http_probe import probe_http, parse_content_disposition
from core.segment import probe_url

class TestHttpProbe(unittest.TestCase):
    def test_probe_normal_range(self):
        """Verified 206 response correctly detects range support and total file size."""
        with FaultOrigin() as origin:
            req = DownloadRequest(url=origin.url("/normal"))
            res = probe_http(req)
            self.assertTrue(res.supports_ranges)
            self.assertEqual(res.total_bytes, len(origin.payload_normal))
            self.assertEqual(res.filename, "normal")

    def test_probe_range_ignored_server_marked_non_splittable(self):
        """Lying server returning HTTP 200 to Range request MUST NOT be marked splittable."""
        with FaultOrigin() as origin:
            req = DownloadRequest(url=origin.url("/range_ignored"))
            res = probe_http(req)
            self.assertFalse(res.supports_ranges)
            self.assertEqual(res.total_bytes, len(origin.payload_normal))

    def test_probe_wrong_content_range_marked_non_splittable(self):
        """Contradictory Content-Range response must not be trusted for multi-stream splitting."""
        with FaultOrigin() as origin:
            req = DownloadRequest(url=origin.url("/wrong_content_range"))
            res = probe_http(req)
            self.assertFalse(res.supports_ranges)

    def test_probe_empty_body(self):
        """Empty 0-byte file (416 */0 or 200 with 0 bytes) resolves to total_bytes=0."""
        with FaultOrigin() as origin:
            req = DownloadRequest(url=origin.url("/empty"))
            res = probe_http(req)
            self.assertEqual(res.total_bytes, 0)
            self.assertFalse(res.supports_ranges)

    def test_probe_unknown_length_stream(self):
        """Streaming response without Content-Length resolves total_bytes=None and non-splittable."""
        with FaultOrigin() as origin:
            req = DownloadRequest(url=origin.url("/unknown_length"))
            res = probe_http(req)
            self.assertIsNone(res.total_bytes)
            self.assertFalse(res.supports_ranges)

    def test_rfc5987_filename_parsing(self):
        """RFC 5987 encoded filenames are parsed and URL-decoded."""
        cd = "attachment; filename*=UTF-8''important%20report%202026.pdf"
        self.assertEqual(parse_content_disposition(cd), "important report 2026.pdf")

    def test_path_traversal_filename_sanitization(self):
        """Path traversal characters in Content-Disposition are neutralized."""
        cd = 'attachment; filename="../../../etc/passwd"'
        self.assertEqual(parse_content_disposition(cd), "passwd")

    def test_probe_unsupported_scheme(self):
        """Non-HTTP/HTTPS URLs raise UNSUPPORTED_SCHEME ProbeError."""
        req = DownloadRequest(url="ftp://ftp.example.com/file.zip")
        with self.assertRaises(ProbeError) as ctx:
            probe_http(req)
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_SCHEME")

    def test_probe_url_legacy_compatibility(self):
        """core.segment.probe_url returns compatible dict for GUI callers."""
        with FaultOrigin() as origin:
            res = probe_url(origin.url("/normal"))
            self.assertIn("url", res)
            self.assertIn("final_url", res)
            self.assertIn("filename", res)
            self.assertIn("total_bytes", res)
            self.assertIn("supports_range", res)
            self.assertTrue(res["supports_range"])
            self.assertEqual(res["total_bytes"], len(origin.payload_normal))


if __name__ == "__main__":
    unittest.main()
