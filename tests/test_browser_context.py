"""
Unit tests for browser context origin scoping and header injection defense.
"""
import unittest
from core.download_models import BrowserRequestContext
from core.browser_context import headers_for_target

class TestBrowserContext(unittest.TestCase):
    def test_headers_same_origin(self):
        """Cookies and auth headers are preserved for same-origin requests."""
        ctx = BrowserRequestContext(
            user_agent="TestBrowser/1.0",
            referrer="https://example.com/page",
            per_origin_headers={
                "https://example.com": {
                    "Cookie": "session=secret_123",
                    "Authorization": "Bearer token_abc"
                }
            }
        )
        hdrs = headers_for_target(ctx, "https://example.com/download.zip")
        self.assertEqual(hdrs["User-Agent"], "TestBrowser/1.0")
        self.assertEqual(hdrs["Cookie"], "session=secret_123")
        self.assertEqual(hdrs["Authorization"], "Bearer token_abc")

    def test_headers_cross_origin_redirect_drops_auth(self):
        """Cookies and Authorization are dropped when redirected to an untrusted third-party host."""
        ctx = BrowserRequestContext(
            user_agent="TestBrowser/1.0",
            per_origin_headers={
                "https://example.com": {
                    "Cookie": "session=secret_123",
                    "Authorization": "Bearer token_abc"
                }
            }
        )
        # Redirected from example.com to cdn.other.com
        hdrs = headers_for_target(
            ctx,
            target_url="https://cdn.other.com/file.zip",
            redirect_from="https://example.com/download.zip"
        )
        self.assertNotIn("Cookie", hdrs)
        self.assertNotIn("Authorization", hdrs)
        self.assertEqual(hdrs["User-Agent"], "TestBrowser/1.0")

    def test_disallowed_headers_filtered(self):
        """Dangerous headers (Host, Content-Length) are never overridden."""
        ctx = BrowserRequestContext(
            per_origin_headers={
                "https://example.com": {
                    "Host": "evil.com",
                    "Content-Length": "9999",
                    "X-Custom-Header": "Allowed"
                }
            }
        )
        hdrs = headers_for_target(ctx, "https://example.com/file.zip")
        self.assertNotIn("Host", hdrs)
        self.assertNotIn("Content-Length", hdrs)
        self.assertEqual(hdrs["X-Custom-Header"], "Allowed")

    def test_crlf_header_injection_sanitized(self):
        """CRLF injection characters are stripped from header values."""
        ctx = BrowserRequestContext(
            user_agent="Mozilla/5.0\r\nInjected-Header: evil"
        )
        hdrs = headers_for_target(ctx, "https://example.com/file.zip")
        self.assertNotIn("\r", hdrs["User-Agent"])
        self.assertNotIn("\n", hdrs["User-Agent"])


if __name__ == "__main__":
    unittest.main()
