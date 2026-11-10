"""
RFC 959 / RFC 3659 Resilient FTP and FTPS Downloader Engine for P-Downloader.
Supports SIZE probing, MDTM timestamps, REST byte-offset resumption, and passive mode transfers.
"""
import os
import time
import ftplib
import threading
from urllib.parse import urlparse, unquote
from typing import Dict, Any, Optional, Callable, List

from .speed_limiter import SpeedLimiter
from .categories import sanitize_filename, resolve_unique_filename


def parse_ftp_url(url: str):
    """Parses an ftp:// or ftps:// URL into components."""
    parsed = urlparse(url)
    is_tls = parsed.scheme.lower() == "ftps"
    host = parsed.hostname or ""
    port = parsed.port or (990 if is_tls else 21)
    username = unquote(parsed.username) if parsed.username else "anonymous"
    password = unquote(parsed.password) if parsed.password else "anonymous@"
    path = unquote(parsed.path).lstrip("/")
    return is_tls, host, port, username, password, path


def probe_ftp(url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Probes an FTP/FTPS server for file existence, size (SIZE), and REST resume support.
    """
    is_tls, host, port, username, password, path = parse_ftp_url(url)
    if not host or not path:
        raise ValueError(f"Invalid FTP URL: {url}")

    filename = os.path.basename(path) or "download.bin"
    total_bytes: Optional[int] = None
    supports_range = False

    ftp_client = None
    try:
        if is_tls:
            ftp_client = ftplib.FTP_TLS(timeout=timeout)
        else:
            ftp_client = ftplib.FTP(timeout=timeout)

        ftp_client.connect(host, port)
        ftp_client.login(username, password)
        if is_tls:
            ftp_client.prot_p()

        # Query file size via SIZE command (RFC 3659)
        try:
            size_resp = ftp_client.sendcmd(f"SIZE {path}")
            if size_resp.startswith("213"):
                total_bytes = int(size_resp.split()[1])
        except Exception:
            total_bytes = None

        # Check REST command support (RFC 3659 byte offset restart)
        try:
            rest_resp = ftp_client.sendcmd("REST 0")
            if rest_resp.startswith(("350", "200")):
                supports_range = True
        except Exception:
            supports_range = False

        return {
            "url": url,
            "final_url": url,
            "filename": sanitize_filename(filename),
            "total_bytes": total_bytes or 0,
            "supports_range": supports_range,
            "is_ftp": True,
            "is_unknown_length": total_bytes is None
        }
    finally:
        if ftp_client:
            try:
                ftp_client.quit()
            except Exception:
                try:
                    ftp_client.close()
                except Exception:
                    pass


class FTPDownloadTask:
    """
    DownloadTask implementation for FTP and FTPS streams with byte-range resume.
    """
    def __init__(
        self,
        task_id: str,
        url: str,
        save_path: str,
        connections: int = 1,
        speed_limit: int = 0,
        headers: Optional[Dict[str, str]] = None,
        on_progress: Optional[Callable[['FTPDownloadTask'], None]] = None,
        on_complete: Optional[Callable[['FTPDownloadTask'], None]] = None,
        on_error: Optional[Callable[['FTPDownloadTask', str], None]] = None
    ):
        self.task_id = task_id
        self.url = url
        self.save_path = save_path
        self.connections = connections
        self.headers = headers or {}
        self.speed_limiter = SpeedLimiter(speed_limit)
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error

        self.total_bytes: Optional[int] = 0
        self.downloaded_bytes: int = 0
        self.supports_range: bool = True
        self.segments: List[Any] = []
        self.status: str = "queued"
        self.speed: float = 0.0
        self.error_message: str = ""
        self.is_ftp: bool = True
        self.staging_path: str = save_path + ".part"

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def prepare(self):
        try:
            info = probe_ftp(self.url)
            self.total_bytes = info.get("total_bytes", 0)
            self.supports_range = info.get("supports_range", False)
        except Exception:
            self.supports_range = False

        save_dir = os.path.dirname(self.save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)

        if os.path.exists(self.staging_path):
            self.downloaded_bytes = os.path.getsize(self.staging_path)
        elif os.path.exists(self.save_path):
            self.downloaded_bytes = os.path.getsize(self.save_path)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self.status = "downloading"
        self._thread = threading.Thread(target=self._run_download, daemon=True)
        self._thread.start()

    def pause(self):
        self._stop_event.set()
        self.status = "paused"
        if self.on_progress:
            self.on_progress(self)

    def resume(self):
        self.start()

    def cancel(self):
        self._stop_event.set()
        self.status = "cancelled"
        if self.on_progress:
            self.on_progress(self)

    def _run_download(self):
        is_tls, host, port, username, password, path = parse_ftp_url(self.url)
        ftp_client = None
        try:
            if is_tls:
                ftp_client = ftplib.FTP_TLS(timeout=15)
            else:
                ftp_client = ftplib.FTP(timeout=15)

            ftp_client.connect(host, port)
            ftp_client.login(username, password)
            if is_tls:
                ftp_client.prot_p()

            ftp_client.set_pasv(True)

            start_offset = 0
            file_mode = "wb"
            if self.supports_range and os.path.exists(self.staging_path):
                start_offset = os.path.getsize(self.staging_path)
                if self.total_bytes and start_offset >= self.total_bytes:
                    # Already completed
                    self._finalize_file()
                    return
                file_mode = "ab"
                self.downloaded_bytes = start_offset

            last_time = time.time()
            bytes_since_last = 0

            with open(self.staging_path, file_mode) as f:
                def handle_chunk(chunk: bytes):
                    if self._stop_event.is_set():
                        raise InterruptedError("Download paused by user")

                    f.write(chunk)
                    chunk_len = len(chunk)
                    nonlocal bytes_since_last, last_time
                    self.downloaded_bytes += chunk_len
                    bytes_since_last += chunk_len

                    now = time.time()
                    dt = now - last_time
                    if dt >= 0.5:
                        self.speed = bytes_since_last / dt
                        bytes_since_last = 0
                        last_time = now
                        if self.on_progress:
                            self.on_progress(self)

                # RFC 3659: REST command followed by RETR
                cmd = f"RETR {path}"
                ftp_client.retrbinary(cmd, handle_chunk, blocksize=65536, rest=start_offset if start_offset > 0 else None)

            if not self._stop_event.is_set():
                self._finalize_file()

        except InterruptedError:
            self.status = "paused"
            if self.on_progress:
                self.on_progress(self)
        except Exception as e:
            if not self._stop_event.is_set():
                self.status = "error"
                self.error_message = str(e)
                if self.on_error:
                    self.on_error(self, str(e))
        finally:
            if ftp_client:
                try:
                    ftp_client.quit()
                except Exception:
                    try:
                        ftp_client.close()
                    except Exception:
                        pass

    def _finalize_file(self):
        if os.path.exists(self.save_path):
            try:
                os.remove(self.save_path)
            except Exception:
                pass
        if os.path.exists(self.staging_path):
            os.replace(self.staging_path, self.save_path)

        self.status = "completed"
        self.speed = 0.0
        if self.on_progress:
            self.on_progress(self)
        if self.on_complete:
            self.on_complete(self)
