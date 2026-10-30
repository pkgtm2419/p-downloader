"""
Stress test for ResourceController under concurrent multi-threaded contention.
"""
import time
import threading
import unittest
from core.resource_controller import ResourceController

class TestResourceStress(unittest.TestCase):
    def test_concurrent_stream_allocation_stress(self):
        """50 worker threads contending for permits never exceed global and origin limits."""
        controller = ResourceController(
            max_global_streams=10,
            max_streams_per_origin=4,
            max_streams_per_task=4
        )

        max_observed_global = 0
        max_observed_origin = 0
        lock = threading.Lock()
        stop_event = threading.Event()

        def worker(worker_id: int):
            nonlocal max_observed_global, max_observed_origin
            origin = f"https://origin-{worker_id % 3}.com"
            for _ in range(20):
                if stop_event.is_set():
                    break
                permit = controller.acquire_stream(f"task-{worker_id}", origin, timeout_s=0.2)
                if permit:
                    with lock:
                        cur_global = controller._active_streams
                        cur_origin = controller._origin_streams.get(origin, 0)
                        max_observed_global = max(max_observed_global, cur_global)
                        max_observed_origin = max(max_observed_origin, cur_origin)
                    time.sleep(0.005)
                    permit.release()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertLessEqual(max_observed_global, 10)
        self.assertLessEqual(max_observed_origin, 4)
        self.assertEqual(controller._active_streams, 0)


if __name__ == "__main__":
    unittest.main()
