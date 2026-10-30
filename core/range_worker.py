"""
Bounded, validated HTTP body range worker writing to staging sink.
"""
import re
import threading
from typing import Optional, Callable
import requests

from .download_models import DownloadRequest, HttpProbeResult, BlockWork, ProbeError
from .transfer_store import BoundedBlockWriter

CHUNK_SIZE = 65536  # 64 KiB read chunks

def fetch_block(
    request: DownloadRequest,
    probe: HttpProbeResult,
    work: BlockWork,
    route_id: Optional[str] = None,
    cancel: Optional[threading.Event] = None,
    sink: Optional[BoundedBlockWriter] = None,
    on_progress: Optional[Callable[[int], None]] = None,
    timeout_s: float = 15.0
) -> int:
    """
    Fetch a verified byte block from origin and stream directly into sink.
    Strictly verifies Range status (206) and Content-Range boundaries.
    """
    if cancel is None:
        cancel = threading.Event()

    range_start = work.start + work.durable_bytes
    is_ranged = True

    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Encoding": "identity"
    }

    if work.end_exclusive is not None:
        range_end = work.end_exclusive - 1
        if range_start > range_end:
            # Block is already fully completed
            return 0
        req_headers["Range"] = f"bytes={range_start}-{range_end}"
    else:
        # Unknown-length streaming
        if range_start > 0:
            req_headers["Range"] = f"bytes={range_start}-"
        else:
            is_ranged = False

    if probe.etag:
        req_headers["If-Range"] = probe.etag

    # Apply context headers
    if request.context:
        if request.context.user_agent:
            req_headers["User-Agent"] = request.context.user_agent
        if request.context.referrer:
            req_headers["Referer"] = request.context.referrer

    # Route binding if session provided
    session = requests.Session()

    try:
        resp = session.get(
            probe.final_url,
            headers=req_headers,
            stream=True,
            timeout=timeout_s,
            allow_redirects=True
        )
    except Exception as e:
        raise ProbeError("NETWORK_ERROR", f"Request failed: {e}")

    status = resp.status_code

    if is_ranged:
        if status == 200:
            # Server completely ignored Range header!
            resp.close()
            if range_start > 0:
                raise ProbeError(
                    "INVALID_RANGE",
                    f"Server returned HTTP 200 to interior ranged request (start={range_start})"
                )
            # If start is 0 and server sent 200, it's returning full body
        elif status == 206:
            # Verify Content-Range header
            cr = resp.headers.get("Content-Range", "")
            match = re.search(r"bytes\s+(\d+)-(\d+)", cr, re.IGNORECASE)
            if not match or int(match.group(1)) != range_start:
                resp.close()
                raise ProbeError(
                    "INVALID_RANGE",
                    f"Content-Range mismatch: expected start {range_start}, got '{cr}'"
                )
        else:
            resp.close()
            raise ProbeError(f"HTTP_{status}", f"Unexpected status {status} for block {work.block_id}")
    else:
        if status not in (200, 206):
            resp.close()
            raise ProbeError(f"HTTP_{status}", f"Unexpected status {status} for un-ranged request")

    bytes_written = 0
    current_offset = range_start

    try:
        for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
            if cancel.is_set():
                break
            if not chunk:
                continue

            # Ensure we do not write past end_exclusive
            if work.end_exclusive is not None:
                remaining = work.end_exclusive - current_offset
                if remaining <= 0:
                    break
                if len(chunk) > remaining:
                    chunk = chunk[:remaining]

            if sink:
                sink.write_at(current_offset, chunk)

            chunk_len = len(chunk)
            current_offset += chunk_len
            bytes_written += chunk_len

            if on_progress:
                on_progress(chunk_len)

            if work.end_exclusive is not None and current_offset >= work.end_exclusive:
                break

    finally:
        resp.close()
        if sink:
            sink.flush_checkpoint()

    return bytes_written
