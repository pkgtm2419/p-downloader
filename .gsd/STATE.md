# STATE.md — Current Session State

## Current Position
- **Milestone**: P-Downloader v1.1.0 Universal Feature Parity & Native Performance
- **Active Phase**: Phase 0 — Critical Bug Fixes & Safety Net (COMPLETED)
- **Target Repo**: `D:\p-downloader`
- **Next Phase**: Phase 1 — Universal Video Extractor & HLS/DASH Overhaul

## Task Queue (Phase 0 — Complete)
- [x] Task 0.1: Context & Proxy Propagation Across All Network Layers (REQ-FIX-01) — Commit `d3ec5d9`
- [x] Task 0.2: Implement RFC 959 / 3659 Resilient FTP Client (REQ-FIX-02) — Commit `d473da8`
- [x] Task 0.3: Fix HLS AES-128 Sequence IV & PKCS#7 Unpadding & Pause Crash (REQ-FIX-03) — Commit `bb72fb7`
- [x] Task 0.4: Fix Firefox Extension MV2 Compatibility & MV3 Fallback (REQ-FIX-04) — Commit `df9d478`

## Verification Proofs
- **Python Test Runner**: 151/151 unit and integration tests passing (`Ran 151 tests in 27.290s. OK`).
- **Node.js Browser Runner**: 18/18 WebExtension tests passing (`pass 18, fail 0`).
- **Commits Landed**:
  - `d3ec5d9` fix(engine): propagate headers, context and proxy configuration across all network layers
  - `d473da8` feat(ftp): implement RFC 959 / 3659 resilient FTP and FTPS downloader client
  - `bb72fb7` fix(hls): correct AES-128 sequence IV calculation, add PKCS#7 unpadding and fix pause unpack crash
  - `df9d478` fix(extension): restore Firefox MV2 compatibility and declare content scripts and background scripts

## Next Phase Queue (Phase 1)
- [ ] Task 1.1: Intelligent URL & Content-Type Router (REQ-VID-01)
- [ ] Task 1.2: Refactor to Universal `core/extractor.py` (REQ-VID-02)
- [ ] Task 1.3: Multi-Threaded Fragment Acceleration (REQ-VID-03)
- [ ] Task 1.4: Extractor Self-Updater Module (REQ-VID-04)

## Next Phase
- Phase 1: Universal Video Extractor & HLS/DASH Overhaul (REQ-VID-01 through REQ-VID-04)
