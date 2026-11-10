"""
Centralized logging framework for P-Downloader (IM-04).
Implements rotating log files (5 x 2 MB), structured per-task context,
canary secret redaction filter, and diagnostic bundle export.
"""
import os
import re
import sys
import logging
import logging.handlers
import zipfile
import platform
from pathlib import Path
from typing import Optional, List, Set

DEFAULT_LOG_DIR = Path.home() / ".pdownloader" / "logs"

SENSITIVE_PATTERNS = [
    # Bearer / Basic tokens
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(Basic\s+)[A-Za-z0-9+/=]{8,}", re.IGNORECASE), r"\1[REDACTED]"),
    # URL query parameters & standalone tokens
    (re.compile(r"([?&\s](?:token|auth|key|secret|access_token|signature|sig)\s*[:=]\s*)[^&\s'\"]+", re.IGNORECASE), r"\1[REDACTED]"),
    # Password / API key-values
    (re.compile(r"((?:password|passwd|pwd|api_key|secret)\s*[:=]\s*)[^\s,;'\"\}]+", re.IGNORECASE), r"\1[REDACTED]"),
    # Cookies
    (re.compile(r"(cookie\s*[:=]\s*)[^\r\n]+", re.IGNORECASE), r"\1[REDACTED]"),
]


class RedactionFilter(logging.Filter):
    """
    Log filter that intercepts log records and sanitizes tokens, passwords,
    cookies, and sensitive query parameters before they hit disk or console.
    """
    def __init__(self, canary_secrets: Optional[List[str]] = None):
        super().__init__()
        self.canary_secrets: Set[str] = set(canary_secrets or [])

    def register_secret(self, secret: str):
        if secret and len(secret) >= 4:
            self.canary_secrets.add(secret)

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            text = record.msg
            for pattern, repl in SENSITIVE_PATTERNS:
                text = pattern.sub(repl, text)
            for canary in self.canary_secrets:
                if canary in text:
                    text = text.replace(canary, "[REDACTED_CANARY]")
            record.msg = text

        if record.args:
            if isinstance(record.args, dict):
                sanitized_dict = {}
                for k, v in record.args.items():
                    val_str = str(v)
                    for pattern, repl in SENSITIVE_PATTERNS:
                        val_str = pattern.sub(repl, val_str)
                    for canary in self.canary_secrets:
                        val_str = val_str.replace(canary, "[REDACTED_CANARY]")
                    sanitized_dict[k] = val_str
                record.args = sanitized_dict
            elif isinstance(record.args, tuple):
                sanitized_list = []
                for v in record.args:
                    val_str = str(v)
                    for pattern, repl in SENSITIVE_PATTERNS:
                        val_str = pattern.sub(repl, val_str)
                    for canary in self.canary_secrets:
                        val_str = val_str.replace(canary, "[REDACTED_CANARY]")
                    sanitized_list.append(val_str)
                record.args = tuple(sanitized_list)

        return True


_global_filter = RedactionFilter()
_initialized = False


def get_log_dir() -> Path:
    try:
        DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        return DEFAULT_LOG_DIR
    except Exception:
        fallback = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "logs")))
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def setup_logging(log_dir: Optional[str] = None, level: int = logging.INFO, register_root: bool = True) -> logging.Logger:
    """
    Initializes rotating file handler (5 x 2 MB) and attaches RedactionFilter.
    """
    global _initialized
    ld = Path(log_dir) if log_dir else get_log_dir()
    ld.mkdir(parents=True, exist_ok=True)
    log_file = ld / "pdownloader.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid adding duplicate handlers on multiple calls
    if not _initialized:
        # Rotating file handler (5 backups, 2 MB each)
        file_handler = logging.handlers.RotatingFileHandler(
            str(log_file),
            maxBytes=2 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
        file_handler.setFormatter(formatter)
        file_handler.addFilter(_global_filter)
        root_logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(_global_filter)
        root_logger.addHandler(console_handler)

        _initialized = True

    return logging.getLogger("pdownloader")


def get_logger(name: str = "pdownloader") -> logging.Logger:
    return logging.getLogger(name)


def register_redacted_secret(secret: str):
    """Adds a runtime secret (API key, user password, bearer token) to the redaction list."""
    _global_filter.register_secret(secret)


def export_diagnostics(target_zip: Optional[str] = None) -> str:
    """
    Bundles log files and sanitized environment details into a diagnostics ZIP for troubleshooting.
    """
    log_dir = get_log_dir()
    if not target_zip:
        target_zip = str(log_dir / f"pdownloader_diagnostics_{os.getpid()}.zip")

    with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Add log files
        for f in log_dir.glob("*.log*"):
            if not f.name.endswith(".zip"):
                zf.write(f, arcname=f"logs/{f.name}")

        # 2. Add sanitized system info
        sys_info = (
            f"OS: {platform.system()} {platform.release()} ({platform.version()})\n"
            f"Architecture: {platform.machine()}\n"
            f"Python: {sys.version}\n"
        )
        zf.writestr("system_info.txt", sys_info)

    return target_zip


def close_logging():
    """Closes all logging handlers and resets initialization state."""
    global _initialized
    root = logging.getLogger()
    for h in list(root.handlers):
        try:
            h.flush()
            h.close()
        except Exception:
            pass
        root.removeHandler(h)
    _initialized = False

