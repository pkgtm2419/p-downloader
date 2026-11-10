# SPEC.md — P-Downloader Feature Parity, Bug Fixes & Native Optimization

Status: FINALIZED
Version: 1.1.0
Target: P-Downloader v1.1.0 Universal Feature Parity & Native Performance

## 1. Vision & Objectives
Bring P-Downloader to feature parity with Mister Download Manager (MDM), resolve all identified code-level bugs, enable universal streaming media extraction across 1,000+ sites, and optimize the application for native performance with <30 MB idle RAM and instant startup via Nuitka AOT compilation.

All changes strictly preserve P-Downloader's unique architectural strengths:
- Multi-NIC Socket Bandwidth Aggregation (`core/network_binder.py`)
- AIMD Closed-Loop Adaptive Concurrency Controller (`core/adaptive_concurrency.py`)
- Strict Two-Stage HTTP Range Probing (`core/http_probe.py`)
- Post-Download Antivirus Security Scan Pipeline (`core/antivirus.py`)

## 2. Requirements & Must-Haves

### Phase 0: Critical Bug Fixes & Safety Net
- [ ] **REQ-FIX-01**: Global Proxy & Context Propagation — Store and forward cookies, User-Agent, and Referer (`BrowserRequestContext`) to all download tasks (`engine.py`, `segment.py`, `add_dialog.py`). Route all HTTP range workers and `yt-dlp` through user-configured HTTP/SOCKS5 proxy (`core/network_binder.py`).
- [ ] **REQ-FIX-02**: RFC 959 / 3659 Resilient FTP Client — Implement `FTPDownloadTask` with `SIZE` pre-flight probing and `REST` resume in `core/ftp_downloader.py`.
- [ ] **REQ-FIX-03**: HLS AES-128 Cryptographic Correctness & Safe Pause — Compute IV as 16-byte big-endian `media_sequence + index` when IV is omitted. Apply PKCS#7 unpadding to decrypted segments. Return sentinel from paused workers to prevent unpack crashes (`core/hls_downloader.py`).
- [ ] **REQ-FIX-04**: Firefox Extension Compatibility — Fix background scripts in `manifest.firefox.json` and remove top-level `importScripts` in `background.js` to restore Firefox compatibility.

### Phase 1: Universal Video Extractor & HLS/DASH Overhaul
- [ ] **REQ-VID-01**: Unified Task Router — Implement `core/router.py` to route URLs by protocol, extension, and content-type without domain restrictions.
- [ ] **REQ-VID-02**: Universal Media Extraction — Replace `youtube_downloader.py` with `core/extractor.py`. Remove `is_youtube_url` restrictions. Support 1,000+ streaming sites (Vimeo, X, TikTok, Reddit, Twitch, news sites) with multi-audio, subtitle extraction, and DRM detection.
- [ ] **REQ-VID-03**: Multi-Threaded Fragment Acceleration — Accelerate HLS/DASH fragment downloads using concurrent chunk workers (`concurrent_fragment_downloads: 8`).
- [ ] **REQ-VID-04**: Extractor Self-Updater — Standalone updater in `core/updater_ytdlp.py` querying GitHub releases.

### Phase 2: BitTorrent Swarm Client & Checksum Verification
- [ ] **REQ-TOR-01**: BitTorrent Engine Integration — Real P2P swarm downloads via `python-libtorrent` in `core/torrent.py` supporting magnet links, DHT, PeX, trackers, and selective file exclusion.
- [ ] **REQ-TOR-02**: Sequential Video Streaming — Prioritize initial and final pieces for in-progress video playback in VLC.
- [ ] **REQ-TOR-03**: Piece Map & Peer Visualization — 2D piece grid and live peer monitoring in `gui/torrent_dialog.py`.
- [ ] **REQ-TOR-04**: Automated RSS Torrent Feed Monitor — Filter and auto-download matched torrents (`core/torrent_rss.py`).
- [ ] **REQ-TOR-05**: Checksum Integrity Verification — MD5, SHA-1, SHA-256 validation UI and automated post-download check.

### Phase 3: Debrid Cloud & Archive Extraction Pipeline
- [ ] **REQ-DEB-01**: Multi-Provider Debrid Support — OAuth device-flow and API clients for Real-Debrid, AllDebrid, and Premiumize in `core/debrid/`.
- [ ] **REQ-ARC-01**: Multi-Volume Archive Extraction — Auto-extract split `.part1.rar`, `.7z.001`, `.zip`, `.tar` via bundled `7za.exe` / native unpackers in `core/extractor_archive.py`.

### Phase 4: Remote Control, Headless Server & AI MCP Server
- [ ] **REQ-REM-01**: Embedded HTTPS Web Remote — TLS-encrypted local web interface with QR-code and 8-digit PIN pairing (`core/remote_server.py`).
- [ ] **REQ-HDL-01**: Headless Daemon & Docker Support — Run without X11/Qt via `main_headless.py` and minimal Docker container.
- [ ] **REQ-MCP-01**: Model Context Protocol (MCP) Server — Stdio JSON-RPC MCP server (`scripts/pdownloader-mcp.py`) exposing tools to Claude Desktop, Cursor, and AI agents.
- [ ] **REQ-CLI-01**: IDM-Compatible CLI Switches — `/d`, `/p`, `/f`, `/q`, `/s`, `/n` command line parameters.

### Phase 5: Privacy, VPN Fail-Closed & Geo-IP
- [ ] **REQ-NET-01**: VPN Exclusive Fail-Closed Kill-Switch — Pause active transfers immediately if the designated VPN adapter disconnects (`core/network_binder.py`).
- [ ] **REQ-NET-02**: Encrypted DNS (DoH) — DNS-over-HTTPS via Cloudflare / Quad9 (`core/dns_doh.py`).
- [ ] **REQ-NET-03**: Geo-IP & Latency Monitoring — Offline DB-IP lookup showing server country flags and ping times.

### Phase 6: Modern UI/UX, Themes, Accessibility & Native AOT Compilation (<30MB RAM)
- [ ] **REQ-UI-01**: Dynamic Theme Engine — Modern Fluent Dark, Fluent Light, Classic 98/XP, Aero/Neon with live switching (`gui/styles.py`).
- [ ] **REQ-UI-02**: Accessibility & HiDPI Scaling — Screen reader labels (NVDA/Narrator), keyboard tab navigation, and 100%-200% zoom.
- [ ] **REQ-UI-03**: Internationalization — `QTranslator` catalogs for 86 languages with RTL layout mirroring (`core/i18n.py`).
- [ ] **REQ-OPT-01**: Nuitka AOT Native Compilation — Standalone C++ compilation script (`scripts/build_native.py`) and lazy loading to achieve <30 MB idle RAM and instant startup.
