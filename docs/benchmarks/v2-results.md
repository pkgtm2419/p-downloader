# P-Downloader v2 Architecture & Benchmark Verification (2026-10-30)

## Overview
This document records the empirical verification and benchmark results for the IDM-grade improvements landed in P-Downloader v2 (Phases A-D).

## 1. Fault Tolerance & Integrity Baselines (Compared to Baseline)

| Test Condition | Legacy Engine (v1.0.3) | v2 Architecture (v1.0.6) | Verification Suite |
| :--- | :--- | :--- | :--- |
| **0-Byte Empty Body** | Hangs in `downloading` | **Immediate completion (PASS)** | `tests.test_http_faults` |
| **Unknown-Length Stream** | Hangs in `downloading` | **Completes on EOF (PASS)** | `tests.test_http_faults` |
| **False Range Support (200 on Range)** | Corrupts destination file | **Falls back to single-stream (PASS)** | `tests.test_http_probe` |
| **Broken Content-Range Header** | Blind write at arbitrary offset | **Strict rejection & worker retry (PASS)** | `tests.test_range_worker` |
| **Interrupted / Dropped Connection** | Stalls indefinitely | **Durable resume from `.part` journal (PASS)** | `tests.test_lifecycle_v2` |
| **Server Throttling (429 / 503)** | Immediate hard failure | **Backoff with jitter & Retry-After (PASS)** | `tests.test_retry_policy` |
| **System Resource Limits** | Unbounded thread contention | **Shared permit token bucket & route caps (PASS)** | `tests.test_resource_stress` |
| **Browser Extension Handoff** | Desynchronized downloads | **Transactional 2-phase reserve/commit (PASS)** | `tests.test_browser_integration` |

## 2. Throughput Benchmarks (Local Deterministic Origin)

Run command: `python tests/benchmarks/benchmark_downloads.py --size-mb 5 --connections 1,4,8,16`

| Streams | Throughput | Duration | SHA-256 Checksum Match | Retries |
| :---: | :---: | :---: | :---: | :---: |
| **1 Stream** | 27.0 MB/s | 0.185 s | **Match (100% integrity)** | 0 |
| **4 Streams** | **80.1 MB/s** | **0.062 s** | **Match (100% integrity)** | 0 |
| **8 Streams** | 39.5 MB/s | 0.126 s | **Match (100% integrity)** | 0 |
| **16 Streams** | 8.7 MB/s | 0.575 s | **Match (100% integrity)** | 0 |

*Note: On local loopback with near-zero latency, 4 concurrent streams saturated the I/O pipeline with maximum efficiency (~3x speedup over single stream). On wide-area networks with latency (RTT > 50ms), 8-16 streams provide higher multiplexing advantages.*

## 3. Crash-Safe Staging & Atomic Commit
- All downloads stage to `.part` files inside the target directory or temporary staging store.
- Offsets are verified per block via `BoundedBlockWriter` and tracked in SQLite `transfer_journals`.
- Only upon 100% byte verification and stream closure is the `.part` file atomically published (`os.replace`) to the final user path.
- Existing files are never partially overwritten; collision policies resolve duplicate names safely.

## 4. Rollback & Telemetry Flags
- `P_DOWNLOADER_ENGINE_V2=1` (Enabled by default; set to 0 for legacy single-segment fallback).
- `P_DOWNLOADER_BROWSER_CAPTURE_V2=1` (Enabled by default for transactional reserve/commit handoff).
