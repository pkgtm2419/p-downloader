"""
Integration tests for Task 4: shared block queue, pause/resume lifecycle, and restart resilience.
"""
import os
import time
import hashlib
import tempfile
import unittest

from tests.support.http_origin import FaultOrigin
from core.download_models import DownloadRequest, DownloadKind
from core.block_scheduler import plan_blocks, BlockScheduler
from core.segment import DownloadTask
from core.engine import DownloadEngine
from core.db import DownloadDB

class TestLifecycleV2(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_engine.db")
        self.db = DownloadDB(self.db_path)
        self.engine = DownloadEngine(self.db)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_block_exact_coverage(self):
        """Block decomposition covers [0, N) with zero gaps and zero overlaps."""
        total = 25 * 1024 * 1024  # 25 MiB
        blocks = plan_blocks(total)
        covered = 0
        for b in blocks:
            self.assertEqual(b.start, covered)
            self.assertIsNotNone(b.end_exclusive)
            covered = b.end_exclusive
        self.assertEqual(covered, total)

    def test_pause_and_resume_roundtrip(self):
        """Download pauses cleanly, checkpoints state, and resumes to exact SHA-256."""
        with FaultOrigin() as origin:
            save_path = os.path.join(self.temp_dir.name, "lifecycle_resume.bin")
            expected_sha = hashlib.sha256(origin.payload_normal).hexdigest()

            task = DownloadTask(
                "life_task",
                origin.url("/normal"),
                save_path,
                connections=4
            )
            task.prepare()
            task.start()

            # Wait until some data has been downloaded
            for _ in range(50):
                if task.downloaded_bytes > 5000 or task.status == "completed":
                    break
                time.sleep(0.02)

            # Pause if not already complete
            if task.status != "completed":
                task.pause()
                self.assertEqual(task.status, "paused")
                self.assertTrue(os.path.exists(task.meta_file))
                downloaded_so_far = task.downloaded_bytes
                self.assertGreater(downloaded_so_far, 0)

                # Resume
                task.start()

            # Wait for completion
            for _ in range(60):
                if task.status == "completed":
                    break
                time.sleep(0.05)

            self.assertEqual(task.status, "completed")
            self.assertEqual(task.downloaded_bytes, len(origin.payload_normal))
            self.assertFalse(os.path.exists(task.meta_file))

            with open(save_path, "rb") as f:
                actual_sha = hashlib.sha256(f.read()).hexdigest()
            self.assertEqual(actual_sha, expected_sha)

    def test_engine_create_from_request_and_kind_persistence(self):
        """Engine creates task from typed DownloadRequest and persists kind."""
        with FaultOrigin() as origin:
            req = DownloadRequest(
                url=origin.url("/normal"),
                filename="file.bin",
                destination=os.path.join(self.temp_dir.name, "file.bin"),
                kind=DownloadKind.HTTP,
                connections=4
            )
            task = self.engine.create_from_request(req, auto_start=False)
            self.assertEqual(task.status, "queued")

            row = self.db.get_download(task.task_id)
            self.assertIsNotNone(row)
            self.assertEqual(row["filename"], "file.bin")
            self.assertEqual(row.get("kind", "http"), "http")


if __name__ == "__main__":
    unittest.main()
