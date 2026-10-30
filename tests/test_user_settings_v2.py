"""
Tests for v2 user settings, persistence, migrations, and resource snapshot interfaces.
"""
import unittest
from core.db import DownloadDB
from core.resource_controller import ResourceController, ResourceSnapshot

class TestUserSettingsV2(unittest.TestCase):
    def setUp(self):
        self.db = DownloadDB(":memory:")
        self.rc = ResourceController(
            max_active_downloads=3,
            max_global_streams=32,
            max_streams_per_task=16,
            max_streams_per_origin=8,
            max_streams_per_route=8
        )

    def test_resource_snapshot_contract(self):
        """ResourceSnapshot must provide required throughput, route traffic, buffer, and error metrics."""
        snap = self.rc.snapshot()
        self.assertTrue(hasattr(snap, "active_streams") or hasattr(snap, "activeStreams"))
        self.assertTrue(hasattr(snap, "throughput"))
        self.assertTrue(hasattr(snap, "perRouteTraffic"))
        self.assertTrue(hasattr(snap, "bufferedBytes"))
        self.assertTrue(hasattr(snap, "diskQueueBytes"))
        self.assertTrue(hasattr(snap, "errorCode"))

    def test_user_settings_persistence(self):
        """V2 user settings persist and reload cleanly from DB."""
        self.db.set_setting("connection_mode", "fixed")
        self.db.set_setting("max_active_downloads", "5")
        self.db.set_setting("max_global_streams", "48")
        self.db.set_setting("global_rate_bps", "5000000")
        self.db.set_setting("capture_mode", "auto")

        self.assertEqual(self.db.get_setting("connection_mode"), "fixed")
        self.assertEqual(int(self.db.get_setting("max_active_downloads")), 5)
        self.assertEqual(int(self.db.get_setting("max_global_streams")), 48)
        self.assertEqual(int(self.db.get_setting("global_rate_bps")), 5000000)
        self.assertEqual(self.db.get_setting("capture_mode"), "auto")

    def test_legacy_settings_compatibility(self):
        """Older DB with missing v2 settings returns expected sensible defaults."""
        mode = self.db.get_setting("connection_mode", default="auto")
        self.assertEqual(mode, "auto")
        max_active = int(self.db.get_setting("max_active_downloads", default="3"))
        self.assertEqual(max_active, 3)


if __name__ == "__main__":
    unittest.main()
