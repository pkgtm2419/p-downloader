"""
Unit tests for standard error taxonomy (IM-05).
"""
import unittest

from core.errors import AppError, ErrorCode


class TestErrorTaxonomy(unittest.TestCase):
    def test_error_attributes_and_defaults(self):
        err = AppError(ErrorCode.DRM_PROTECTED)
        self.assertEqual(err.code, ErrorCode.DRM_PROTECTED)
        self.assertFalse(err.retryable)
        self.assertIn("DRM", err.message)
        self.assertIn("[DRM_PROTECTED]", str(err))

        d = err.to_dict()
        self.assertEqual(d["code"], "DRM_PROTECTED")
        self.assertFalse(d["retryable"])

    def test_retryable_network_errors(self):
        err_timeout = AppError(ErrorCode.NETWORK_TIMEOUT)
        self.assertTrue(err_timeout.retryable)

        err_429 = AppError(ErrorCode.HTTP_429_503, details={"retry_after": 30})
        self.assertTrue(err_429.retryable)
        self.assertEqual(err_429.details["retry_after"], 30)

    def test_custom_message_and_details(self):
        err = AppError(
            ErrorCode.STREAM_URL_EXPIRED,
            message="Token expired at 12:00",
            details={"url": "https://example.com/live"},
            user_action="Click refresh to re-acquire manifest"
        )
        self.assertEqual(err.message, "Token expired at 12:00")
        self.assertEqual(err.user_action, "Click refresh to re-acquire manifest")
        self.assertEqual(err.details["url"], "https://example.com/live")


if __name__ == "__main__":
    unittest.main()
