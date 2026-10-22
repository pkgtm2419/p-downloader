"""
High-Precision Token Bucket Speed Limiter for P-Downloader.
Allows throttling download speeds globally or per-download task
to ensure bandwidth sharing with streaming, browsing, or gaming.
"""
import time
import threading

class SpeedLimiter:
    def __init__(self, limit_bytes_per_sec: int = 0):
        """
        limit_bytes_per_sec: maximum bytes allowed per second (0 or negative means Unlimited)
        """
        self.limit = max(0, limit_bytes_per_sec)
        self.tokens = float(self.limit)
        self.last_update = time.time()
        self._lock = threading.Lock()

    def set_limit(self, limit_bytes_per_sec: int):
        with self._lock:
            self.limit = max(0, limit_bytes_per_sec)
            self.tokens = float(self.limit)
            self.last_update = time.time()

    def acquire(self, byte_count: int):
        """
        Acquires permission to process byte_count bytes.
        Sleeps if necessary to maintain rate limit.
        """
        if self.limit <= 0:
            return  # Unlimited

        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now

            # Replenish tokens based on elapsed time
            self.tokens = min(float(self.limit), self.tokens + elapsed * self.limit)

            if self.tokens >= byte_count:
                self.tokens -= byte_count
                return

            # Need to wait
            deficit = byte_count - self.tokens
            sleep_time = deficit / self.limit
            self.tokens = 0.0

        if sleep_time > 0:
            time.sleep(min(sleep_time, 1.0))
