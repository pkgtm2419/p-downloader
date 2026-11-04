# Core Engine API Reference

This document provides internal API contracts, class signatures, and usage patterns for key modules in `core/`.

---

## 1. DownloadEngine (`core/engine.py`)

Central orchestrator managing active and queued downloads, lifecycle transitions, and event emission.

```python
class DownloadEngine(QObject):
    # Signals
    task_started = pyqtSignal(int)          # download_id
    task_progress = pyqtSignal(dict)        # {id, downloaded, total, speed, percent, eta}
    task_completed = pyqtSignal(int, str)   # download_id, output_path
    task_failed = pyqtSignal(int, str)      # download_id, error_message
    task_paused = pyqtSignal(int)           # download_id

    def __init__(self, db: DownloadDB, resource_controller: ResourceController | None = None): ...
    
    def create_download(self, request: DownloadRequest) -> int:
        """Probes URL, saves download record in database, and returns download_id."""
        
    def start_download(self, download_id: int) -> bool:
        """Enqueues and starts download if resource limits permit."""
        
    def pause_download(self, download_id: int) -> bool:
        """Cooperatively signals active workers to pause and checkpoints state."""
        
    def resume_download(self, download_id: int) -> bool:
        """Reconstructs task worker from saved journal state and resumes transfer."""
        
    def cancel_download(self, download_id: int, delete_files: bool = False) -> bool:
        """Aborts transfer and optionally deletes staging .part and journal files."""
        
    def update_download_url(self, download_id: int, new_url: str) -> bool:
        """Refreshes expired target URL (401/403 recovery) while preserving progress."""
```

---

## 2. UltraDownloader (`core/segment.py`)

Primary multi-connection HTTP download worker executing parallel segmented downloads.

```python
class UltraDownloader:
    def __init__(
        self,
        url: str,
        output_path: str,
        total_size: int,
        connections: int = 8,
        headers: dict | None = None,
        progress_callback: Callable[[dict], None] | None = None,
        resource_controller: ResourceController | None = None
    ): ...

    def start(self) -> None:
        """Spawns range worker pool and drives block queue to completion."""

    def pause(self) -> None:
        """Triggers cooperative pause flag and waits for active blocks to persist."""

    def cancel(self) -> None:
        """Signals worker pool cancellation."""
```

---

## 3. BlockScheduler (`core/block_scheduler.py`)

Dynamic block-level work distributor dividing files into bite-sized units and managing hedged tail execution.

```python
@dataclass
class BlockWork:
    block_id: int
    start_byte: int
    end_byte: int
    size: int
    status: str            # 'pending' | 'in_progress' | 'completed' | 'failed'
    assigned_worker: str | None = None
    retry_count: int = 0

class BlockScheduler:
    def __init__(self, total_size: int, block_size: int = 2 * 1024 * 1024): ...

    def claim_next_block(self, worker_id: str) -> BlockWork | None:
        """Claims next pending block for worker; returns None when all claimed."""

    def mark_completed(self, block_id: int) -> None:
        """Marks block finished and checks whether all blocks are completed."""

    def mark_failed(self, block_id: int, worker_id: str) -> None:
        """Re-enqueues block for retry; increments block retry count."""

    def claim_hedged_tail_block(self, idle_worker_id: str) -> BlockWork | None:
        """Identifies slow straggler blocks in progress and duplicates execution."""
```

---

## 4. AdaptiveConcurrencyController (`core/adaptive_concurrency.py`)

AIMD closed-loop controller auto-tuning connection concurrency.

```python
class AdaptiveConcurrencyController:
    def __init__(
        self,
        initial_streams: int = 4,
        min_streams: int = 1,
        max_streams: int = 32,
        additive_step: int = 1,
        decrease_factor: float = 0.5
    ): ...

    def record_success(self, bytes_transferred: int, duration_ms: float) -> None:
        """Records throughput sample and checks if stream count should increase."""

    def record_throttle_event(self, http_status: int) -> None:
        """Invoked on 429/503; cuts concurrency by decrease_factor and sets backoff."""

    def should_spawn_stream(self) -> bool:
        """Returns True if controller recommends increasing current stream count."""
```

---

## 5. HttpProbe (`core/http_probe.py`)

Strict URL capability probe verifying byte-range support and capturing server metadata.

```python
@dataclass
class ProbeResult:
    url: str
    effective_url: str
    status_code: int
    content_length: int
    supports_ranges: bool
    filename: str | None
    etag: str | None
    last_modified: str | None
    content_type: str | None

class HttpProbe:
    @staticmethod
    def probe(url: str, headers: dict | None = None, timeout: float = 10.0) -> ProbeResult:
        """Issues bounded Range GET to strictly verify server capability."""
```

---

## 6. TransferStore (`core/transfer_store.py`)

Durable file storage abstraction managing `.part` staging files, sparse pre-allocation, and atomic publishing.

```python
class TransferStore:
    def __init__(self, target_path: str, total_size: int): ...

    def prepare_staging_file(self) -> str:
        """Creates target_path.part and preallocates sparse disk capacity."""

    def write_block(self, start_offset: int, data: bytes) -> None:
        """Writes verified block into designated file byte range."""

    def publish_atomic(self) -> str:
        """Atomically replaces staging .part file to final destination path."""

    def cleanup_staging(self) -> None:
        """Removes incomplete .part and .pdownload journal files on cancel."""
```

---

## 7. ResourceController (`core/resource_controller.py`)

Global resource governor enforcing bandwidth limits and stream budgets.

```python
class ResourceController:
    def __init__(self, global_rate_limit: int = 0, max_active_tasks: int = 3): ...

    def acquire_bandwidth(self, requested_bytes: int) -> int:
        """Blocks/throttles caller according to token-bucket rate limiter."""

    def can_start_task(self) -> bool:
        """Returns True if current active task count is below ceiling."""

    def set_global_rate_limit(self, bytes_per_sec: int) -> None:
        """Updates global token-bucket refill rate dynamically."""
```

---

## 8. DownloadDB (`core/db.py`)

SQLite database layer managing persistent records, history, queue state, categories, and settings.

```python
class DownloadDB:
    def __init__(self, db_path: str | None = None): ...

    def add_download(self, record: DownloadRecord) -> int:
        """Inserts a new download record; returns generated record ID."""

    def get_download(self, download_id: int) -> DownloadRecord | None:
        """Retrieves download record by ID."""

    def update_status(self, download_id: int, status: str, error: str = "") -> None:
        """Updates task status ('queued', 'downloading', 'paused', 'completed', 'failed')."""

    def get_active_downloads(self) -> list[DownloadRecord]:
        """Returns list of currently active or queued downloads."""

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Reads configuration key from settings table."""

    def set_setting(self, key: str, value: Any) -> None:
        """Saves configuration key/value into settings table."""
```

