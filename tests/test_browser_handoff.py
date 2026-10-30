"""
Unit tests for browser handoff store and two-phase ownership state machine.
"""
import sqlite3
import unittest
from core.download_models import DownloadRequest
from core.browser_handoff import HandoffStore

class TestBrowserHandoff(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.store = HandoffStore(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_reserve_returns_prepared(self):
        """reserve() generates PREPARED offer with valid handoffId and expiresAt."""
        req = DownloadRequest(url="https://example.com/movie.mp4", filename="movie.mp4")
        offer = self.store.reserve(req, capture_id="cap_001", ttl_seconds=10.0)

        self.assertEqual(offer.state, "PREPARED")
        self.assertTrue(offer.handoff_id.startswith("hnd_"))
        self.assertGreater(offer.expires_at_utc, 0)
        self.assertIsNone(offer.task_id)

    def test_reserve_idempotency_on_capture_id(self):
        """Repeated reserve() calls with same capture_id return identical handoffId."""
        req = DownloadRequest(url="https://example.com/movie.mp4")
        offer1 = self.store.reserve(req, capture_id="cap_same")
        offer2 = self.store.reserve(req, capture_id="cap_same")

        self.assertEqual(offer1.handoff_id, offer2.handoff_id)
        self.assertEqual(offer1.state, offer2.state)

    def test_commit_persists_ownership_and_idempotent(self):
        """commit() transitions offer to COMMITTED and returns durable taskId idempotently."""
        req = DownloadRequest(url="https://example.com/file.zip")
        offer = self.store.reserve(req, capture_id="cap_commit")

        task_id1 = self.store.commit(offer.handoff_id)
        self.assertTrue(task_id1)

        # Repeating commit returns same task_id
        task_id2 = self.store.commit(offer.handoff_id)
        self.assertEqual(task_id1, task_id2)

        # Status check
        status = self.store.get_status(offer.handoff_id)
        self.assertIsNotNone(status)
        self.assertEqual(status.state, "COMMITTED")
        self.assertEqual(status.task_id, task_id1)

    def test_release_marks_released(self):
        """release() transitions state to RELEASED."""
        req = DownloadRequest(url="https://example.com/file.zip")
        offer = self.store.reserve(req, capture_id="cap_rel")
        self.store.release(offer.handoff_id)

        status = self.store.get_status(offer.handoff_id)
        self.assertEqual(status.state, "RELEASED")


if __name__ == "__main__":
    unittest.main()
