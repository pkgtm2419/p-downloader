"""
Unit tests for HTTP error classification and retry policy.
"""
import unittest
from core.http_errors import classify_response, parse_retry_after, TransferError
from core.retry_policy import RetryPolicy, next_retry_delay

class TestRetryPolicy(unittest.TestCase):
    def test_parse_retry_after_seconds(self):
        """Integer seconds in Retry-After are parsed accurately."""
        self.assertEqual(parse_retry_after("15"), 15.0)
        self.assertIsNone(parse_retry_after(""))

    def test_classify_429_rate_limited(self):
        """HTTP 429 is classified as retryable with Retry-After parsed."""
        err = classify_response(status_code=429, headers={"Retry-After": "5"})
        self.assertEqual(err.code, "RATE_LIMITED")
        self.assertTrue(err.retryable)
        self.assertEqual(err.retry_after_s, 5.0)

    def test_classify_503_service_unavailable(self):
        """HTTP 503 is classified as retryable."""
        err = classify_response(status_code=503)
        self.assertEqual(err.code, "SERVICE_UNAVAILABLE")
        self.assertTrue(err.retryable)

    def test_classify_401_403_auth_required(self):
        """HTTP 401/403 are classified as non-retryable requiring credentials."""
        err401 = classify_response(status_code=401)
        self.assertEqual(err401.code, "AUTH_REQUIRED")
        self.assertFalse(err401.retryable)

        err403 = classify_response(status_code=403)
        self.assertEqual(err403.code, "AUTH_REQUIRED")
        self.assertFalse(err403.retryable)

    def test_classify_404_410_terminal(self):
        """HTTP 404/410 are terminal errors."""
        err = classify_response(status_code=404)
        self.assertEqual(err.code, "NOT_FOUND_OR_EXPIRED")
        self.assertFalse(err.retryable)

    def test_classify_timeout_exception(self):
        """Timeout exception is retryable."""
        err = classify_response(exception=TimeoutError("Request timed out"))
        self.assertEqual(err.code, "TIMEOUT")
        self.assertTrue(err.retryable)

    def test_next_retry_delay_exponential_and_cap(self):
        """Retry delays grow exponentially up to max_delay_s."""
        policy = RetryPolicy(max_attempts=3, initial_delay_s=1.0, max_delay_s=10.0, jitter=0.0)
        d0 = next_retry_delay(0, policy=policy)
        d1 = next_retry_delay(1, policy=policy)
        d2 = next_retry_delay(2, policy=policy)
        d3 = next_retry_delay(3, policy=policy)  # Exceeded max_attempts

        self.assertEqual(d0, 1.0)
        self.assertEqual(d1, 2.0)
        self.assertEqual(d2, 4.0)
        self.assertIsNone(d3)

    def test_next_retry_delay_honors_retry_after(self):
        """Server-specified Retry-After is respected up to max_delay_s."""
        policy = RetryPolicy(max_attempts=5, max_delay_s=20.0)
        delay = next_retry_delay(0, retry_after=7.5, policy=policy)
        self.assertEqual(delay, 7.5)


if __name__ == "__main__":
    unittest.main()
