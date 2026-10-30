"""
Unit tests for BlockScheduler and block planning.
"""
import unittest
from core.download_models import BlockWork
from core.block_scheduler import plan_blocks, BlockScheduler

class TestBlockScheduler(unittest.TestCase):
    def test_plan_blocks_zero_bytes(self):
        """0-byte file produces a single 0-length block."""
        blocks = plan_blocks(0)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].start, 0)
        self.assertEqual(blocks[0].end_exclusive, 0)

    def test_plan_blocks_unknown_length(self):
        """Unknown length (None) produces a single open-ended block."""
        blocks = plan_blocks(None)
        self.assertEqual(len(blocks), 1)
        self.assertIsNone(blocks[0].end_exclusive)

    def test_plan_blocks_slicing(self):
        """Known length file is sliced into contiguous non-overlapping blocks."""
        total = 10 * 1024 * 1024  # 10 MiB -> 1 MiB blocks
        blocks = plan_blocks(total)
        self.assertEqual(len(blocks), 10)
        self.assertEqual(blocks[0].start, 0)
        self.assertEqual(blocks[0].end_exclusive, 1024 * 1024)
        self.assertEqual(blocks[-1].end_exclusive, total)

        # Verify continuity
        for i in range(len(blocks) - 1):
            self.assertEqual(blocks[i].end_exclusive, blocks[i+1].start)

    def test_scheduler_claim_and_complete(self):
        """Claiming blocks dequeues them and completing updates progress."""
        blocks = plan_blocks(4 * 1024 * 1024)
        sched = BlockScheduler(blocks)
        self.assertFalse(sched.is_complete())

        # Claim blocks
        claimed = []
        while work := sched.claim_next():
            claimed.append(work)

        self.assertEqual(len(claimed), len(blocks))
        self.assertIsNone(sched.claim_next())  # Empty queue

        # Complete each
        for work in claimed:
            size = work.end_exclusive - work.start
            sched.complete(work.block_id, size)

        self.assertTrue(sched.is_complete())
        dl, total = sched.progress()
        self.assertEqual(dl, 4 * 1024 * 1024)
        self.assertEqual(total, 4 * 1024 * 1024)

    def test_scheduler_return_remaining_reclaims_block(self):
        """Returning uncompleted work re-enqueues block with updated durable bytes."""
        blocks = [BlockWork(0, 0, 1000)]
        sched = BlockScheduler(blocks)

        work = sched.claim_next()
        self.assertIsNotNone(work)
        self.assertIsNone(sched.claim_next())

        # Return with partial progress 500 bytes
        sched.return_remaining(work.block_id, durable_bytes=500)

        # Reclaim should yield block with durable_bytes = 500
        reclaimed = sched.claim_next()
        self.assertIsNotNone(reclaimed)
        self.assertEqual(reclaimed.durable_bytes, 500)


if __name__ == "__main__":
    unittest.main()
