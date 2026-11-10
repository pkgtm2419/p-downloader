"""
Standardized error taxonomy for P-Downloader (IM-05).
Provides typed, actionable exceptions for network, extractor, storage, and protocol failures.
"""
from enum import Enum
from typing import Optional, Dict, Any, Tuple


class ErrorCode(str, Enum):
    # Network & Transport
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    NETWORK_RESET = "NETWORK_RESET"
    HTTP_4XX_AUTH = "HTTP_4XX_AUTH"
    HTTP_429_503 = "HTTP_429_503"
    STREAM_URL_EXPIRED = "STREAM_URL_EXPIRED"
    UNSAFE_URL = "UNSAFE_URL"
    ADAPTER_DOWN = "ADAPTER_DOWN"

    # Streaming Media & Extractors
    DRM_PROTECTED = "DRM_PROTECTED"
    NO_MEDIA_FOUND = "NO_MEDIA_FOUND"
    EXTRACTOR_OUTDATED = "EXTRACTOR_OUTDATED"
    GEO_BLOCKED = "GEO_BLOCKED"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    MUX_FAILED = "MUX_FAILED"

    # Filesystem & Storage
    DISK_FULL = "DISK_FULL"
    PATH_DENIED = "PATH_DENIED"
    NAME_TOO_LONG = "NAME_TOO_LONG"
    CHECKSUM_MISMATCH = "CHECKSUM_MISMATCH"
    ARCHIVE_CORRUPT = "ARCHIVE_CORRUPT"

    # Protocol & System
    FTP_ERROR = "FTP_ERROR"
    TORRENT_ERROR = "TORRENT_ERROR"
    DEBRID_ERROR = "DEBRID_ERROR"
    INTERNAL = "INTERNAL"


DEFAULT_ERROR_ACTIONS: Dict[ErrorCode, Tuple[str, bool]] = {
    ErrorCode.NETWORK_TIMEOUT: ("Connection timed out. Retrying with exponential backoff...", True),
    ErrorCode.NETWORK_RESET: ("Network connection was reset by peer. Retrying...", True),
    ErrorCode.HTTP_4XX_AUTH: ("Access denied (401/403). Authentication cookies or login required.", False),
    ErrorCode.HTTP_429_503: ("Server requested rate limiting. Waiting before retry...", True),
    ErrorCode.STREAM_URL_EXPIRED: ("Stream authorization token expired. Please refresh the address.", False),
    ErrorCode.UNSAFE_URL: ("Security block: Prohibited destination or loopback/private network IP.", False),
    ErrorCode.ADAPTER_DOWN: ("Designated network adapter or VPN is down. Fail-closed killswitch active.", True),
    ErrorCode.DRM_PROTECTED: ("Protected video: This content is encrypted with DRM and cannot be saved.", False),
    ErrorCode.NO_MEDIA_FOUND: ("No downloadable media or video streams were detected on this webpage.", False),
    ErrorCode.EXTRACTOR_OUTDATED: ("Site player format has changed. Please update extractors in Settings.", False),
    ErrorCode.GEO_BLOCKED: ("Content is geographically restricted by the content provider.", False),
    ErrorCode.LOGIN_REQUIRED: ("Account login required to access this file or stream.", False),
    ErrorCode.MUX_FAILED: ("FFmpeg failed to merge video and audio streams.", False),
    ErrorCode.DISK_FULL: ("Insufficient disk storage space available.", False),
    ErrorCode.PATH_DENIED: ("Access denied to target directory. Check write permissions.", False),
    ErrorCode.NAME_TOO_LONG: ("Filename exceeds OS path length limit.", False),
    ErrorCode.CHECKSUM_MISMATCH: ("Integrity check failed: Computed digest does not match expected checksum.", False),
    ErrorCode.ARCHIVE_CORRUPT: ("Archive unpack failed: Archive is damaged or password is required.", False),
    ErrorCode.INTERNAL: ("An unexpected internal error occurred.", False)
}


class AppError(Exception):
    """
    Standard application error with machine-readable code, user-friendly message,
    actionable recovery advice, and retry classification.
    """
    def __init__(
        self,
        code: ErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        retryable: Optional[bool] = None,
        user_action: Optional[str] = None
    ):
        self.code = code
        default_msg, default_retry = DEFAULT_ERROR_ACTIONS.get(code, ("An error occurred.", False))
        self.message = message or default_msg
        self.retryable = retryable if retryable is not None else default_retry
        self.user_action = user_action or default_msg
        self.details = details or {}
        super().__init__(f"[{self.code.value}] {self.message}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "user_action": self.user_action,
            "retryable": self.retryable,
            "details": self.details
        }
