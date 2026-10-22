"""
High-performance multi-connection segmented download worker.
Supports dynamic chunking, pause/resume, and direct offset writing.
"""
import os
import json
import time
import requests
import threading
from typing import Callable, List, Optional, Dict, Any
from urllib.parse import urlparse, unquote

class Segment:
    def __init__(self, index: int, start: int, end: int, downloaded: int = 0):
        self.index = index
        self.start = start
        self.end = end  # inclusive
        self.downloaded = downloaded
        self.completed = False

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
            "completed": self.completed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Segment':
        seg = cls(data["index"], data["start"], data["end"], data.get("downloaded", 0))
        seg.completed = data.get("completed", False)
        return seg

def probe_url(url: str, timeout: int = 10, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*"
    }
    if headers:
        req_headers.update(headers)

    filename = "download"
    total_bytes = 0
    supports_range = False

    try:
        # Try HEAD request first
        head_resp = requests.head(url, headers=req_headers, allow_redirects=True, timeout=timeout)
        final_url = head_resp.url
        content_len = head_resp.headers.get("Content-Length")
        accept_ranges = head_resp.headers.get("Accept-Ranges", "")
        content_disposition = head_resp.headers.get("Content-Disposition", "")
        
        # Test range support with a 0-0 range GET if uncertain
        range_test = requests.get(final_url, headers={**req_headers, "Range": "bytes=0-0"}, timeout=timeout, stream=True)
        if range_test.status_code == 206:
            supports_range = True
            if not content_len:
                cr = range_test.headers.get("Content-Range", "")
                if "/" in cr:
                    total_bytes = int(cr.split("/")[1])
        range_test.close()

        if content_len:
            total_bytes = int(content_len)
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

    return {
        "url": url,
        "final_url": final_url,
        "filename": filename,
        "total_bytes": total_bytes,
        "supports_range": supports_range
    }

class DownloadTask:
    def __init__(
        self,
        task_id: str,
        url: str,
        save_path: str,
        connections: int = 8,
        on_progress: Optional[Callable[['DownloadTask'], None]] = None,
        on_complete: Optional[Callable[['DownloadTask'], None]] = None,
        on_error: Optional[Callable[['DownloadTask', str], None]] = None
    ):
        self.task_id = task_id
        self.url = url
        self.save_path = save_path
        self.connections = connections
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
                    return
            except Exception:
                pass

        # Probe fresh URL
        info = probe_url(self.url)
        self.total_bytes = info["total_bytes"]
        self.supports_range = info["supports_range"]

        os.makedirs(os.path.dirname(self.save_path), exist_ok=True)

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
        if elapsed >= 0.5:
            delta = self.downloaded_bytes - self._last_downloaded
            self.speed = delta / elapsed
            self._last_time = now
            self._last_downloaded = self.downloaded_bytes
            if self.on_progress:
                self.on_progress(self)

    def _download_segment(self, seg: Segment):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        start_byte = seg.current_offset
        if start_byte > seg.end:
            seg.completed = True
            self._check_completion()
            return

        headers["Range"] = f"bytes={start_byte}-{seg.end}"

        try:
            with requests.get(self.url, headers=headers, stream=True, timeout=15) as resp:
                if resp.status_code not in (200, 206):
                    raise RuntimeError(f"HTTP {resp.status_code}")

                mode = "r+b" if os.path.exists(self.save_path) else "w+b"
                with open(self.save_path, mode) as f:
                    f.seek(start_byte)
                    for chunk in resp.iter_content(chunk_size=65536):
                        if self._stop_event.is_set():
                            break
                        if chunk:
                            with self._file_lock:
                                f.seek(seg.current_offset)
                                f.write(chunk)
                                seg.downloaded += len(chunk)
                                self.downloaded_bytes += len(chunk)
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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        mode = "ab" if (self.downloaded_bytes > 0 and self.supports_range) else "wb"
        if mode == "ab":
            headers["Range"] = f"bytes={self.downloaded_bytes}-"

        try:
            with requests.get(self.url, headers=headers, stream=True, timeout=15) as resp:
                if resp.status_code not in (200, 206):
                    raise RuntimeError(f"HTTP {resp.status_code}")

                with open(self.save_path, mode) as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if self._stop_event.is_set():
                            break
                        if chunk:
                            f.write(chunk)
                            self.downloaded_bytes += len(chunk)
                            if self.segments:
                                self.segments[0].downloaded = self.downloaded_bytes
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
