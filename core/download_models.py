"""
Typed models, contracts, and error definitions for P-Downloader V2 engine.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any

class CaptureMode(str, Enum):
    AUTO = "auto"
    ASK = "ask"
    OFF = "off"

class DownloadKind(str, Enum):
    HTTP = "http"
    HLS = "hls"
    YOUTUBE = "youtube"

@dataclass(frozen=True)
class BrowserRequestContext:
    source_browser: Optional[str] = None
    page_url: Optional[str] = None
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    per_origin_headers: Dict[str, Dict[str, str]] = field(default_factory=dict)

@dataclass(frozen=True)
class DownloadRequest:
    url: str
    filename: Optional[str] = None
    destination: Optional[str] = None
    kind: DownloadKind = DownloadKind.HTTP
    context: Optional[BrowserRequestContext] = None
    connections: Optional[int] = None      # None = Auto concurrency
    capture_id: Optional[str] = None       # Idempotency token for browser handoffs
    expected_sha256: Optional[str] = None

@dataclass(frozen=True)
class HttpProbeResult:
    final_url: str
    total_bytes: Optional[int]             # None = unknown length (stream); 0 = empty body
    supports_ranges: bool
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    filename: str = "download"
    content_type: Optional[str] = None

@dataclass(frozen=True)
class BlockWork:
    block_id: int
    start: int
    end_exclusive: Optional[int]           # None for unknown-length single stream
    durable_bytes: int = 0

class ProbeError(Exception):
    """Explicit probe failure with structured error code."""
    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
