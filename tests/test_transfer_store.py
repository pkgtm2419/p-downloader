"""
Unit tests for BoundedBlockWriter, TransferStore, and atomic staging publish.
"""
import os
import hashlib
import tempfile
import unittest
from core.db import init_db
from core.transfer_store import TransferState, BoundedBlockWriter, TransferStore

class TestTransferStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_transfer.db")
        self.conn = init_db(self.db_path)
        self.store = TransferStore(self.conn)

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_writer_direct_seek_and_flush(self):
        """BoundedBlockWriter writes bytes at designated offset without overwriting other regions."""
        staging = os.path.join(self.temp_dir.name, "staging.part")
        writer = BoundedBlockWriter(staging)
        writer.write_at(100, b"BLOCK_AT_100")
        writer.flush_checkpoint()
        writer.close()

        with open(staging, "rb") as f:
            f.seek(100)
            data = f.read(12)
        self.assertEqual(data, b"BLOCK_AT_100")

    def test_checkpoint_and_load(self):
        """TransferState is saved to disk meta file and SQLite journal, then restored."""
        staging = os.path.join(self.temp_dir.name, "sample.part")
        state = TransferState(
            task_id="task_123",
            destination=os.path.join(self.temp_dir.name, "sample.bin"),
            staging_path=staging,
            total_bytes=1024,
            downloaded_bytes=512,
            etag='"v1-etag"',
            completed_blocks=[0, 1]
        )
        self.store.checkpoint("task_123", state)

        # Reload from store
        loaded = self.store.load("task_123", staging_path=staging)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.task_id, "task_123")
        self.assertEqual(loaded.downloaded_bytes, 512)
        self.assertEqual(loaded.completed_blocks, [0, 1])

    def test_publish_atomic_rename(self):
        """Publish moves staging file to destination and cleans up journal."""
        staging = os.path.join(self.temp_dir.name, "pub.part")
        dest = os.path.join(self.temp_dir.name, "pub.bin")
        payload = b"PUBLISHED_DATA_CONTENT_12345"
        with open(staging, "wb") as f:
            f.write(payload)

        state = TransferState(
            task_id="pub_task",
            destination=dest,
            staging_path=staging,
            total_bytes=len(payload),
            downloaded_bytes=len(payload)
        )
        self.store.checkpoint("pub_task", state)

        final_path = self.store.publish("pub_task", state, expected_bytes=len(payload))
        self.assertEqual(final_path, dest)
        self.assertTrue(os.path.exists(dest))
        self.assertFalse(os.path.exists(staging))
        with open(dest, "rb") as f:
            self.assertEqual(f.read(), payload)

    def test_publish_checksum_validation(self):
        """Publish validates expected SHA-256 and rejects corrupted file."""
        staging = os.path.join(self.temp_dir.name, "hash.part")
        dest = os.path.join(self.temp_dir.name, "hash.bin")
        payload = b"INTEGRITY_CHECK_SAMPLE_BYTES"
        with open(staging, "wb") as f:
            f.write(payload)

        correct_sha = hashlib.sha256(payload).hexdigest()
        bad_sha = "0000000000000000000000000000000000000000000000000000000000000000"

        state = TransferState(
            task_id="hash_task",
            destination=dest,
            staging_path=staging,
            total_bytes=len(payload),
            downloaded_bytes=len(payload)
        )

        # Bad hash must raise ValueError and keep staging file safe
        with self.assertRaises(ValueError):
            self.store.publish("hash_task", state, checksum_sha256=bad_sha)
        self.assertTrue(os.path.exists(staging))

        # Good hash must succeed
        final_dest = self.store.publish("hash_task", state, checksum_sha256=correct_sha)
        self.assertEqual(final_dest, dest)
        self.assertTrue(os.path.exists(dest))

    def test_resolve_unique_destination_duplicate_prevention(self):
        """Existing file at destination path is not overwritten; duplicate suffix is applied."""
        dest = os.path.join(self.temp_dir.name, "myfile.zip")
        with open(dest, "w") as f:
            f.write("original")

        resolved = self.store.resolve_unique_destination(dest)
        expected = os.path.join(self.temp_dir.name, "myfile (1).zip")
        self.assertEqual(resolved, expected)


if __name__ == "__main__":
    unittest.main()
