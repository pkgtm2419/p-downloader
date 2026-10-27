import unittest
import tempfile
import os
import shutil
from unittest.mock import MagicMock
from core.db import DownloadDB
from core.scheduler_service import SchedulerService

class TestSchedulerService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_sched.db")
        self.db = DownloadDB(self.db_path)

        self.mock_engine = MagicMock()
        self.mock_engine.db = self.db
        self.mock_engine.tasks = {}

        self.scheduler = SchedulerService(self.mock_engine)

    def tearDown(self):
        self.scheduler.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_time_matches(self):
        self.assertTrue(self.scheduler._time_matches("14:30:15", "14:30:00"))
        self.assertTrue(self.scheduler._time_matches("02:00:00", "02:00"))
        self.assertFalse(self.scheduler._time_matches("14:31:00", "14:30:00"))

    def test_manage_concurrency(self):
        self.db.set_setting("simultaneous_downloads", "2")

        task1 = MagicMock(task_id="t1", status="downloading")
        task2 = MagicMock(task_id="t2", status="paused")
        task3 = MagicMock(task_id="t3", status="paused")

        self.mock_engine.tasks = {"t1": task1, "t2": task2, "t3": task3}

        self.scheduler._manage_concurrency()
        # Should resume task2 because active count (1) < limit (2)
        self.mock_engine.resume_download.assert_called_once_with("t2")

    def test_completion_detection(self):
        self.scheduler._had_active_downloads = True
        self.scheduler._completion_handled = False

        task1 = MagicMock(task_id="t1", status="completed")
        self.mock_engine.tasks = {"t1": task1}

        self.db.set_setting("sched_action_exit", "0")
        self.db.set_setting("sched_action_shutdown", "0")

        self.scheduler._check_completion()
        self.assertTrue(self.scheduler._completion_handled)

if __name__ == "__main__":
    unittest.main()
