"""
Unit tests for straggler tail hedging and scheduling.
"""
import unittest
from core.adaptive_concurrency import (
    StreamActionType,
    ConcurrencyPolicy,
    ConcurrencySnapshot,
    compute_actions
)

class TestTailScheduling(unittest.TestCase):
    def test_tail_hedging_triggered_near_completion(self):
        """When 90%+ blocks are completed and stragglers remain, HEDGE action is issued."""
        snapshot = ConcurrencySnapshot(
            timestamp=200.0,
            per_route_active={"route_default": 2},
            per_route_served={"route_default": 2},
            per_route_refused={"route_default": 0},
            pending_blocks=0,
            total_blocks=20,
            completed_blocks=19  # 95% complete
        )
        actions = compute_actions(snapshot)
        self.assertTrue(any(a.action_type == StreamActionType.HEDGE for a in actions))

    def test_no_hedging_when_pending_blocks_remain(self):
        """Do not hedge if unclaimed pending blocks still exist."""
        snapshot = ConcurrencySnapshot(
            timestamp=200.0,
            per_route_active={"route_default": 4},
            per_route_served={"route_default": 4},
            per_route_refused={"route_default": 0},
            pending_blocks=5,
            total_blocks=20,
            completed_blocks=11
        )
        actions = compute_actions(snapshot)
        self.assertFalse(any(a.action_type == StreamActionType.HEDGE for a in actions))


if __name__ == "__main__":
    unittest.main()
