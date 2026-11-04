# Testing & Quality Assurance Guide

This guide details the test strategy, execution methods, mock fixtures, and testing best practices for **P-Downloader**.

---

## 1. Test Architecture & Structure

P-Downloader features a comprehensive offline test harness designed to rigorously test concurrent networking, pause/resume persistence, chaos faults, and IPC protocols without hitting live public websites.

```
tests/
├── support/
│   ├── http_origin.py           # FaultOrigin: Embedded local HTTP test server
│   └── __init__.py
├── benchmarks/                  # Performance and concurrency benchmarks
├── browser/                     # Extension test scripts
├── test_adaptive_concurrency.py # Tests AIMD stream tuning & backoff logic
├── test_antivirus.py            # Tests Windows Defender / ClamAV command hooks
├── test_block_scheduler.py      # Tests block claim queue, retry & hedged tail
├── test_browser_context.py      # Tests cookie/referer origin preservation
├── test_browser_handoff.py      # Tests 2-phase reserve/commit transaction states
├── test_browser_integration.py  # Tests end-to-end browser handoff flow
├── test_download_chaos.py       # Tests transient failures, changing ETags, 429
├── test_engine.py               # Tests engine queue, start, pause, resume
├── test_extension_installer.py  # Tests registry and manifest registration
├── test_gui_responsiveness.py   # Tests UI event loop starvation resistance
├── test_hls.py                  # Tests .m3u8 parsing and chunk assembly
├── test_http_faults.py          # Tests recovery against corrupted Range headers
├── test_http_probe.py           # Tests strict Range GET probe capability checks
├── test_ipc_protocol.py         # Tests framed JSON protocol & token auth
├── test_lifecycle_v2.py         # Tests state machine lifecycle transitions
├── test_multinetwork.py         # Tests multi-route socket binding
├── test_muxer.py                # Tests FFmpeg remuxing arguments
├── test_range_worker.py         # Tests block fetching, cancellation & writing
├── test_resource_controller.py  # Tests bandwidth token bucket and task limits
├── test_resume.py               # Tests zero-loss pause and resume from journal
├── test_retry_policy.py         # Tests exponential backoff and jitter calculations
├── test_scheduler.py            # Tests timed queue triggers & power actions
├── test_security.py             # Tests credential vault, SSRF & secret redaction
└── test_youtube_downloader.py   # Tests yt-dlp parameter normalization
```

---

## 2. Running Tests

### Running the Entire Test Suite
From the project root within your activated `.venv`:
```powershell
python -m pytest
```

### Running Specific Subsets
To run specific modules quickly:
```powershell
# Run core scheduler and concurrency tests
python -m pytest tests/test_adaptive_concurrency.py tests/test_block_scheduler.py tests/test_retry_policy.py -v

# Run engine lifecycle tests
python -m pytest tests/test_engine.py tests/test_lifecycle_v2.py -v

# Run security hardening tests
python -m pytest tests/test_security.py -v
```

### Running with Output Logs
```powershell
python -m pytest tests/test_block_scheduler.py -s -vv
```

---

## 3. The `FaultOrigin` Test Fixture (`tests/support/http_origin.py`)

A critical component of P-Downloader's test reliability is `FaultOrigin`, an in-memory HTTP server built with Python's native `http.server` that can programmatically simulate hostile network environments:

### Simulated Failure Modes:
- **`RANGE_IGNORED`**: Server responds with HTTP `200 OK` despite receiving a `Range: bytes=X-Y` header.
- **`WRONG_CONTENT_RANGE`**: Server responds with invalid or miscalculated `Content-Range` bounds.
- **`THROTTLED_429`**: Returns HTTP `429 Too Many Requests` or `503 Service Unavailable` on the first $N$ requests.
- **`CHANGING_ETAG`**: Mutates the ETag midway through download to simulate upstream file overwrites.
- **`PREMATURE_EOF`**: Closes connection abruptly after delivering partial bytes.
- **`SLOW_DRIP`**: Injects artificial delays to trigger timeout or hedged tail request logic.

### Example Test Using `FaultOrigin`:
```python
from tests.support.http_origin import FaultOrigin
from core.http_probe import HttpProbe

def test_handles_range_ignored_gracefully():
    with FaultOrigin(fault_mode="RANGE_IGNORED", payload=b"ABCDEF123456") as origin:
        result = HttpProbe.probe(origin.url)
        # Probe detects server does not honor range slicing:
        assert result.supports_ranges is False
```

---

## 4. Writing New Tests

When adding features or bug fixes, adhere to these test conventions:
1. **Zero External Network Dependencies**: All network tests must bind to `127.0.0.1` via `FaultOrigin` or mock requests.
2. **Deterministic Cleanup**: Always clean up temporary files in `tearDown()` or fixture finalizers (`tempfile.TemporaryDirectory`).
3. **Assert State Invariance**: Verify that pausing a download leaves `.part` and `.pdownload` files in a consistent, resumable state.
4. **Cooperative Cancellation**: Ensure tests assert that canceled tasks terminate worker threads in less than 500 ms without hanging.

