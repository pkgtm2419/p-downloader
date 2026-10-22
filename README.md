<div align="center">

<img src="resources/logo.png" alt="P-Downloader Logo" width="128" height="128" />

# P-Downloader (Pure Downloader)

### Ultra High-Performance Desktop Download Accelerator & Bandwidth Manager
*A clean-room, open-source download accelerator built from scratch in Python and PyQt6.*

[![CI](https://github.com/p-downloader/p-downloader/actions/workflows/ci.yml/badge.svg)](https://github.com/p-downloader/p-downloader/actions/workflows/ci.yml)
[![Release](https://github.com/p-downloader/p-downloader/actions/workflows/release.yml/badge.svg)](https://github.com/p-downloader/p-downloader/actions/workflows/release.yml)
[![GitHub Release](https://img.shields.io/github/v/release/p-downloader/p-downloader?include_prereleases&style=flat-square&color=blue)](https://github.com/p-downloader/p-downloader/releases/latest)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue?style=flat-square&logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20x64-0078D6?style=flat-square&logo=windows)](https://github.com/p-downloader/p-downloader/releases)

[**Download Windows Installer**](https://github.com/p-downloader/p-downloader/releases/latest) •
[**Features**](#-features) •
[**Quick Start**](#-quick-start) •
[**Browser Integration**](#-browser-extension-integration) •
[**CLI Mode**](#-cli-headless-mode) •
[**Build from Source**](#-building-and-packaging) •
[**GitHub Actions CI/CD**](#-automated-release-workflow-github-actions)

</div>

---

## ⚡ Overview

**P-Downloader** is an open-source, full-featured desktop download manager and acceleration engine. Designed as a modern alternative to legacy download utilities like Internet Download Manager (IDM), P-Downloader saturates your internet connection through multi-connection chunking, automatic network interface bonding, dynamic pause/resume, and direct browser interception.

---

## ✨ Features

### 🚀 High-Speed Multi-Connection Acceleration
- **Dynamic Connection Slicing**: Splits files into up to **32 concurrent streams** using HTTP `Range` headers to bypass server-side single-connection throttling.
- **Sparse File Pre-allocation**: Instantly reserves file capacity on disk, reducing fragmentation and eliminating write latency.

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

### ⏱️ High-Precision Speed Limiter
- **Token-Bucket Throttling**: Restrict transfer speeds from 100 KB/s up to Gigabit capacity so background downloads never disrupt gaming, VoIP, or video streaming.

### 🖥️ Native Desktop Experience & System Tray
- **Modern Dark Interface**: Custom high-DPI desktop UI built with PyQt6.
- **Floating Drop Target**: Drag-and-drop links or text onto an on-screen desktop drop target widget.
- **Live Segment Visualizer**: Real-time progress bars showcasing individual download streams and network adapter allocations.
- **Single-Instance IPC**: Running background instances accept new downloads instantly from the command line or browser extension.
- **System Tray Execution**: Minimize to the Windows notification tray with completion balloon alerts.

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

## 📥 Downloads & Installation

You can get pre-compiled, virus-scanned binaries from the [**GitHub Releases**](https://github.com/p-downloader/p-downloader/releases/latest) page:

| Package | Description | Recommended For |
| :--- | :--- | :--- |
| **`P-Downloader-Setup-vX.Y.Z.exe`** | Standard Windows installer with desktop shortcut and start menu registration | General Windows users |
| **`P-Downloader-vX.Y.Z-Portable.exe`** | Single-file portable executable, zero installation required | USB drives / Portable usage |
| **`P-Downloader-vX.Y.Z-Windows-x64-Portable.zip`** | Standalone folder containing application and runtime assets | Portable environments |
| **`pdownloader-browser-extension-vX.Y.Z.zip`** | Chrome / Edge Manifest V3 extension | Browser integration |
| **`SHA256SUMS.txt`** | Cryptographic verification hashes for all release artifacts | Security verification |

---

## 🚀 Quick Start (Running from Source)

### Prerequisites
- **Python 3.10+** (Python 3.12 64-bit recommended)
- **Windows 10 / 11** (Linux supported for core engine & headless CLI)

### 1. Clone the Repository
```bash
git clone https://github.com/p-downloader/p-downloader.git
cd p-downloader
```

### 2. Create and Activate a Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Launch Application
- **Double-click** `run_pdownloader.bat` or run:
```bash
python main.py
```

---

## 🌐 Browser Extension Integration

P-Downloader includes an official Manifest V3 browser extension for **Google Chrome**, **Microsoft Edge**, **Brave**, and **Chromium-based** browsers.

### 1. Register the Windows Native Messaging Host
Run the automated registrar script from an elevated or user command prompt:
```bash
python browser_extension/installer.py
```
*This registers `com.pdownloader.host` in your Windows registry (`HKCU\Software\Google\Chrome\NativeMessagingHosts` and `HKCU\Software\Microsoft\Edge\NativeMessagingHosts`).*

### 2. Load the WebExtension in Your Browser
1. In your browser, navigate to:
   - Chrome / Brave: `chrome://extensions`
   - Microsoft Edge: `edge://extensions`
2. Enable **Developer Mode** (top-right toggle).
3. Click **Load unpacked**.
4. Select the `browser_extension` folder inside this repository (or extract `pdownloader-browser-extension-vX.Y.Z.zip`).
5. Right-click any downloadable link or file in your browser and choose **Download with P-Downloader**!

---

## 💻 CLI (Headless Mode)

P-Downloader includes a headless command-line interface suitable for scripts, remote servers, and automation:

```bash
# Basic high-speed download (8 connections)
python main.py --cli --url "https://example.com/archive.iso"

# Ultra multi-connection download (32 parallel connections to specified location)
python main.py --cli --url "https://example.com/dataset.zip" --connections 32 --output "D:\Datasets\dataset.zip"

# Check version
python main.py --version
```

### Command-line Arguments
| Argument | Description | Default |
| :--- | :--- | :--- |
| `--url <URL>` | Download target URL | `""` |
| `--connections <N>` | Number of concurrent connection segments (`1-32`) | `8` |
| `--output <PATH>` | Custom destination file path | Default category folder |
| `--cli` | Run in headless console mode without GUI | `False` |
| `--tray` / `--minimized`| Launch minimized directly into Windows System Tray | `False` |
| `--version`, `-v` | Display application version and exit | - |

---

## 📁 Project Structure

```
p-downloader/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                 # Continuous Integration test & build workflow
│   │   └── release.yml            # Automated GitHub Release & installer packaging
│   ├── ISSUE_TEMPLATE/            # Bug report & feature request templates
│   └── PULL_REQUEST_TEMPLATE.md   # Pull request review checklist
├── core/
│   ├── __init__.py                # Version declaration (__version__ = "1.0.0")
│   ├── categories.py              # Filetype categorization & download path resolution
│   ├── credentials_manager.py     # Domain-specific HTTP authentication store
│   ├── db.py                      # SQLite download queue persistence
│   ├── engine.py                  # Download engine lifecycle manager
│   ├── ipc.py                     # Single-instance cross-process communication
│   ├── network_binder.py          # Multi-adapter interface bandwidth bonding
│   ├── segment.py                 # Multi-segment HTTP Range engine & resume logic
│   ├── speed_limiter.py           # Token-bucket rate throttler
│   └── torrent.py                 # Bencode parser & Magnet URI resolver
├── gui/
│   ├── add_dialog.py              # "Add URL" dialog with automatic clipboard probe
│   ├── batch_dialog.py            # Batch URL import dialog
│   ├── download_dialog.py         # Live multi-stream transfer monitor
│   ├── drop_target.py             # Floating desktop drag-and-drop link target
│   ├── grabber_dialog.py          # Site grabber dialog
│   ├── main_window.py             # Main application dashboard
│   ├── refresh_dialog.py          # "Refresh Download Address" recovery dialog
│   ├── scheduler_dialog.py        # Task scheduler dialog
│   ├── settings_dialog.py         # User settings & network adapter manager
│   ├── site_logins_dialog.py      # HTTP authentication manager dialog
│   └── styles.py                  # High-DPI dark styles & metric formatters
├── browser_extension/
│   ├── background.js              # WebExtension service worker
│   ├── installer.py               # Windows Registry Native Messaging registrar
│   ├── manifest.json              # Manifest V3 extension configuration
│   └── pdownloader_native_host.py  # Native messaging stdin/stdout bridge
├── resources/                     # Icons, logos, and UI asset previews
├── tests/
│   ├── test_engine.py             # Unit tests for categories, DB, and segments
│   ├── test_resume.py             # In-process HTTP Range pause/resume integration test
│   └── test_ultra_downloader.py   # Unit tests for credentials, bonding, limiter, torrents
├── build_installer.bat            # Automated local build script (PyInstaller + Inno Setup)
├── installer.iss                  # Inno Setup 6 compiler configuration script
├── main.py                        # Main executable entry point (GUI + CLI)
├── pdownloader.spec               # PyInstaller directory distribution spec
├── P-Downloader-Portable.spec      # PyInstaller standalone single-file spec
├── requirements.txt               # Production dependencies
├── requirements-dev.txt           # Development & testing dependencies
├── run_pdownloader.bat            # Windows one-click desktop launcher
└── LICENSE                        # MIT License
```

---

## 🔨 Building and Packaging

### 1. Compile with PyInstaller
To build the standalone portable executable or folder bundle locally:
```bash
pip install -r requirements-dev.txt

# Option A: Directory distribution (used by installer)
python -m PyInstaller --clean -y pdownloader.spec

# Option B: Single-file portable executable
python -m PyInstaller --clean -y P-Downloader-Portable.spec
```
Outputs:
- `dist/P-Downloader/` (Portable application directory)
- `dist/P-Downloader-Portable.exe` (Single-file portable executable)

### 2. Compile Windows Setup Installer (Inno Setup)
Make sure [Inno Setup 6](https://jrsoftware.org/isdl.php) is installed, then run:
```bat
# Default build
build_installer.bat

# Or pass a custom version tag
build_installer.bat 1.0.0
```
Output:
- `Output\P-Downloader-Setup.exe`

---

## 🤖 Automated Release Workflow (GitHub Actions)

This repository includes a production-grade CI/CD pipeline powered by GitHub Actions:

### 1. Continuous Integration (`ci.yml`)
- Automatically runs on every push and pull request to `master` and `main`.
- Tests across **Python 3.10, 3.11, and 3.12** on both **Windows** and **Ubuntu**.
- Runs linting and static analysis with `flake8`.
- Executes 100% of unit and integration test suites.
- Performs a build verification dry run on Windows runners.

### 2. Automated Release & Installer Generation (`release.yml`)
Releases can be generated and published automatically in two ways:

#### A. By Git Tag (Recommended)
Tag your commit and push it to GitHub:
```bash
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

#### B. Via GitHub Actions Web UI (`workflow_dispatch`)
1. Go to the **Actions** tab on your GitHub repository.
2. Select the **Release** workflow from the left sidebar.
3. Click **Run workflow**, optionally specify a version (e.g. `1.0.0`), and click **Run**.

**What the Release Action Does Automatically:**
1. Checks out the code and sets up Python 3.12.
2. Runs the full test suite.
3. Installs Inno Setup via Chocolatey.
4. Compiles the PyInstaller directory distribution (`dist/P-Downloader`).
5. Compiles the PyInstaller standalone single-file binary (`dist/P-Downloader-Portable.exe`).
6. Injects the version number and compiles `Output\P-Downloader-Setup.exe`.
7. Bundles the portable directory into `P-Downloader-vX.Y.Z-Windows-x64-Portable.zip`.
8. Packages the Chrome/Edge WebExtension into `pdownloader-browser-extension-vX.Y.Z.zip`.
9. Calculates SHA-256 hashes and generates `SHA256SUMS.txt`.
10. Publishes a new GitHub Release with release notes and attaches all binary artifacts.

---

## 🛡️ Security & Privacy

- **Clean-room Codebase**: Zero proprietary, closed-source, or telemetry libraries.
- **Local Data Only**: All download records and credentials are stored strictly on your local machine in an SQLite database at `~/.pdownloader/downloads.db`.
- **Pre-flight CI Checks**: Secrets, environment files, `.pem` certificates, and sensitive credentials are barred by a comprehensive `.gitignore` configuration.

---

## 🤝 Contributing

Contributions are welcomed!
1. Fork this repository.
2. Create a feature branch (`git checkout -b feature/awesome-feature`).
3. Commit your changes (`git commit -m "Add awesome feature"`).
4. Run tests: `python -m unittest discover tests` to ensure everything passes.
5. Push to the branch (`git push origin feature/awesome-feature`).
6. Open a **Pull Request**.

---

## 📄 License

This project is licensed under the [**MIT License**](LICENSE). Free for personal and commercial use.
