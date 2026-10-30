"""
Exponential backoff retry policy with jitter and Retry-After compliance.
"""
import random
from dataclasses import dataclass
from typing import Optional

@dataclass
class RetryPolicy:
    max_attempts: int = 5
    initial_delay_s: float = 1.0
    max_delay_s: float = 30.0
    backoff_multiplier: float = 2.0
    jitter: float = 0.2


def next_retry_delay(
    attempt: int,
    retry_after: Optional[float] = None,
    policy: Optional[RetryPolicy] = None
) -> Optional[float]:
    """
    Calculate next delay in seconds. Returns None if max_attempts exceeded.
    """
    policy = policy or RetryPolicy()

    if attempt >= policy.max_attempts:
        return None

    if retry_after is not None and retry_after > 0:
        return min(retry_after, policy.max_delay_s)

    # Exponential backoff: initial * (multiplier ** attempt)
    base_delay = policy.initial_delay_s * (policy.backoff_multiplier ** attempt)
    capped_delay = min(base_delay, policy.max_delay_s)

    # Apply jitter: +/- jitter percentage
    jitter_factor = 1.0 + random.uniform(-policy.jitter, policy.jitter)
    return max(0.1, capped_delay * jitter_factor)
