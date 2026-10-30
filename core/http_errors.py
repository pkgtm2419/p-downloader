"""
Transfer error classification, user-friendly messages, and recovery categorization.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from email.utils import parsedate_to_datetime
import time

@dataclass
class TransferError(Exception):
    code: str
    status_code: Optional[int]
    retryable: bool
    origin: str
    user_message: str
    retry_after_s: Optional[float] = None

    def __str__(self) -> str:
        return f"[{self.code}] {self.user_message}"


def parse_retry_after(header_val: Optional[str]) -> Optional[float]:
    """Parse HTTP Retry-After header into delta seconds."""
    if not header_val:
        return None
    header_val = header_val.strip()
    # Try integer seconds
    if header_val.isdigit():
        return float(header_val)
    # Try HTTP date
    try:
        dt = parsedate_to_datetime(header_val)
        delta = (dt.timestamp() - time.time())
        return max(0.0, delta)
    except Exception:
        return None


def classify_response(
    status_code: Optional[int] = None,
    headers: Optional[Dict[str, str]] = None,
    exception: Optional[Exception] = None,
    origin: str = ""
) -> TransferError:
    """
    Classify an HTTP response or transport exception into a structured TransferError.
    """
    headers = headers or {}
    retry_after = parse_retry_after(headers.get("Retry-After"))

    if status_code is not None:
        if status_code == 429:
            return TransferError(
                code="RATE_LIMITED",
                status_code=429,
                retryable=True,
                origin=origin,
                user_message="Rate limit reached on server. Backing off.",
                retry_after_s=retry_after or 2.0
            )
        elif status_code == 503:
            return TransferError(
                code="SERVICE_UNAVAILABLE",
                status_code=503,
                retryable=True,
                origin=origin,
                user_message="Server temporarily unavailable (503). Retrying.",
                retry_after_s=retry_after or 2.0
            )
        elif status_code in (401, 403):
            return TransferError(
                code="AUTH_REQUIRED",
                status_code=status_code,
                retryable=False,
                origin=origin,
                user_message=f"Access denied (HTTP {status_code}). Check site login/credentials."
            )
        elif status_code in (404, 410):
            return TransferError(
                code="NOT_FOUND_OR_EXPIRED",
                status_code=status_code,
                retryable=False,
                origin=origin,
                user_message=f"Download link expired or not found (HTTP {status_code}). Refresh address."
            )
        elif status_code == 416:
            return TransferError(
                code="RANGE_NOT_SATISFIABLE",
                status_code=416,
                retryable=False,
                origin=origin,
                user_message="HTTP 416 Range Not Satisfiable: file may have changed or size mismatch."
            )
        elif 500 <= status_code <= 599:
            return TransferError(
                code="SERVER_ERROR",
                status_code=status_code,
                retryable=True,
                origin=origin,
                user_message=f"Server returned internal error (HTTP {status_code}). Retrying."
            )

    if exception:
        exc_str = (str(exception) + " " + type(exception).__name__).lower()
        if "timeout" in exc_str:
            return TransferError(
                code="TIMEOUT",
                status_code=None,
                retryable=True,
                origin=origin,
                user_message="Connection timed out while transferring data."
            )
        if "connection" in exc_str or "reset" in exc_str or "broken" in exc_str:
            return TransferError(
                code="NETWORK_RESET",
                status_code=None,
                retryable=True,
                origin=origin,
                user_message="Network connection reset or interrupted."
            )

    return TransferError(
        code="UNKNOWN_TRANSFER_ERROR",
        status_code=status_code,
        retryable=False,
        origin=origin,
        user_message=f"Transfer failed: {exception or f'HTTP {status_code}'}"
    )
