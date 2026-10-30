# ROADMAP.md — P-Downloader IDM-Grade Reliability & Adaptive Concurrency

Based on `2026-10-30-p-downloader-idm-grade-improvements.md`.

## Phase A: Integrity Foundation (Tasks 1-4, 8)
- [x] Task 1: Baseline, reproducible origin and fault-injection tests (P0)
- [x] Task 2: Correct HTTP probing, metadata and download kind contracts (P0)
- [x] Task 3: Durable staging and verified byte-range workers (P0)
- [x] Task 4: Shared block queue and correct pause/resume lifecycle (P0)
- [x] Task 8: Retry classification, rate-limit recovery and final integrity (P1)

## Phase B: IDM-like Throughput and Efficiency (Tasks 5-7)
- [x] Task 5: Adaptive per-network concurrency and tail optimization (P1)
- [x] Task 6: Global resource budgets, shared rate limits and fairness (P1)
- [x] Task 7: Real network adapter discovery, routing and graceful failover (P1)

## Phase C: Browser Ownership and Authentication (Tasks 9-13)
- [x] Task 9: Authenticated, acknowledged desktop IPC and native-messaging protocol (P0)
- [x] Task 10: Browser extension capture coordinator and guaranteed decline fallback (P0)
- [x] Task 11: End-to-end capture acknowledgment and fallback UI integration (P0)
- [x] Task 12: Authenticated sessions and secret-safe request context (P0)
- [x] Task 13: Cross-browser install/coverage and unsupported-download fallback (P1)

## Phase D: UX, Compatibility and Rollout (Tasks 14-15)
- [x] Task 14: GUI resource observability, configuration and regression preservation (P1)
- [x] Task 15: Benchmark harness, CI, compatibility, security and staged release gate (P0)
