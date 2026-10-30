"""
Unit tests for adaptive concurrency policy controller.
"""
import unittest
from core.adaptive_concurrency import (
    StreamActionType,
    ConcurrencyPolicy,
    ConcurrencySnapshot,
    compute_actions
)

class TestAdaptiveConcurrency(unittest.TestCase):
    def test_healthy_stream_growth(self):
        """Under low latency and zero refusal, controller issues ADD action."""
        snapshot = ConcurrencySnapshot(
            timestamp=100.0,
            per_route_active={"route_default": 4},
            per_route_served={"route_default": 4},
            per_route_refused={"route_default": 0},
            pending_blocks=10,
            disk_write_latency_ms=10.0,
            queued_write_bytes=1024
        )
        actions = compute_actions(snapshot)
        self.assertTrue(any(a.action_type == StreamActionType.ADD for a in actions))

    def test_server_refusal_backs_off(self):
        """When server throttles (refusal > 0), controller issues RETIRE action."""
        snapshot = ConcurrencySnapshot(
            timestamp=100.0,
            per_route_active={"route_default": 16},
            per_route_served={"route_default": 10},
            per_route_refused={"route_default": 2},
            pending_blocks=5,
            disk_write_latency_ms=10.0
        )
        actions = compute_actions(snapshot)
        self.assertTrue(any(a.action_type == StreamActionType.RETIRE for a in actions))

    def test_disk_backpressure_retires_streams(self):
        """Excessive disk latency or queued writes causes controller to back off."""
        snapshot = ConcurrencySnapshot(
            timestamp=100.0,
            per_route_active={"route_default": 12},
            per_route_served={"route_default": 12},
            per_route_refused={"route_default": 0},
            pending_blocks=5,
            disk_write_latency_ms=250.0  # Above 100ms threshold
        )
        actions = compute_actions(snapshot)
        self.assertTrue(any(a.action_type == StreamActionType.RETIRE for a in actions))

    def test_fixed_concurrency_mode_honored(self):
        """Fixed user setting strictly caps concurrency without auto-growth."""
        policy = ConcurrencyPolicy(is_fixed_mode=True, fixed_concurrency=6)
        snapshot = ConcurrencySnapshot(
            timestamp=100.0,
            per_route_active={"route_default": 6},
            per_route_served={"route_default": 6},
            per_route_refused={"route_default": 0},
            pending_blocks=20
        )
        actions = compute_actions(snapshot, policy)
        self.assertFalse(any(a.action_type == StreamActionType.ADD for a in actions))


if __name__ == "__main__":
    unittest.main()
