"""
Unit tests for centralized logging and canary secret redaction (IM-04).
Verifies rotating file logger and confirms sensitive tokens/passwords never leak to disk.
"""
import os
import logging
import tempfile
import unittest
import zipfile
from pathlib import Path

from core.logging_setup import (
    RedactionFilter, setup_logging, get_logger,
    register_redacted_secret, export_diagnostics, close_logging
)


class TestLoggingSetup(unittest.TestCase):
    def tearDown(self):
        close_logging()

    def test_redaction_filter_direct(self):
        rf = RedactionFilter(["MY_TOP_SECRET_CANARY_12345"])
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname=__file__, lineno=10,
            msg="User login with password=SecretPassword123! and token=ghp_ABC123456789XYZ and MY_TOP_SECRET_CANARY_12345",
            args=(), exc_info=None
        )
        rf.filter(record)
        self.assertNotIn("SecretPassword123!", record.msg)
        self.assertNotIn("ghp_ABC123456789XYZ", record.msg)
        self.assertNotIn("MY_TOP_SECRET_CANARY_12345", record.msg)
        self.assertIn("[REDACTED]", record.msg)
        self.assertIn("[REDACTED_CANARY]", record.msg)

    def test_canary_secret_not_written_to_file(self):
        td = tempfile.TemporaryDirectory()
        try:
            log_dir = Path(td.name)
            logger = setup_logging(log_dir=str(log_dir), level=logging.DEBUG)

            canary = "CANARY_TOKEN_987654321_DO_NOT_LEAK"
            register_redacted_secret(canary)

            logger.info(f"Connecting with Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test and {canary}")
            logger.warning("Failed request: https://example.com/api?token=secret_param_value&file=video.mp4")

            # Flush handlers
            for h in logging.getLogger().handlers:
                h.flush()

            log_file = log_dir / "pdownloader.log"
            self.assertTrue(log_file.is_file())
            content = log_file.read_text(encoding="utf-8")

            # Assert plain-text secrets never leaked
            self.assertNotIn(canary, content)
            self.assertNotIn("secret_param_value", content)
            self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", content)
        finally:
            close_logging()
            td.cleanup()

    def test_export_diagnostics(self):
        td = tempfile.TemporaryDirectory()
        try:
            log_dir = Path(td.name)
            setup_logging(log_dir=str(log_dir), level=logging.DEBUG)
            logger = get_logger("diag_test")
            logger.info("Diagnostics test log message")

            for h in logging.getLogger().handlers:
                h.flush()

            zip_path = os.path.join(td.name, "diag.zip")
            out_zip = export_diagnostics(target_zip=zip_path)
            self.assertTrue(os.path.isfile(out_zip))

            with zipfile.ZipFile(out_zip, "r") as zf:
                names = zf.namelist()
                self.assertIn("system_info.txt", names)
                sys_content = zf.read("system_info.txt").decode("utf-8")
                self.assertIn("Python:", sys_content)
        finally:
            close_logging()
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
