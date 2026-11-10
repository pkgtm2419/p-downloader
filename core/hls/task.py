"""
HLS Download Task Adapter (IM-01 / IM-02).
Implements the unified Task interface for HLS streams within DownloadEngine and GUI.
"""
from typing import Dict, Any, Optional, Callable
from .fetch import HLSDownloader


class HLSDownloadTask:
    def __init__(
        self,
        task_id: str,
        url: str,
        save_path: str,
        connections: int = 8,
        speed_limit: int = 0,
        headers: Optional[Dict[str, str]] = None,
        on_progress: Optional[Callable[['HLSDownloadTask'], None]] = None,
        on_complete: Optional[Callable[['HLSDownloadTask'], None]] = None,
        on_error: Optional[Callable[['HLSDownloadTask', str], None]] = None
    ):
        self.task_id = task_id
        self.url = url
        self.save_path = save_path
        self.connections = connections
        self.headers = headers or {}
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error

        self.total_bytes = 0
        self.downloaded_bytes = 0
        self.supports_range = True
        self.segments = []
        self.status = "queued"
        self.speed = 0.0
        self.error_message = ""
        self.is_hls = True

        self.downloader = HLSDownloader(url, save_path, max_workers=connections, headers=self.headers)
        self.downloader.add_callback(self._on_hls_state)

    def prepare(self):
        self.status = "queued"

    def start(self):
        self.status = "downloading"
        self.downloader.start()

    def pause(self):
        self.status = "paused"
        self.downloader.pause()

    def resume(self):
        self.status = "downloading"
        self.downloader.start()

    def cancel(self):
        self.status = "cancelled"
        self.downloader.cancel()

    def stop_recording(self):
        """Signals live recording to finish gracefully and preserve captured stream."""
        self.downloader.stop_live()

    def set_speed_limit(self, limit: int):
        pass

    def _on_hls_state(self, state: Dict[str, Any]):
        self.downloaded_bytes = state.get("downloaded_bytes", 0)
        self.speed = state.get("speed", 0.0)
        st = state.get("status", "")

        if st == "completed":
            self.status = "completed"
            if self.on_complete:
                self.on_complete(self)
        elif st == "error":
            self.status = "error"
            self.error_message = state.get("error_message", "HLS stream download failed")
            if self.on_error:
                self.on_error(self, self.error_message)
        elif st in ("downloading", "merging", "fetching", "recording"):
            self.status = "recording" if st == "recording" else "downloading"
            if self.on_progress:
                self.on_progress(self)
