"""
Integration tests for multi-network routing and graceful adapter failover.
"""
import os
import tempfile
import unittest
from tests.support.http_origin import FaultOrigin
from core.download_models import DownloadRequest, BlockWork
from core.network_routes import NetworkRoute, get_session_for_route
from core.range_worker import fetch_block
from core.transfer_store import BoundedBlockWriter

class TestMultiNetwork(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_multi_route_block_transfers(self):
        """Separate blocks can be retrieved through designated routes and written to staging sink."""
        with FaultOrigin() as origin:
            staging = os.path.join(self.temp_dir.name, "multi.part")
            writer = BoundedBlockWriter(staging)

            route_a = NetworkRoute(id="route-a", device="adapter1", source_ip="0.0.0.0", address_family="ipv4")
            route_b = NetworkRoute(id="route-b", device="adapter2", source_ip="0.0.0.0", address_family="ipv4")

            req = DownloadRequest(url=origin.url("/normal"))
            from core.http_probe import probe_http
            probe = probe_http(req)

            # Block 0 on Route A
            work0 = BlockWork(block_id=0, start=0, end_exclusive=1000)
            w0 = fetch_block(req, probe, work0, route_id=route_a.id, sink=writer)
            self.assertEqual(w0, 1000)

            # Block 1 on Route B
            work1 = BlockWork(block_id=1, start=1000, end_exclusive=2000)
            w1 = fetch_block(req, probe, work1, route_id=route_b.id, sink=writer)
            self.assertEqual(w1, 1000)

            writer.close()
            with open(staging, "rb") as f:
                data = f.read(2000)
            self.assertEqual(data, origin.payload_normal[:2000])


if __name__ == "__main__":
    unittest.main()
