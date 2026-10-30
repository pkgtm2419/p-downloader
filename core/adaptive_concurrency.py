"""
Adaptive concurrency controller and straggler tail optimization.
Pure, deterministic feedback policy ported from Plexo concurrency principles.
"""
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional

class StreamActionType(str, Enum):
    ADD = "add"
    RETIRE = "retire"
    HEDGE = "hedge"
    SPLIT = "split"
    NOOP = "noop"

@dataclass(frozen=True)
class StreamAction:
    action_type: StreamActionType
    route_id: Optional[str] = None
    target_block_id: Optional[int] = None
    reason: str = ""

@dataclass(frozen=True)
class ConcurrencyPolicy:
    min_streams: int = 4
    max_streams: int = 32
    start_streams: int = 8
    target_write_latency_ms: float = 100.0
    max_queued_write_bytes: int = 32 * 1024 * 1024  # 32 MiB
    hedge_threshold_ratio: float = 0.9              # Last 10% of download
    is_fixed_mode: bool = False
    fixed_concurrency: Optional[int] = None

@dataclass(frozen=True)
class ConcurrencySnapshot:
    timestamp: float
    per_route_active: Dict[str, int]
    per_route_served: Dict[str, int]
    per_route_refused: Dict[str, int]
    pending_blocks: int
    disk_write_latency_ms: float = 0.0
    queued_write_bytes: int = 0
    total_blocks: int = 1
    completed_blocks: int = 0

def compute_actions(
    snapshot: ConcurrencySnapshot,
    policy: Optional[ConcurrencyPolicy] = None
) -> List[StreamAction]:
    """
    Compute stream adjustments based on network response and disk backpressure.
    Returns deterministic list of StreamAction items.
    """
    policy = policy or ConcurrencyPolicy()
    actions: List[StreamAction] = []

    total_active = sum(snapshot.per_route_active.values())

    # 1. Fixed user concurrency mode
    if policy.is_fixed_mode and policy.fixed_concurrency is not None:
        target = min(policy.max_streams, max(1, policy.fixed_concurrency))
        if total_active < target and snapshot.pending_blocks > 0:
            actions.append(StreamAction(
                action_type=StreamActionType.ADD,
                reason=f"Fixed mode: reaching user target {target}"
            ))
        elif total_active > target:
            actions.append(StreamAction(
                action_type=StreamActionType.RETIRE,
                reason=f"Fixed mode: exceeding user target {target}"
            ))
        return actions

    # 2. Disk backpressure check
    if (snapshot.disk_write_latency_ms > policy.target_write_latency_ms or
            snapshot.queued_write_bytes > policy.max_queued_write_bytes):
        if total_active > policy.min_streams:
            actions.append(StreamAction(
                action_type=StreamActionType.RETIRE,
                reason="Disk write backpressure: reducing active streams"
            ))
        return actions

    # 3. Server throttling check (429 / 503 refusal)
    total_refused = sum(snapshot.per_route_refused.values())
    if total_refused > 0:
        if total_active > policy.min_streams:
            actions.append(StreamAction(
                action_type=StreamActionType.RETIRE,
                reason="Server rate limits/throttling detected: reducing streams"
            ))
        return actions

    # 4. Healthy growth check
    if snapshot.pending_blocks > 0 and total_active < policy.max_streams:
        # If all currently active streams are actively served and below max
        total_served = sum(snapshot.per_route_served.values())
        if total_active == 0 or total_served >= total_active:
            actions.append(StreamAction(
                action_type=StreamActionType.ADD,
                reason="Healthy network and queue headroom: ramping concurrency"
            ))

    # 5. Tail straggler hedging / tail splitting near end of file
    if snapshot.total_blocks > 0:
        ratio = snapshot.completed_blocks / snapshot.total_blocks
        if ratio >= policy.hedge_threshold_ratio and snapshot.pending_blocks == 0 and total_active > 0:
            if total_active < policy.max_streams:
                actions.append(StreamAction(
                    action_type=StreamActionType.HEDGE,
                    reason="Tail straggler optimization: hedging remaining slow blocks"
                ))

    if not actions:
        actions.append(StreamAction(action_type=StreamActionType.NOOP, reason="Stable"))

    return actions
