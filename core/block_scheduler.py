"""
Small-block shared work scheduler, block planning, and work assignment.
"""
import threading
from typing import Optional, List, Dict, Tuple
from .download_models import BlockWork

DEFAULT_MIN_BLOCK_SIZE = 1 * 1024 * 1024       # 1 MiB
DEFAULT_MAX_BLOCK_SIZE = 8 * 1024 * 1024       # 8 MiB

def plan_blocks(
    total_bytes: Optional[int],
    routes: int = 1,
    max_block_bytes: int = DEFAULT_MAX_BLOCK_SIZE
) -> List[BlockWork]:
    """
    Decompose a known file length into 1-8 MiB blocks.
    Unknown-length returns a single open-ended block.
    """
    if total_bytes is None:
        return [BlockWork(block_id=0, start=0, end_exclusive=None, durable_bytes=0)]

    if total_bytes == 0:
        return [BlockWork(block_id=0, start=0, end_exclusive=0, durable_bytes=0)]

    # Determine adaptive block size
    if total_bytes <= DEFAULT_MIN_BLOCK_SIZE:
        block_size = total_bytes
    elif total_bytes <= 16 * 1024 * 1024:
        block_size = 1 * 1024 * 1024
    elif total_bytes <= 128 * 1024 * 1024:
        block_size = 2 * 1024 * 1024
    elif total_bytes <= 1024 * 1024 * 1024:
        block_size = 4 * 1024 * 1024
    else:
        block_size = min(max_block_bytes, 8 * 1024 * 1024)

    blocks: List[BlockWork] = []
    block_id = 0
    offset = 0

    while offset < total_bytes:
        end_excl = min(offset + block_size, total_bytes)
        blocks.append(BlockWork(
            block_id=block_id,
            start=offset,
            end_exclusive=end_excl,
            durable_bytes=0
        ))
        offset = end_excl
        block_id += 1

    return blocks


class BlockScheduler:
    """
    Thread-safe shared block queue with claiming, completion, and failure reclaim.
    """
    def __init__(self, blocks: List[BlockWork], completed_ids: Optional[List[int]] = None):
        self._lock = threading.Lock()
        self._all_blocks: Dict[int, BlockWork] = {b.block_id: b for b in blocks}
        self._pending: List[int] = []
        self._claimed: Dict[int, str] = {}  # block_id -> route_id or worker_id
        self._completed: Dict[int, int] = {}  # block_id -> durable_bytes
        self._total_bytes: Optional[int] = None

        if blocks and blocks[-1].end_exclusive is not None:
            self._total_bytes = blocks[-1].end_exclusive

        # Mark already completed blocks (from resumed checkpoint)
        completed_set = set(completed_ids or [])
        for b in blocks:
            if b.block_id in completed_set:
                size = (b.end_exclusive - b.start) if b.end_exclusive is not None else b.durable_bytes
                self._completed[b.block_id] = size
            else:
                self._pending.append(b.block_id)

    @property
    def total_bytes(self) -> Optional[int]:
        return self._total_bytes

    def claim_next(self, worker_id: str = "worker") -> Optional[BlockWork]:
        """Claim next pending block for processing."""
        with self._lock:
            if not self._pending:
                return None
            block_id = self._pending.pop(0)
            self._claimed[block_id] = worker_id
            return self._all_blocks[block_id]

    def complete(self, block_id: int, bytes_written: int) -> None:
        """Mark block durably complete."""
        with self._lock:
            self._claimed.pop(block_id, None)
            self._completed[block_id] = bytes_written

    def return_remaining(self, block_id: int, durable_bytes: int) -> None:
        """Reclaim unfinished block and preserve bytes already written."""
        with self._lock:
            self._claimed.pop(block_id, None)
            original = self._all_blocks[block_id]
            # Update durable offset
            updated = BlockWork(
                block_id=original.block_id,
                start=original.start,
                end_exclusive=original.end_exclusive,
                durable_bytes=durable_bytes
            )
            self._all_blocks[block_id] = updated
            # Insert back at front of queue for priority retry
            if block_id not in self._pending:
                self._pending.insert(0, block_id)

    def is_complete(self) -> bool:
        """True if all blocks are completed."""
        with self._lock:
            return len(self._completed) == len(self._all_blocks) and not self._pending and not self._claimed

    def completed_block_ids(self) -> List[int]:
        """List of all completed block IDs."""
        with self._lock:
            return sorted(list(self._completed.keys()))

    def progress(self) -> Tuple[int, Optional[int]]:
        """Return (downloaded_bytes, total_bytes)."""
        with self._lock:
            downloaded = sum(self._completed.values())
            return (downloaded, self._total_bytes)

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    def active_count(self) -> int:
        with self._lock:
            return len(self._claimed)
