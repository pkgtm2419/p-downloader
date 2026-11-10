# 🚀 P-Downloader v1.1.0 — Universal Media Extractor, Live HLS/DASH, FTP, BitTorrent & Debrid

P-Downloader v1.1.0 is our biggest architectural update yet, transforming P-Downloader into a high-performance, universal multi-protocol download manager and media extraction power-house.

---

## 📥 Quick Download Links

| Package | Platform | Direct Download |
| :--- | :--- | :--- |
| 🪟 **Windows Setup Installer** | Windows 10/11 (x64) | [**Download P-Downloader-Setup.exe**](https://github.com/pkgtm2419/p-downloader/releases/download/v1.1.0/P-Downloader-Setup.exe) |
| 🪟 **Windows Standalone Portable** | Windows 10/11 (x64) | [**Download P-Downloader-Portable.exe**](https://github.com/pkgtm2419/p-downloader/releases/download/v1.1.0/P-Downloader-Portable.exe) |
| 🪟 **Windows Portable Archive** | Windows (x64) | [**Download P-Downloader-Windows-x64-Portable.zip**](https://github.com/pkgtm2419/p-downloader/releases/download/v1.1.0/P-Downloader-Windows-x64-Portable.zip) |
| 🐧 **Linux Standalone Tarball** | Linux (x64) | [**Download P-Downloader-Linux-x64.tar.gz**](https://github.com/pkgtm2419/p-downloader/releases/download/v1.1.0/P-Downloader-Linux-x64.tar.gz) |
| 🌐 **Browser Extension** | Chrome / Edge / Brave / Firefox | [**Download pdownloader-browser-extension.zip**](https://github.com/pkgtm2419/p-downloader/releases/download/v1.1.0/pdownloader-browser-extension.zip) |

*(Direct links automatically serve the compiled v1.1.0 binaries. Checksums are verified in `SHA256SUMS.txt`)*.

---

## 🌟 Major Highlights & New Features

### 🎬 1. Universal Video & Audio Extraction (1,000+ Sites)
- **Universal Engine (`core/video_extractor.py`)**: Seamless extraction from YouTube, Vimeo, Twitter/X, Reddit, TikTok, Facebook, Instagram, Bilibili, and 1,000+ media portals via integrated `yt-dlp` and `ffmpeg`.
- **Browser Authentication Forwarding**: Passes cookies, User-Agent, and Referer headers from browser extensions directly to the backend downloader to bypass anti-hotlinking and access private or member-only media.
- **Dynamic Quality Selector (`gui/video_quality_dialog.py`)**: Choose between exact resolutions (8K, 4K, 1440p, 1080p, 720p), framerates (60fps HDR), codec profiles (AV1, VP9, H.264), audio-only extraction (MP3, AAC, FLAC), and subtitle tracks.
- **Signed Self-Updating Pipeline (`core/video_updater.py`)**: Automated updater for extractor components with SHA-256 verification and automatic rollback if an update fails.

### 📡 2. Modular HLS & DASH Streaming Engine
- **RFC 8216 Compliance (`core/hls/`)**: Full support for master playlists, variant streams, and byte-range segment requests (`#EXT-X-BYTERANGE`).
- **CMAF Fragmented MP4 (fMP4)**: Handles `#EXT-X-MAP:URI` initialization sequences correctly across all segments.
- **AES-128 Key Rotation**: Full decryption support including implicit initialization vectors from `#EXT-X-MEDIA-SEQUENCE` and on-the-fly key rotations.
- **Audio/Video Demux & Muxing**: Downloads separate `#EXT-X-MEDIA:TYPE=AUDIO` streams and seamlessly remuxes them into a single playable MP4 or MKV container.
- **Live Stream Recording**: Sliding window live recorder with ring buffer memory safety and zero data corruption on pause or finish.

### 📁 3. Resilient RFC 959/3659 FTP & FTPS Client
- **Secure File Transfers (`core/ftp/`)**: Full support for standard FTP and explicit TLS/SSL encrypted FTPS (`AUTH TLS`) with encrypted data channels (`PROT P`).
- **Resumption & Auto-Sizing**: Full resume capability via `REST` command and accurate byte sizing via `SIZE`.
- **Active & Passive Modes**: Automatic EPSV / PASV mode fallback for restrictive firewall and NAT environments.

### 🧲 4. Swarm BitTorrent Engine & RSS Watcher
- **Swarm Torrent Transfers (`core/torrent/`)**: Support for `.torrent` files and `magnet:` links with DHT, peer exchange, and tracker communication.
- **Interactive Torrent Inspector (`gui/torrent_dialog.py`)**: Inspect torrent contents, deselect unwanted files, assign per-file priority, and monitor seed/peer health.
- **Live Piece Visualizer**: Dynamic visual piece map displaying chunk download progress in real time.
- **Automated RSS Watcher**: Periodically fetch RSS feeds, evaluate regex patterns, and auto-queue matching releases.

### ☁️ 5. Cloud Debrid Support & Archive Unpacker
- **Multi-Host Debrid Engines (`core/debrid/`)**: Native API integration for Real-Debrid, AllDebrid, and Premiumize to download premium files at uncapped speeds.
- **Integrated Archive Unpacker (`core/extractor.py`)**: Automated post-download extraction for `.zip`, `.tar.gz`, `.tar.bz2`, and `.7z` multi-part and password-protected archives.

### 🌐 6. Web Remote Dashboard & Headless Daemon
- **Headless Mode (`main_headless.py`)**: Run P-Downloader as a lightweight daemon without GUI on servers, NAS devices, or Docker.
- **Mobile-Friendly Web UI**: Full web interface to add URLs, inspect progress, control speeds, and pause/resume downloads from smartphones or external browsers.
- **Docker Ready**: First-class `Dockerfile` and `docker-compose.yml` configs for containerized home lab deployments.

### 🤖 7. Model Context Protocol (MCP) Server for AI Assistants
- **AI Integration (`scripts/pdownloader_mcp.py`)**: Native MCP server enabling AI coding assistants and automation workflows (Claude, Gemini, Antigravity) to manage downloads, trigger batch jobs, and query network status.

### 🔒 8. Hardened Network Privacy & Security
- **VPN Fail-Closed Kill Switch (`core/network_detector.py`)**: Hard kill switch locks downloads if the designated VPN network adapter drops, preventing IP leakage.
- **Encrypted DNS (DoH)**: Built-in DNS-over-HTTPS resolver (Cloudflare, Quad9, Google) to defeat ISP DNS hijacking and censorship.
- **SSRF Mitigation**: IP pinning and private network address filtering prevent DNS rebinding attacks and local intranet probing.
- **Sanitized Diagnostics (`core/logging_setup.py`)**: Automated log export bundles redacting auth tokens, API keys, and sensitive credentials.

### 🎨 9. Modern GUI Architecture & Accessibility
- **Decoupled MVC Pattern (`gui/models/download_table_model.py`)**: High-performance Qt Model/View architecture capable of smoothly rendering thousands of downloads.
- **9 Built-in Themes**: Emerald, Dark Slate, Midnight Blue, Dracula, Nord, Solarized Dark, Gruvbox, Cyberpunk, and Light Clean.
- **Screen Reader Accessibility**: Standardized accessible roles, descriptions, and keyboard focus traversal for NVDA and Windows Narrator.
- **RTL Language Mirroring**: Complete Right-to-Left layout mirroring support for Arabic, Hebrew, and Persian locales.

### ⚡ 10. Low-RAM AOT Compilation & Multi-OS Packaging
- **Nuitka Ahead-of-Time Compilation (`scripts/build_nuitka.py`)**: Produces standalone binaries consuming <30 MB of RAM with instant startup.
- **Cross-Platform Compatibility**: Full testing and packaging for Windows (Setup & Portable), Linux (x64 Tarball), and macOS.

---

## 🧪 Verification & Test Suite

- **209 Python Tests Passing**: Comprehensive unit, regression, integration, and mock network tests.
- **23 Node.js Browser Tests Passing**: Full suite of manifest, content script, and native messaging tests.
- **Flake8 & Type Safety**: Zero syntax or undefined symbol errors across all packages.
