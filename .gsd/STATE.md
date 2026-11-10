# STATE.md — Current Session State

## Current Position
- **Milestone**: P-Downloader v1.1.0 Universal Feature Parity & Native Performance (SHIPPED & RELEASED)
- **Active Release**: `v1.1.0` (Tagged and Pushed to GitHub)
- **Target Repo**: `D:\p-downloader` (`https://github.com/pkgtm2419/p-downloader.git`)
- **Current Git Branch**: `master` (Synchronized with origin, all 26 atomic commits pushed)

## Shipped Architecture & Features
- [x] **Universal Media Extraction (`core/extractor.py`)**: Universal extractor for 1,000+ sites (YouTube, Vimeo, Twitter/X, TikTok, Reddit, Twitch, etc.), smart routing, and pinned updater.
- [x] **Modular HLS & DASH Engine (`core/hls/`)**: CMAF fMP4 `#EXT-X-MAP`, separate audio renditions (`#EXT-X-MEDIA:TYPE=AUDIO`), AES-128 key rotation, and continuous live stream recording.
- [x] **Browser Extension Sniffing v2 (`browser_extension/`)**: DASH `.mpd` support, MSE `blob:` video resolution via `pageUrl`, session storage persistence, and options diagnostic tool.
- [x] **Resilient FTP/FTPS & BitTorrent Client**: Full RFC 959/3659 FTP/FTPS with TLS `PROT P`, BitTorrent swarm task, piece map widget, and RSS watcher.
- [x] **Debrid Cloud & Archive Extraction**: Real-Debrid, AllDebrid, and Premiumize client adapters with multi-volume `.zip`/`.rar`/`.7z` unpacker.
- [x] **Web Remote, Headless Daemon & MCP Server**: Embedded REST/WebSocket server, headless daemon for Docker/NAS, Model Context Protocol server for AI assistants, and IDM-compatible CLI flags.
- [x] **Network Security, VPN Kill Switch & DoH**: SSRF IP pinning blocking private IPs/cloud metadata, encrypted DNS-over-HTTPS (DoH), and fail-closed VPN kill switch.
- [x] **GUI MVC Modularization & 9 Themes**: `DownloadTableModel(QAbstractTableModel)` and `DownloadController`, typed settings schema registry (`core/settings.py`), 9 curated themes, screen reader accessibility, and RTL mirroring.
- [x] **AOT Compilation & Packaging**: Nuitka compilation pipeline (<30 MB RAM), official Windows Setup, portable executables, Linux tarball, and multi-OS installation guides.

## Empirical Verification Proofs
- **Python Full Test Runner**: 209/209 tests passing (`Ran 209 tests in 30.643s. OK`).
- **Node.js Browser Runner**: 23/23 tests passing (`pass 23, fail 0`).
- **Total Test Coverage**: 232 automated unit, integration, contract, and browser extension tests passing with 0 failures.
