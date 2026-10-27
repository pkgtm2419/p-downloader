<div align="center">

<img src="resources/logo.png" alt="P-Downloader Logo" width="128" height="128" />

# P-Downloader (Pure Downloader)

### Ultra High-Performance Desktop Download Accelerator & Bandwidth Manager
*A clean-room, cross-platform open-source download accelerator built from scratch in Python and PyQt6.*

[![CI](https://github.com/pkgtm2419/p-downloader/actions/workflows/ci.yml/badge.svg)](https://github.com/pkgtm2419/p-downloader/actions/workflows/ci.yml)
[![Release](https://github.com/pkgtm2419/p-downloader/actions/workflows/release.yml/badge.svg)](https://github.com/pkgtm2419/p-downloader/actions/workflows/release.yml)
[![GitHub Release](https://img.shields.io/github/v/release/pkgtm2419/p-downloader?include_prereleases&style=flat-square&color=blue)](https://github.com/pkgtm2419/p-downloader/releases/latest)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue?style=flat-square&logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-0078D6?style=flat-square)](https://github.com/pkgtm2419/p-downloader/releases)

[**Download Releases**](https://github.com/pkgtm2419/p-downloader/releases/latest) •
[**Features**](#-features) •
[**Windows Installation**](#1-windows-installation) •
[**Linux Installation**](#2-linux-installation-ubuntudebianfedoraarch) •
[**macOS Installation**](#3-macos-installation) •
[**Browser Integration**](#-browser-extension-integration-chrome-edge-brave-firefox) •
[**CLI Mode**](#-cli-headless-mode) •
[**Build from Source**](#-building-and-packaging)

</div>

---

## ⚡ Overview

**P-Downloader** is a modern, open-source desktop download manager and acceleration engine. Designed as a clean alternative to legacy utilities like Internet Download Manager (IDM), P-Downloader maximizes bandwidth utilization through dynamic chunking, multi-adapter network bonding, resume resilience, streaming HLS parsing, FFmpeg remuxing, video stream sniffing, and browser interception across Windows, Linux, and macOS.

---

## ✨ Features

### 🚀 High-Speed Multi-Connection Acceleration
- **Dynamic Connection Slicing**: Splits files into up to **32 concurrent streams** using HTTP `Range` headers to bypass server-side single-connection throttling.
- **Sparse File Pre-allocation**: Instantly reserves file capacity on disk, reducing fragmentation and eliminating write latency.

### 🎬 In-Page Video Sniffer & HLS / DASH Streaming
- **Browser Media Sniffing**: In-page floating download pill detects HTML5 video, streaming playlists, and audio tracks.
- **HLS (.m3u8) Chunk Processor**: Downloads and concatenates fragmented live and VoD streaming video segments.
- **FFmpeg Auto-Muxing**: Merges separated 1080p/4K video and high-bitrate audio streams into finished MP4/MKV files.

### 🌐 Multi-Network Bandwidth Aggregation (Bonding)
- **Multi-Adapter Pooling**: Automatically detects all active network interfaces (e.g., Ethernet + Wi-Fi + 5G USB/Hotspot tethering).
- **Socket Source Binding**: Pins concurrent HTTP segment connections across distinct physical network adapters to aggregate total available bandwidth.

### 🔄 Resilient Pause, Resume & Expired Link Recovery
- **Zero-Loss Pause & Resume**: Saves live chunk offsets in `.pdownload` sidecar state files. Downloads can be resumed after network drops or machine restarts.
- **Refresh Download Address (IDM-Grade)**: When temporary pre-signed links (Google Drive, Dropbox, Rapidgator, MEGA) expire with HTTP 401/403/410, seamlessly update the target URL without restarting from 0%.

### 🧲 Torrent & Magnet Link Support
- **Built-in Bencode/Bdecode Parser**: Native extraction of `.torrent` file metadata and BitTorrent parameters without heavy external dependencies.
- **Magnet Link Resolution**: Parses display names, info hashes, and multi-tier tracker addresses instantly.

### 🔒 Site Logins & Authentication Injection
- **Domain Credentials Store**: Securely stores basic HTTP and Bearer token credentials for private repositories, corporate intranets, and authenticated file servers.
- **Automatic Header Injection**: Matches target URLs to domain profiles and applies authentication automatically.

### ⏱️ High-Precision Speed Limiter & Multi-Queue Scheduler
- **Token-Bucket Throttling**: Restrict transfer speeds from 100 KB/s up to Gigabit capacity so background downloads never disrupt gaming, VoIP, or video streaming.
- **Timed Multi-Queue Scheduler**: Automate off-peak queues with automatic computer shutdown, sleep, or network disconnect.

### 🖥️ Native Desktop Experience & System Tray
- **Modern Dark Interface**: Custom high-DPI desktop UI built with PyQt6.
- **Live Segment Visualizer**: Real-time progress bars showcasing individual download streams and network adapter allocations.
- **Single-Instance IPC**: Running background instances accept new downloads instantly from the command line or browser extension.
- **System Tray Execution**: Minimize to the system notification tray with completion alerts.

---

## 🏗️ Architecture & Component Overview

```
                          ┌──────────────────────────┐
                          │   Browser Integration    │
                          │   (Chrome / Edge MV3)    │
                          └─────────────┬────────────┘
                                        │ Native Messaging IPC
                                        ▼
┌───────────────────────┐  IPC  ┌──────────────────────────┐
│   CLI Engine Mode     │ ◄───► │  PyQt6 Desktop GUI &     │
│  (Headless Terminal)  │       │  System Tray Controller  │
└───────────┬───────────┘       └────────────┬─────────────┘
            │                                │
            └───────────────────┬────────────┘
                                │
                                ▼
                   ┌──────────────────────────┐
                   │  Central Download Engine │
                   │  (Queue / Task Manager)  │
                   └────────────┬─────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌────────────────┐      ┌────────────────┐      ┌────────────────┐
│ SQLite Database│      │  Multi-Adapter │      │ Speed Limiter  │
│  Persistence   │      │Bandwidth Bond  │      │(Token Bucket)  │
└────────────────┘      └───────┬────────┘      └────────────────┘
                                │
                                ▼
                   ┌──────────────────────────┐
                   │ Segmented Range Worker   │
                   │ (Up to 32 Parallel Conns)│
                   └────────────┬─────────────┘
                                │
                                ▼
                   ┌──────────────────────────┐
                   │ Sparse Preallocated Disk │
                   │ + .pdownload Meta State  │
                   └──────────────────────────┘
```

---

## 📥 Downloads & Official Releases

You can download compiled release packages from the [**GitHub Releases**](https://github.com/pkgtm2419/p-downloader/releases/latest) page:

| Package File | Operating System | Description | Direct Download |
| :--- | :--- | :--- | :--- |
| **P-Downloader-Setup.exe** | **Windows** (10/11 x64) | Full Windows Setup Installer with Desktop icon & Startup entry | [📥 **Download Setup (.exe)**](https://github.com/pkgtm2419/p-downloader/releases/latest/download/P-Downloader-Setup.exe) |
| **P-Downloader-Portable.exe** | **Windows** (10/11 x64) | Zero-install standalone executable for USB drives / portable usage | [⚡ **Download Portable (.exe)**](https://github.com/pkgtm2419/p-downloader/releases/latest/download/P-Downloader-Portable.exe) |
| **P-Downloader-Windows-x64-Portable.zip** | **Windows** (x64) | Standalone portable folder with executable and all bundled libraries | [📦 **Download Archive (.zip)**](https://github.com/pkgtm2419/p-downloader/releases/latest/download/P-Downloader-Windows-x64-Portable.zip) |
| **P-Downloader-Linux-x64.tar.gz** | **Linux** (x64) | Standalone Linux portable package (tarball) | [🐧 **Download Linux (.tar.gz)**](https://github.com/pkgtm2419/p-downloader/releases/latest/download/P-Downloader-Linux-x64.tar.gz) |
| **pdownloader-browser-extension.zip** | **All Platforms** | Chrome, Edge, Brave, and Firefox WebExtension | [🌐 **Download Extension (.zip)**](https://github.com/pkgtm2419/p-downloader/releases/latest/download/pdownloader-browser-extension.zip) |
| **SHA256SUMS.txt** | **All Platforms** | Cryptographic verification checksums for every release file | [🔒 **Download Checksums**](https://github.com/pkgtm2419/p-downloader/releases/latest/download/SHA256SUMS.txt) |
---

## 📦 Complete Installation Guide (Every OS)

### 1. Windows Installation

#### Option A: Windows Setup Installer (Recommended)
1. Download **`P-Downloader-Setup-v1.0.3.exe`** from [GitHub Releases](https://github.com/pkgtm2419/p-downloader/releases/latest).
2. Run the installer wizard. If an existing version of P-Downloader is already present, the setup will automatically detect it and ask whether you want to seamlessly upgrade (preserving your history and settings) or perform a clean reinstall.
3. The installer automatically registers native messaging host integration for Chrome, Edge, Brave, Chromium, and Firefox.
4. Launch P-Downloader from your Start Menu or Desktop shortcut.

#### Option B: Portable Mode
1. Download **`P-Downloader-v1.0.3-Portable.exe`** or extract **`P-Downloader-v1.0.3-Windows-x64-Portable.zip`**.
2. Double-click `P-Downloader.exe` to run immediately without installation.

#### Option C: Run from Source
```powershell
# 1. Clone repository
git clone https://github.com/pkgtm2419/p-downloader.git
cd p-downloader

# 2. Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch app
python main.py
# Or double-click: run_pdownloader.bat
```

---

### 2. Linux Installation (Ubuntu, Debian, Fedora, Arch)

#### Option A: Standalone Binary Package
1. Download **`P-Downloader-v1.0.3-Linux-x64.tar.gz`** from [GitHub Releases](https://github.com/pkgtm2419/p-downloader/releases/latest).
2. Extract the archive:
   ```bash
   tar -xvf P-Downloader-v1.0.3-Linux-x64.tar.gz
   cd P-Downloader
   ./P-Downloader
   ```

#### Option B: Run from Source on Linux
1. **Install system dependencies**:
   - **Ubuntu / Debian / Linux Mint**:
     ```bash
     sudo apt update
     sudo apt install -y python3 python3-pip python3-venv libegl1 libgl1 libxkbcommon-x11-0 libdbus-1-3 ffmpeg
     ```
   - **Fedora / RHEL**:
     ```bash
     sudo dnf install -y python3 python3-pip mesa-libGL mesa-libEGL libxkbcommon-x11 ffmpeg
     ```
   - **Arch Linux / Manjaro**:
     ```bash
     sudo pacman -S python python-pip libxkbcommon xcb-util-cursor ffmpeg
     ```

2. **Clone and run**:
   ```bash
   git clone https://github.com/pkgtm2419/p-downloader.git
   cd p-downloader
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ./run_pdownloader.sh
   ```

3. **Install Linux Desktop Icon & Launcher** (Optional):
   ```bash
   chmod +x run_pdownloader.sh
   cp pdownloader.desktop ~/.local/share/applications/
   ```

---

### 3. macOS Installation

#### Option: Run from Source (macOS 12+ Monterey, Ventura, Sonoma, Sequoia)

1. **Install Python 3 and FFmpeg** (via Homebrew):
   ```bash
   # Install Homebrew if not already installed (https://brew.sh)
   brew install python@3.12 ffmpeg
   ```

2. **Clone and set up**:
   ```bash
   git clone https://github.com/pkgtm2419/p-downloader.git
   cd p-downloader
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Launch**:
   ```bash
   ./run_pdownloader.sh
   # Or directly:
   python3 main.py
   ```

---

## 🌐 Browser Extension Integration (Chrome, Edge, Brave, Firefox)

P-Downloader includes an official Manifest V3 browser extension and a native messaging host bridge for instant browser interception and in-page video sniffing.

### Step 1: Register Native Messaging Host
Run the automated registrar script:
- **Windows**:
  ```cmd
  python browser_extension\installer.py
  ```
- **Linux & macOS**:
  ```bash
  python3 browser_extension/installer.py
  ```
*This automatically registers `com.pdownloader.host` in your OS registry or browser manifest directories.*

### Step 2: Load the WebExtension in Your Browser
1. In your browser, open the extensions manager:
   - **Chrome / Brave**: `chrome://extensions`
   - **Microsoft Edge**: `edge://extensions`
   - **Firefox**: `about:debugging#/runtime/this-firefox`
2. Turn ON **Developer mode** (top-right toggle).
3. Click **Load unpacked** (or extract `pdownloader-browser-extension-v1.0.3.zip`).
4. Select the `browser_extension` folder.
5. You're ready! Right-click any downloadable link or click the floating video download pill on media pages.

---

## 💻 CLI (Headless Mode)

P-Downloader includes a headless command-line interface suitable for remote Linux servers, Docker containers, and automated cron pipelines:

```bash
# Basic high-speed download (8 connections)
python main.py --cli --url "https://example.com/archive.iso"

# Ultra multi-connection download (32 parallel connections to custom path)
python main.py --cli --url "https://example.com/dataset.zip" --connections 32 --output "/data/dataset.zip"

# Download a torrent or magnet link
python main.py --cli --url "magnet:?xt=urn:btih:..."

# Check version
python main.py --version
```

### Command-line Arguments
| Argument | Description | Default |
| :--- | :--- | :--- |
| `--url <URL>` | Download target URL / Magnet URI | `""` |
| `--connections <N>` | Number of concurrent connection segments (`1-32`) | `8` |
| `--output <PATH>` | Custom destination file path | Category default |
| `--cli` | Run in headless console mode without GUI | `False` |
| `--tray` / `--minimized`| Launch minimized directly into System Tray | `False` |
| `--version`, `-v` | Display application version and exit | - |

---

## 🔨 Building and Packaging

### 1. Windows PyInstaller & Inno Setup
```cmd
pip install -r requirements-dev.txt

# Directory distribution (used by installer)
python -m PyInstaller --clean -y pdownloader.spec

# Single-file portable executable
python -m PyInstaller --clean -y P-Downloader-Portable.spec

# Inno Setup Windows installer
build_installer.bat 1.0.1
```

### 2. Linux Standalone Bundle
```bash
pip install -r requirements-dev.txt
python3 -m PyInstaller --clean -y pdownloader.spec
tar -czvf P-Downloader-v1.0.3-Linux-x64.tar.gz -C dist P-Downloader
```

---

## 🤖 GitHub Actions Automated Releases

When a version tag is pushed (e.g. `v1.0.0`), the [`.github/workflows/release.yml`](.github/workflows/release.yml) workflow automatically:
1. Runs all 23 unit & integration test suites.
2. Compiles the Windows Setup `.exe`, portable `.exe`, and portable `.zip`.
3. Compiles the Linux standalone portable package `.tar.gz`.
4. Bundles the Chrome/Edge WebExtension `.zip`.
5. Computes SHA-256 hashes in `SHA256SUMS.txt`.
6. Publishes the release on GitHub with release notes.

To trigger a release manually:
1. Go to **Actions** → **Release** in your GitHub repository.
2. Click **Run workflow**, specify the version (e.g. `1.0.0`), and run.

---

## 🛡️ Security & Privacy

- **Clean-room Codebase**: Zero telemetry, tracking, or adware.
- **Local Storage Only**: All credentials and download logs stay on your local disk at `~/.pdownloader/downloads.db`.
- **Pre-flight CI Security**: Barred by `.gitignore` against accidental credential/environment leakage.

---

## 📄 License

This project is licensed under the [**MIT License**](LICENSE). Free for personal and commercial use.
