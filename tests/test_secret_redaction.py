"""
Unit tests for secret redaction in logging and diagnostics.
"""
import unittest
from browser_extension.pdownloader_native_host import redact_sensitive

class TestSecretRedaction(unittest.TestCase):
    def test_recursive_dict_and_list_redaction(self):
        """Deep structures containing sensitive keys are redacted."""
        raw = {
            "id": 1,
            "auth": "password123",
            "items": [
                {"token": "secret_abc"},
                {"file": "document.pdf"}
            ],
            "nested": {
                "user_password": "supersecretpassword",
                "safe_field": 42
            }
        }
        clean = redact_sensitive(raw)
        self.assertEqual(clean["auth"], "[REDACTED]")
        self.assertEqual(clean["items"][0]["token"], "[REDACTED]")
        self.assertEqual(clean["items"][1]["file"], "document.pdf")
        self.assertEqual(clean["nested"]["user_password"], "[REDACTED]")
        self.assertEqual(clean["nested"]["safe_field"], 42)


if __name__ == "__main__":
    unittest.main()
