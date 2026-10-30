"""
Global resource coordinator: connection permits, origin/route caps, and shared bandwidth.
"""
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional
from .speed_limiter import SpeedLimiter

DEFAULT_MAX_ACTIVE_DOWNLOADS = 3
DEFAULT_MAX_GLOBAL_STREAMS = 64
DEFAULT_MAX_STREAMS_PER_TASK = 32
DEFAULT_MAX_STREAMS_PER_ORIGIN = 16
DEFAULT_MAX_STREAMS_PER_ROUTE = 16

@dataclass
class ResourceSnapshot:
    active_downloads: int = 0
    active_streams: int = 0
    origin_stream_counts: Dict[str, int] = field(default_factory=dict)
    route_stream_counts: Dict[str, int] = field(default_factory=dict)
    global_rate_bps: int = 0
    total_ingress_bytes: int = 0
    throughput: int = 0
    activeStreams: int = 0
    perRouteTraffic: Dict[str, int] = field(default_factory=dict)
    bufferedBytes: int = 0
    diskQueueBytes: int = 0
    errorCode: Optional[str] = None

class StreamPermit:
    """Context manager representing an acquired HTTP stream allocation."""
    def __init__(self, controller: 'ResourceController', task_id: str, origin: str, route_id: str):
        self.controller = controller
        self.task_id = task_id
        self.origin = origin
        self.route_id = route_id
        self.released = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def release(self):
        if not self.released:
            self.released = True
            self.controller._release_stream(self.task_id, self.origin, self.route_id)


class ResourceController:
    """
    Central system-wide coordinator enforcing global, per-origin, and per-route limits.
    """
    _instance: Optional['ResourceController'] = None
    _singleton_lock = threading.Lock()

    def __init__(
        self,
        max_active_downloads: int = DEFAULT_MAX_ACTIVE_DOWNLOADS,
        max_global_streams: int = DEFAULT_MAX_GLOBAL_STREAMS,
        max_streams_per_task: int = DEFAULT_MAX_STREAMS_PER_TASK,
        max_streams_per_origin: int = DEFAULT_MAX_STREAMS_PER_ORIGIN,
        max_streams_per_route: int = DEFAULT_MAX_STREAMS_PER_ROUTE,
        global_rate_bps: int = 0
    ):
        self.max_active_downloads = max_active_downloads
        self.max_global_streams = max_global_streams
        self.max_streams_per_task = max_streams_per_task
        self.max_streams_per_origin = max_streams_per_origin
        self.max_streams_per_route = max_streams_per_route

        self.global_limiter = SpeedLimiter(global_rate_bps)
        self._lock = threading.Lock()

        # Tracking state
        self._active_downloads: set = set()
        self._active_streams: int = 0
        self._task_streams: Dict[str, int] = {}
        self._origin_streams: Dict[str, int] = {}
        self._route_streams: Dict[str, int] = {}
        self._total_ingress_bytes: int = 0

    @classmethod
    def get_instance(cls) -> 'ResourceController':
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def set_global_rate(self, bps: int) -> None:
        """Set aggregate speed ceiling across all downloads."""
        self.global_limiter.set_limit(bps)

    def register_download(self, task_id: str) -> bool:
        """Admit a download if below max active downloads cap."""
        with self._lock:
            if len(self._active_downloads) >= self.max_active_downloads and task_id not in self._active_downloads:
                return False
            self._active_downloads.add(task_id)
            return True

    def unregister_download(self, task_id: str) -> None:
        """Unregister a completed/paused download."""
        with self._lock:
            self._active_downloads.discard(task_id)

    def acquire_stream(
        self,
        task_id: str,
        origin: str,
        route_id: str = "default",
        timeout_s: float = 5.0
    ) -> Optional[StreamPermit]:
        """
        Attempt to allocate an HTTP stream permit respecting all hierarchy boundaries.
        Returns StreamPermit or None if limits reached within timeout.
        """
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            with self._lock:
                task_count = self._task_streams.get(task_id, 0)
                origin_count = self._origin_streams.get(origin, 0)
                route_count = self._route_streams.get(route_id, 0)

                if (self._active_streams < self.max_global_streams and
                    task_count < self.max_streams_per_task and
                    origin_count < self.max_streams_per_origin and
                    route_count < self.max_streams_per_route):

                    self._active_streams += 1
                    self._task_streams[task_id] = task_count + 1
                    self._origin_streams[origin] = origin_count + 1
                    self._route_streams[route_id] = route_count + 1
                    return StreamPermit(self, task_id, origin, route_id)

            time.sleep(0.02)
        return None

    def _release_stream(self, task_id: str, origin: str, route_id: str) -> None:
        with self._lock:
            if self._active_streams > 0:
                self._active_streams -= 1
            if task_id in self._task_streams:
                self._task_streams[task_id] = max(0, self._task_streams[task_id] - 1)
            if origin in self._origin_streams:
                self._origin_streams[origin] = max(0, self._origin_streams[origin] - 1)
            if route_id in self._route_streams:
                self._route_streams[route_id] = max(0, self._route_streams[route_id] - 1)

    def record_ingress(self, route_id: str, task_id: str, byte_count: int) -> None:
        """Record transferred ingress bytes and apply shared bandwidth rate limiting."""
        self.global_limiter.acquire(byte_count)
        with self._lock:
            self._total_ingress_bytes += byte_count

    def snapshot(self) -> ResourceSnapshot:
        with self._lock:
            return ResourceSnapshot(
                active_downloads=len(self._active_downloads),
                active_streams=self._active_streams,
                origin_stream_counts=dict(self._origin_streams),
                route_stream_counts=dict(self._route_streams),
                global_rate_bps=self.global_limiter.limit,
                total_ingress_bytes=self._total_ingress_bytes,
                throughput=self.global_limiter.limit,
                activeStreams=self._active_streams,
                perRouteTraffic=dict(self._route_streams),
                bufferedBytes=0,
                diskQueueBytes=0,
                errorCode=None
            )

    def metrics(self) -> ResourceSnapshot:
        return self.snapshot()
