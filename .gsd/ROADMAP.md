# ROADMAP.md — P-Downloader v1.1.0 Roadmap

Based on `p-downloader-master-feature-and-optimization-plan.md`.

## Phase 0: Critical Bug Fixes & Safety Net (Completed)
- [x] Task 0.1: Context & Proxy Propagation Across All Network Layers (REQ-FIX-01)
- [x] Task 0.2: Implement RFC 959 / 3659 Resilient FTP Client (REQ-FIX-02)
- [x] Task 0.3: Fix HLS AES-128 Sequence IV & PKCS#7 Unpadding & Pause Crash (REQ-FIX-03)
- [x] Task 0.4: Fix Firefox Extension MV2 Compatibility & MV3 Fallback (REQ-FIX-04)

## Phase 1: Universal Video Extractor & HLS/DASH Overhaul (Completed)
- [x] Task 1.1: Intelligent URL & Content-Type Router (REQ-VID-01)
- [x] Task 1.2: Refactor to Universal `core/extractor.py` (REQ-VID-02)
- [x] Task 1.3: Multi-Threaded Fragment Acceleration (REQ-VID-03)
- [x] Task 1.4: Extractor Self-Updater Module (REQ-VID-04)

## Phase 2: BitTorrent Swarm Client & Integrity Verification (Completed)
- [x] Task 2.1: In-Process BitTorrent Client via `python-libtorrent` (REQ-TOR-01)
- [x] Task 2.2: Sequential Video Streaming Prioritization (REQ-TOR-02)
- [x] Task 2.3: 2D Piece Map & Peer Visualization UI (REQ-TOR-03)
- [x] Task 2.4: Automated RSS Torrent Watcher (REQ-TOR-04)
- [x] Task 2.5: Checksum Verification Subsystem (REQ-TOR-05)

## Phase 3: Debrid Cloud & Automatic Archive Extraction (Completed)
- [x] Task 3.1: Multi-Provider Debrid API Clients (REQ-DEB-01)
- [x] Task 3.2: Multi-Volume Archive Extraction Pipeline (REQ-ARC-01)

## Phase 4: Remote Control, Headless Server & AI MCP Server
- [ ] Task 4.1: Embedded HTTPS Web Remote with QR/PIN Pairing (REQ-REM-01)
- [ ] Task 4.2: Headless Daemon Mode for NAS & Docker (REQ-HDL-01)
- [ ] Task 4.3: Model Context Protocol (MCP) Server for AI Assistants (REQ-MCP-01)
- [ ] Task 4.4: IDM-Compatible CLI Switch Support (REQ-CLI-01)

## Phase 5: Privacy, VPN Fail-Closed & Geo-IP
- [ ] Task 5.1: VPN Exclusive Mode Fail-Closed Kill-Switch (REQ-NET-01)
- [ ] Task 5.2: DNS-over-HTTPS (DoH) Integration (REQ-NET-02)
- [ ] Task 5.3: Offline Geo-IP Location & Latency Display (REQ-NET-03)

## Phase 6: Modern UI/UX, Themes, Accessibility & Native AOT Compilation (<30MB RAM)
- [ ] Task 6.1: Dynamic Multi-Theme Engine (REQ-UI-01)
- [ ] Task 6.2: Accessibility & Screen Reader Compliance (REQ-UI-02)
- [ ] Task 6.3: Multi-Language Internationalization (86 Languages + RTL) (REQ-UI-03)
- [ ] Task 6.4: AOT Native C++ Compilation via Nuitka (<30 MB RAM) (REQ-OPT-01)
