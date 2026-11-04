# P-Downloader Developer Guide

This guide describes development workflows, coding conventions, architectural rules, and instructions for extending **P-Downloader**.

---

## 1. Project Directory Structure

```
p-downloader/
├── core/                        # Core non-GUI transfer engine and utilities
│   ├── adaptive_concurrency.py  # AIMD dynamic stream auto-tuning controller
│   ├── antivirus.py             # Post-download virus scanner integration
│   ├── block_scheduler.py       # Block-level work queue & hedged tail scheduler
│   ├── browser_context.py       # Cookies, User-Agent, and Referer encapsulation
│   ├── browser_handoff.py       # 2-Phase browser handoff transaction manager
│   ├── categories.py            # File extension-to-category classifier
│   ├── credentials_manager.py   # Secure Fernet encrypted credential store
│   ├── db.py                    # SQLite database, queries, and schema migration
│   ├── download_models.py       # Dataclasses (DownloadRequest, BlockWork, etc.)
│   ├── engine.py                # Central DownloadEngine orchestrator
│   ├── hls_downloader.py        # HLS (.m3u8) streaming segment downloader
│   ├── http_errors.py           # HTTP error classification & secret sanitization
│   ├── http_probe.py            # Strict HTTP Range and capability probe
│   ├── ipc.py                   # Local framed IPC client/server & token auth
│   ├── muxer.py                 # FFmpeg auto-remuxing audio/video processor
│   ├── network_binder.py        # Multi-adapter socket binder (NIC aggregation)
│   ├── network_routes.py        # OS network interface and route detector
│   ├── range_worker.py          # HTTP byte-range worker fetching blocks
│   ├── resource_controller.py   # Global bandwidth & connection limiter
│   ├── retry_policy.py          # Exponential backoff and retry rules
│   ├── scheduler_service.py     # Timed queue scheduler & system power actions
│   ├── segment.py               # UltraDownloader segmented transfer coordinator
│   ├── speed_limiter.py         # Token-bucket rate limiter
│   ├── spider.py                # Recursive web crawler & link grabber
│   ├── torrent.py               # Bencode parser & Magnet link metadata extractor
│   ├── transfer_store.py        # Durable staging (.part) and atomic publisher
│   └── youtube_downloader.py    # yt-dlp integration for video sites
├── gui/                         # PyQt6 desktop graphical user interface
│   ├── add_dialog.py            # "Add URL" modal with auto-clipboard sniffing
│   ├── batch_dialog.py          # Batch URL importer dialog
│   ├── download_dialog.py       # Active download modal & segment visualizer
│   ├── grabber_dialog.py        # Web site grabber & crawler interface
│   ├── icons.py                 # SVG/PNG icon asset provider
│   ├── integration_prompt_dialog.py # Browser interception confirmation modal
│   ├── main_window.py           # Primary application window & system tray
│   ├── quick_prompt_dialog.py   # Quick download prompt popup
│   ├── refresh_dialog.py        # Expired link (403/410) recovery dialog
│   ├── scheduler_dialog.py      # Timed queue scheduling settings UI
│   ├── settings_dialog.py       # Global preferences and network configuration
│   ├── site_logins_dialog.py    # Saved credentials manager UI
│   ├── styles.py                # Modern high-DPI dark theme stylesheets (QSS)
│   └── video_quality_dialog.py  # Video stream resolution & audio picker UI
├── browser_extension/           # Manifest V3 browser extension & native bridge
│   ├── background.js            # Background service worker & download hook
│   ├── content.js               # In-page media sniffer & floating UI pill
│   ├── installer.py             # Cross-platform native host manifest installer
│   ├── manifest.json            # Chromium Manifest V3 configuration
│   ├── manifest.firefox.json    # Firefox Manifest V2/V3 configuration
│   └── pdownloader_native_host.py # Stdio native messaging bridge
├── tests/                       # Unit, integration, stress, and chaos tests
├── resources/                   # Application icons, logos, and graphics
├── docs/                        # Comprehensive technical documentation
├── main.py                      # Application bootstrap entry point
├── pyproject.toml               # Build configuration and project metadata
└── requirements-dev.txt         # Development dependencies
```

---

## 2. Coding Standards & Conventions

### 2.1 Python Code Style
- **PEP 8 Compliance**: Enforced via `flake8`.
- **Type Annotations**: Use Python 3.10+ union syntax (`str | None`, `list[int]`) across all core classes.
- **Line Length**: Soft limit of 100 characters; hard limit of 120 characters.
- **Docstrings**: Provide clear docstrings for all classes and public methods explaining arguments, returns, and raised exceptions.

### 2.2 Thread Safety Rules (Crucial)
1. **Never Touch GUI Widgets from Background Threads**:
   Any modification of PyQt6 widgets from a worker thread causes unstable memory states or hard segfaults.
2. **Use Qt Signals (`pyqtSignal`) for Cross-Thread Events**:
   ```python
   # Correct: Define a signal and emit it from the worker
   class WorkerThread(QThread):
       progress_updated = pyqtSignal(dict)

       def run(self):
           # In background thread
           self.progress_updated.emit({"percent": 50.0, "speed": 1048576})

   # In GUI class:
   worker.progress_updated.connect(self.on_progress_updated)
   ```
3. **Use Cooperative Cancellation**:
   Worker loops must periodically inspect `self.stop_requested.is_set()` or `self._cancelled` and break immediately without leaving hanging file handles.

---

## 3. Lifecycle of a Download

When a user adds a URL or the browser extension intercepts a file:

1. **Request Intake**:
   - URL is entered in [`gui/add_dialog.py`](file:///gui/add_dialog.py) or received via IPC (`core/ipc.py`).
2. **Strict HTTP Capability Probe**:
   - [`core/http_probe.py`](file:///core/http_probe.py) probes the target URL using a bounded Range GET (`bytes=0-0`).
   - Retrieves file size, filename from `Content-Disposition`, ETag, and verifies whether the server correctly returns `206 Partial Content`.
3. **Record Creation**:
   - `DownloadRecord` is inserted into SQLite via [`core/db.py:DownloadDB.add_download()`](file:///core/db.py).
4. **Engine Enqueue**:
   - [`core/engine.py:DownloadEngine.start_download()`](file:///core/engine.py) checks global resource limits via [`core/resource_controller.py`](file:///core/resource_controller.py).
   - Instantiates an `UltraDownloader` task.
5. **Staging & Work Allocation**:
   - [`core/transfer_store.py`](file:///core/transfer_store.py) prepares `output.part` staging storage and initializes `.pdownload` journal.
   - [`core/block_scheduler.py`](file:///core/block_scheduler.py) partitions total size into verified blocks (e.g., 2 MiB blocks).
6. **Parallel Transfer**:
   - Range workers claim pending blocks and stream content into `.part` offsets.
   - Dynamic concurrency controller ([`core/adaptive_concurrency.py`](file:///core/adaptive_concurrency.py)) tunes stream counts based on server throughput and response codes.
7. **Verification & Atomic Publish**:
   - Once all blocks reach completion, the file is atomically renamed (`os.replace`) to the user's destination path.
   - Post-download hooks execute (optional antivirus scan, desktop notifications).

---

## 4. Extending P-Downloader

### Adding a New Download Protocol / Source
1. Define the protocol parser in `core/` (similar to `core/hls_downloader.py` or `core/youtube_downloader.py`).
2. Add URL detection pattern in `core/download_models.py` or `core/engine.py`.
3. In `core/engine.py:create_download()`, route matching URLs to your dedicated worker class.
4. Ensure your worker implements standard lifecycle methods:
   - `start()`
   - `pause()`
   - `resume()`
   - `cancel()`
   - Emits progress updates via a callback or signal.
5. Write unit tests in `tests/test_<protocol>.py`.

### Creating a New GUI Modal Dialog
1. Inherit from `QDialog` in `gui/`.
2. Apply the application dark theme styling from [`gui/styles.py`](file:///gui/styles.py).
3. Ensure parent window is passed for correct modal centering.
4. Hook actions to engine functions asynchronously (using worker threads if the action requires network or disk operations).

