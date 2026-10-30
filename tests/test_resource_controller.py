"""
Unit tests for ResourceController and hierarchical budget enforcement.
"""
import unittest
from core.resource_controller import ResourceController

class TestResourceController(unittest.TestCase):
    def setUp(self):
        self.controller = ResourceController(
            max_active_downloads=2,
            max_global_streams=8,
            max_streams_per_task=4,
            max_streams_per_origin=3,
            max_streams_per_route=4
        )

    def test_acquire_and_release_stream(self):
        """Permit acquires stream and releases it upon context manager exit."""
        self.assertEqual(self.controller._active_streams, 0)
        with self.controller.acquire_stream("task1", "https://origin1.com") as permit:
            self.assertIsNotNone(permit)
            self.assertEqual(self.controller._active_streams, 1)

        self.assertEqual(self.controller._active_streams, 0)

    def test_per_origin_cap(self):
        """Origin stream cap prevents a single host from consuming all sockets."""
        permits = []
        for i in range(3):
            p = self.controller.acquire_stream("task1", "https://origin1.com", timeout_s=0.1)
            self.assertIsNotNone(p)
            permits.append(p)

        # 4th permit for same origin must be rejected (cap = 3)
        p_blocked = self.controller.acquire_stream("task1", "https://origin1.com", timeout_s=0.05)
        self.assertIsNone(p_blocked)

        # But another origin can still acquire!
        p_other = self.controller.acquire_stream("task2", "https://origin2.com", timeout_s=0.1)
        self.assertIsNotNone(p_other)
        permits.append(p_other)

        for p in permits:
            p.release()
        self.assertEqual(self.controller._active_streams, 0)

    def test_active_download_admission(self):
        """Admission gate respects max_active_downloads."""
        self.assertTrue(self.controller.register_download("t1"))
        self.assertTrue(self.controller.register_download("t2"))
        # 3rd is rejected
        self.assertFalse(self.controller.register_download("t3"))

        self.controller.unregister_download("t1")
        # Now t3 can be admitted
        self.assertTrue(self.controller.register_download("t3"))


if __name__ == "__main__":
    unittest.main()
