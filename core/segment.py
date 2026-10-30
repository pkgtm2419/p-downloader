"""
High-performance multi-connection segmented download worker.
Supports dynamic chunking, multi-network interface bonding (Plexo),
expired URL refresh/recovery (IDM), pause/resume, and direct offset writing.
"""
import os
import json
import time
import requests
import threading
from typing import Callable, List, Optional, Dict, Any, Tuple
from urllib.parse import urlparse, unquote

from .network_binder import NetworkManager, NetworkInterface
from .speed_limiter import SpeedLimiter
from .credentials_manager import CredentialsManager
from .categories import sanitize_filename

class Segment:
    def __init__(self, index: int, start: int, end: int, downloaded: int = 0):
        self.index = index
        self.start = start
        self.end = end  # inclusive
        self.downloaded = downloaded
        self.completed = False
        self.assigned_adapter: Optional[str] = None

    @property
    def total_size(self) -> int:
        if self.end < self.start:
            return 0
        return self.end - self.start + 1

    @property
    def current_offset(self) -> int:
        return self.start + self.downloaded

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "start": self.start,
            "end": self.end,
            "downloaded": self.downloaded,
            "completed": self.completed,
            "assigned_adapter": self.assigned_adapter
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Segment':
        seg = cls(data["index"], data["start"], data["end"], data.get("downloaded", 0))
        seg.completed = data.get("completed", False)
        seg.assigned_adapter = data.get("assigned_adapter", None)
        return seg

def probe_url(url: str, timeout: int = 10, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    # Check if YouTube URL and probe with yt-dlp
    try:
        from core.youtube_downloader import is_youtube_url, probe_youtube
        if is_youtube_url(url):
            yt_info = probe_youtube(url)
            return {
                "url": url,
                "final_url": url,
                "filename": yt_info.get("filename", "YouTube_Video.mp4"),
                "total_bytes": yt_info.get("total_bytes", 0),
                "supports_range": True,
                "is_youtube": True
            }
    except Exception:
        pass

    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*"
    }
    # Auto-inject site authentication headers if stored
    auth_headers = CredentialsManager().get_auth_headers_for_url(url)
    if auth_headers:
        req_headers.update(auth_headers)

    if headers:
        req_headers.update(headers)

    filename = "download"
    total_bytes = 0
    supports_range = False
    final_url = url

    try:
        # Try HEAD request first
        head_resp = requests.head(url, headers=req_headers, allow_redirects=True, timeout=timeout)
        final_url = head_resp.url
        content_len = head_resp.headers.get("Content-Length")
        accept_ranges = head_resp.headers.get("Accept-Ranges", "")
        content_disposition = head_resp.headers.get("Content-Disposition", "")
        
        # Test range support with a 0-0 range GET if uncertain
        try:
            range_test = requests.get(final_url, headers={**req_headers, "Range": "bytes=0-0"}, timeout=timeout, stream=True)
            if range_test.status_code == 206:
                supports_range = True
                if not content_len:
                    cr = range_test.headers.get("Content-Range", "")
                    if "/" in cr:
                        total_bytes = int(cr.split("/")[1])
            range_test.close()
        except Exception:
            pass

        if content_len:
            try:
                total_bytes = int(content_len)
            except Exception:
                pass
        if "bytes" in accept_ranges.lower():
            supports_range = True

        # Extract filename
        if "filename=" in content_disposition:
            parts = content_disposition.split("filename=")
            raw_fn = parts[1].split(";")[0].strip("\"' ")
            if raw_fn:
                filename = raw_fn
        else:
            path = urlparse(final_url).path
            extracted = os.path.basename(unquote(path))
            if extracted:
                filename = extracted

    except Exception:
        # Fallback to GET stream
        try:
            with requests.get(url, headers=req_headers, stream=True, allow_redirects=True, timeout=timeout) as resp:
                final_url = resp.url
                content_len = resp.headers.get("Content-Length")
                if content_len:
                    total_bytes = int(content_len)
                path = urlparse(final_url).path
                extracted = os.path.basename(unquote(path))
                if extracted:
                    filename = extracted
        except Exception as e:
            raise RuntimeError(f"Unable to probe URL: {e}")

    filename = sanitize_filename(filename)


    return {
        "url": url,
        "final_url": final_url,
        "filename": filename,
        "total_bytes": total_bytes,
        "supports_range": supports_range
    }

def validate_refresh_url(new_url: str, expected_size: int = 0) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validates a replacement URL for IDM Refresh Download Address:
    Checks accessibility, byte-range resume support, and size parity.
    """
    try:
        info = probe_url(new_url)
        new_size = info.get("total_bytes", 0)
        supports_range = info.get("supports_range", False)

        if expected_size > 0 and new_size > 0 and new_size != expected_size:
            return False, f"Size mismatch: Original file is {expected_size:,} bytes, but new URL provides {new_size:,} bytes.", info

        if expected_size > 0 and not supports_range:
            return False, "The replacement server does not support byte ranges. Resuming existing progress requires Range support.", info

        return True, "URL verified successfully. Byte range and file size match.", info
    except Exception as e:
        return False, f"Verification failed: {str(e)}", {}

class DownloadTask:
    def __init__(
        self,
        task_id: str,
        url: str,
        save_path: str,
        connections: int = 8,
        speed_limit: int = 0,
        on_progress: Optional[Callable[['DownloadTask'], None]] = None,
        on_complete: Optional[Callable[['DownloadTask'], None]] = None,
        on_error: Optional[Callable[['DownloadTask', str], None]] = None
    ):
        self.task_id = task_id
        self.url = url
        self.save_path = save_path
        self.connections = connections
        self.speed_limiter = SpeedLimiter(speed_limit)
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error

        self.total_bytes = 0
        self.downloaded_bytes = 0
        self.supports_range = False
        self.segments: List[Segment] = []
        self.status = "queued"  # queued, downloading, paused, completed, error
        self.error_message = ""
        self.speed = 0.0  # bytes per sec
        self.meta_file = save_path + ".pdownload"

        self._stop_event = threading.Event()
        self._threads: List[threading.Thread] = []
        self._file_lock = threading.Lock()
        self._last_time = time.time()
        self._last_downloaded = 0

    def set_speed_limit(self, limit_bytes_per_sec: int):
        self.speed_limiter.set_limit(limit_bytes_per_sec)

    def refresh_url(self, new_url: str) -> bool:
        """
        Updates the URL of an existing download task (e.g. after expiration).
        Persists into .pdownload and resets error states so download can resume.
        """
        self.url = new_url
        self.error_message = ""
        if self.status != "completed":
            self.status = "paused"
        self._save_metadata()
        return True

    def prepare(self):
        # Load metadata if resuming
        if os.path.exists(self.meta_file) and os.path.exists(self.save_path):
            try:
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.total_bytes = data["total_bytes"]
                    self.supports_range = data["supports_range"]
                    self.segments = [Segment.from_dict(s) for s in data["segments"]]
                    self.downloaded_bytes = sum(s.downloaded for s in self.segments)
                    # If URL in metadata differs and self.url is set, keep current
                    return
            except Exception:
                pass

        # Probe fresh URL
        info = probe_url(self.url)
        self.total_bytes = info["total_bytes"]
        self.supports_range = info["supports_range"]

        save_dir = os.path.dirname(self.save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)

        if self.supports_range and self.total_bytes > 0:
            # Pre-allocate sparse file
            with open(self.save_path, "wb") as f:
                f.seek(self.total_bytes - 1)
                f.write(b"\0")

            # Divide into segments
            num_segs = max(1, min(self.connections, 32))
            part_size = self.total_bytes // num_segs
            self.segments = []
            for i in range(num_segs):
                start = i * part_size
                end = (start + part_size - 1) if (i < num_segs - 1) else (self.total_bytes - 1)
                self.segments.append(Segment(i, start, end))
        else:
            # Single stream
            self.segments = [Segment(0, 0, max(0, self.total_bytes - 1))]

        self._save_metadata()

    def _save_metadata(self):
        try:
            with open(self.meta_file, "w", encoding="utf-8") as f:
                json.dump({
                    "task_id": self.task_id,
                    "url": self.url,
                    "total_bytes": self.total_bytes,
                    "supports_range": self.supports_range,
                    "segments": [s.to_dict() for s in self.segments]
                }, f, indent=2)
        except Exception:
            pass

    def start(self):
        if self.status == "downloading":
            return
        self._stop_event.clear()
        self.status = "downloading"
        self._last_time = time.time()
        self._last_downloaded = self.downloaded_bytes

        if not self.segments:
            self.prepare()

        if self.supports_range and self.total_bytes > 0:
            self._threads = []
            for seg in self.segments:
                if not seg.completed:
                    t = threading.Thread(target=self._download_segment, args=(seg,), daemon=True)
                    self._threads.append(t)
                    t.start()
        else:
            t = threading.Thread(target=self._download_single_stream, daemon=True)
            self._threads.append(t)
            t.start()

    def pause(self):
        if self.status != "downloading":
            return
        self._stop_event.set()
        self.status = "paused"
        for t in self._threads:
            t.join(timeout=1.0)
        self._save_metadata()
        if self.on_progress:
            self.on_progress(self)

    def cancel(self):
        self.status = "cancelled"
        self._stop_event.set()
        for t in self._threads:
            t.join(timeout=1.0)
        # Clean up files
        if os.path.exists(self.save_path):
            try:
                os.remove(self.save_path)
            except Exception:
                pass
        if os.path.exists(self.meta_file):
            try:
                os.remove(self.meta_file)
            except Exception:
                pass

    def _update_speed(self):
        now = time.time()
        elapsed = now - self._last_time
        if elapsed >= 0.2:
            delta = self.downloaded_bytes - self._last_downloaded
            self.speed = max(0.0, delta / elapsed)
            self._last_time = now
            self._last_downloaded = self.downloaded_bytes
            if self.on_progress:
                self.on_progress(self)

    def _download_segment(self, seg: Segment):
        net_mgr = NetworkManager()
        is_local = "127.0.0.1" in self.url or "localhost" in self.url
        assigned_if = None if is_local else net_mgr.get_interface_for_segment(seg.index)
        if assigned_if:
            seg.assigned_adapter = assigned_if.alias

        session = net_mgr.get_session_for_interface(assigned_if.ip if assigned_if else None)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        auth_headers = CredentialsManager().get_auth_headers_for_url(self.url)
        if auth_headers:
            headers.update(auth_headers)

        start_byte = seg.current_offset
        if start_byte > seg.end:
            seg.completed = True
            self._check_completion()
            return

        headers["Range"] = f"bytes={start_byte}-{seg.end}"

        try:
            with session.get(self.url, headers=headers, stream=True, timeout=15) as resp:
                if resp.status_code in (401, 403, 410):
                    err = f"HTTP {resp.status_code} (Link Expired - Refresh Address)"
                    raise RuntimeError(err)

                if resp.status_code not in (200, 206):
                    raise RuntimeError(f"HTTP {resp.status_code}")

                mode = "r+b" if os.path.exists(self.save_path) else "w+b"
                with open(self.save_path, mode) as f:
                    f.seek(start_byte)
                    for chunk in resp.iter_content(chunk_size=65536):
                        if self._stop_event.is_set():
                            break
                        if chunk:
                            # Apply speed limiter throttling if active
                            self.speed_limiter.acquire(len(chunk))

                            with self._file_lock:
                                f.seek(seg.current_offset)
                                f.write(chunk)
                                seg.downloaded += len(chunk)
                                self.downloaded_bytes += len(chunk)

                            if assigned_if:
                                assigned_if.record_bytes(len(chunk))
                                assigned_if.update_speed()

                            self._update_speed()

                if seg.downloaded >= seg.total_size:
                    seg.completed = True

        except Exception as e:
            if not self._stop_event.is_set() and self.status not in ("paused", "cancelled"):
                self.error_message = str(e)
                self.status = "error"
                if self.on_error:
                    self.on_error(self, str(e))
                return

        self._check_completion()

    def _download_single_stream(self):
        net_mgr = NetworkManager()
        is_local = "127.0.0.1" in self.url or "localhost" in self.url
        assigned_if = None if is_local else net_mgr.get_interface_for_segment(0)
        session = net_mgr.get_session_for_interface(assigned_if.ip if assigned_if else None)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        auth_headers = CredentialsManager().get_auth_headers_for_url(self.url)
        if auth_headers:
            headers.update(auth_headers)

        mode = "ab" if (self.downloaded_bytes > 0 and self.supports_range) else "wb"
        if mode == "ab":
            headers["Range"] = f"bytes={self.downloaded_bytes}-"

        try:
            with session.get(self.url, headers=headers, stream=True, timeout=15) as resp:
                if resp.status_code in (401, 403, 410):
                    err = f"HTTP {resp.status_code} (Link Expired - Refresh Address)"
                    raise RuntimeError(err)

                if resp.status_code not in (200, 206):
                    raise RuntimeError(f"HTTP {resp.status_code}")

                with open(self.save_path, mode) as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if self._stop_event.is_set():
                            break
                        if chunk:
                            self.speed_limiter.acquire(len(chunk))
                            f.write(chunk)
                            self.downloaded_bytes += len(chunk)
                            if self.segments:
                                self.segments[0].downloaded = self.downloaded_bytes
                            if assigned_if:
                                assigned_if.record_bytes(len(chunk))
                                assigned_if.update_speed()
                            self._update_speed()

        except Exception as e:
            if not self._stop_event.is_set() and self.status not in ("paused", "cancelled"):
                self.error_message = str(e)
                self.status = "error"
                if self.on_error:
                    self.on_error(self, str(e))
                return

        self._check_completion()

    def _check_completion(self):
        if self._stop_event.is_set() or self.status in ("paused", "cancelled"):
            return

        all_done = all(s.completed for s in self.segments)
        if all_done or (self.total_bytes > 0 and self.downloaded_bytes >= self.total_bytes):
            self.status = "completed"
            self.speed = 0.0
            if os.path.exists(self.meta_file):
                try:
                    os.remove(self.meta_file)
                except Exception:
                    pass
            if self.on_progress:
                self.on_progress(self)
            if self.on_complete:
                self.on_complete(self)
