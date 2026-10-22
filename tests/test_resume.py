"""
Pause and resume integration test for P-Downloader.
"""
import os
import time
import unittest
from core.segment import DownloadTask
import zipfile

class TestPauseResume(unittest.TestCase):
    def test_pause_and_resume(self):
        url = "https://www.python.org/ftp/python/3.12.0/python-3.12.0-embed-amd64.zip"
        save_path = "d:\\p-downloader\\tests\\resume-test.zip"
        if os.path.exists(save_path):
            os.remove(save_path)

        task = DownloadTask(
            task_id="resumetest",
            url=url,
            save_path=save_path,
            connections=4
        )
        task.prepare()
        self.assertTrue(task.supports_range)
        self.assertGreater(task.total_bytes, 0)

        # Start download
        task.start()
        # Wait until some data has been downloaded
        for _ in range(50):
            if task.downloaded_bytes > 50000:
                break
            time.sleep(0.1)

        # Pause
        task.pause()
        self.assertEqual(task.status, "paused")
        downloaded_so_far = task.downloaded_bytes
        self.assertGreater(downloaded_so_far, 0)
        self.assertTrue(os.path.exists(task.meta_file))

        # Re-start/resume
        task.start()
        # Wait for completion
        for _ in range(60):
            if task.status == "completed":
                break
            time.sleep(0.5)

        self.assertEqual(task.status, "completed")
        self.assertEqual(task.downloaded_bytes, task.total_bytes)
        self.assertFalse(os.path.exists(task.meta_file))

        # Test archive integrity
        with zipfile.ZipFile(save_path, 'r') as zf:
            bad = zf.testzip()
            self.assertIsNone(bad)

        if os.path.exists(save_path):
            os.remove(save_path)

if __name__ == "__main__":
    unittest.main()
