"""
Unit tests for range worker and verified byte block transfers.
"""
import os
import tempfile
import threading
import unittest
from tests.support.http_origin import FaultOrigin
from core.download_models import DownloadRequest, HttpProbeResult, BlockWork, ProbeError
from core.range_worker import fetch_block
from core.transfer_store import BoundedBlockWriter

class TestRangeWorker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_fetch_block_normal(self):
        """Valid 206 response writes byte block to exact offset."""
        with FaultOrigin() as origin:
            req = DownloadRequest(url=origin.url("/normal"))
            probe = HttpProbeResult(
                final_url=origin.url("/normal"),
                total_bytes=len(origin.payload_normal),
                supports_ranges=True,
                etag='"v1-clean"'
            )
            staging = os.path.join(self.temp_dir.name, "test.part")
            writer = BoundedBlockWriter(staging)
            work = BlockWork(block_id=0, start=100, end_exclusive=200)

            written = fetch_block(req, probe, work, sink=writer)
            writer.close()

            self.assertEqual(written, 100)
            self.assertTrue(os.path.exists(staging))
            with open(staging, "rb") as f:
                f.seek(100)
                data = f.read(100)
            self.assertEqual(data, origin.payload_normal[100:200])

    def test_fetch_interior_block_rejects_http_200(self):
        """Server returning HTTP 200 to interior ranged request must raise INVALID_RANGE."""
        with FaultOrigin() as origin:
            req = DownloadRequest(url=origin.url("/range_ignored"))
            probe = HttpProbeResult(
                final_url=origin.url("/range_ignored"),
                total_bytes=len(origin.payload_normal),
                supports_ranges=True
            )
            staging = os.path.join(self.temp_dir.name, "test.part")
            writer = BoundedBlockWriter(staging)
            work = BlockWork(block_id=1, start=1000, end_exclusive=2000)

            with self.assertRaises(ProbeError) as ctx:
                fetch_block(req, probe, work, sink=writer)
            writer.close()

            self.assertEqual(ctx.exception.code, "INVALID_RANGE")

    def test_fetch_block_rejects_wrong_content_range(self):
        """Server returning contradictory Content-Range header raises INVALID_RANGE."""
        with FaultOrigin() as origin:
            req = DownloadRequest(url=origin.url("/wrong_content_range"))
            probe = HttpProbeResult(
                final_url=origin.url("/wrong_content_range"),
                total_bytes=len(origin.payload_normal),
                supports_ranges=True
            )
            staging = os.path.join(self.temp_dir.name, "test.part")
            writer = BoundedBlockWriter(staging)
            work = BlockWork(block_id=0, start=0, end_exclusive=10)

            with self.assertRaises(ProbeError) as ctx:
                fetch_block(req, probe, work, sink=writer)
            writer.close()

            self.assertEqual(ctx.exception.code, "INVALID_RANGE")

    def test_cooperative_cancellation(self):
        """Setting cancel event immediately halts chunk iteration."""
        with FaultOrigin() as origin:
            req = DownloadRequest(url=origin.url("/normal"))
            probe = HttpProbeResult(
                final_url=origin.url("/normal"),
                total_bytes=len(origin.payload_normal),
                supports_ranges=True
            )
            staging = os.path.join(self.temp_dir.name, "test.part")
            writer = BoundedBlockWriter(staging)
            cancel = threading.Event()
            cancel.set()  # Cancel before reading
            work = BlockWork(block_id=0, start=0, end_exclusive=1000)

            written = fetch_block(req, probe, work, cancel=cancel, sink=writer)
            writer.close()
            self.assertEqual(written, 0)


if __name__ == "__main__":
    unittest.main()
