"""
Unit tests for native host secret redaction and payload processing.
"""
import unittest
from browser_extension.pdownloader_native_host import redact_sensitive

class TestNativeHost(unittest.TestCase):
    def test_redact_sensitive_cleans_credentials(self):
        """Cookies, tokens, passwords, and auth headers are masked in logs."""
        payload = {
            "action": "download",
            "url": "https://example.com/file.zip",
            "cookie": "session_id=SECRET123; user=alice",
            "authorization": "Bearer secret-token-abc",
            "headers": {
                "User-Agent": "Mozilla/5.0",
                "Cookie": "secret=val",
                "X-Auth-Token": "secret_token_123"
            }
        }
        cleaned = redact_sensitive(payload)
        self.assertEqual(cleaned["cookie"], "[REDACTED]")
        self.assertEqual(cleaned["authorization"], "[REDACTED]")
        self.assertEqual(cleaned["headers"]["Cookie"], "[REDACTED]")
        self.assertEqual(cleaned["headers"]["X-Auth-Token"], "[REDACTED]")
        self.assertEqual(cleaned["headers"]["User-Agent"], "Mozilla/5.0")


if __name__ == "__main__":
    unittest.main()
