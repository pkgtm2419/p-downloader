# Getting Started with P-Downloader

This guide walks you through setting up your local development environment to run and modify **P-Downloader** on Windows, Linux, or macOS.

---

## 1. Prerequisites

Before setting up P-Downloader, verify that your machine has the following installed:

| Requirement | Supported Versions | Notes |
| :--- | :--- | :--- |
| **Python** | 3.10, 3.11, 3.12 | Python 3.10 or higher is required. |
| **Git** | Latest | For cloning and version control. |
| **FFmpeg** | Optional (Recommended) | Required for merging 1080p/4K YouTube video and audio tracks, and HLS streams. |
| **C++ Build Tools** | Windows only | Standard Visual C++ runtime (usually present by default). |

### Installing FFmpeg (Recommended)
- **Windows**: Install via winget (`winget install Gyan.FFmpeg`) or Chocolatey (`choco install ffmpeg`). Ensure `ffmpeg.exe` is in your system `PATH`.
- **Linux (Ubuntu/Debian)**: `sudo apt update && sudo apt install ffmpeg`
- **macOS**: `brew install ffmpeg`

---

## 2. Setting Up the Virtual Environment

Always use an isolated virtual environment (`.venv`) to manage dependencies.

### Windows (PowerShell)
```powershell
# 1. Clone repository (if not already cloned)
git clone https://github.com/pkgtm2419/p-downloader.git
cd p-downloader

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 4. Verify python path points to .venv
Get-Command python | Select-Object -ExpandProperty Source
```

> [!NOTE]
> If PowerShell blocks script execution, run:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Linux & macOS (Bash/Zsh)
```bash
# 1. Clone repository
git clone https://github.com/pkgtm2419/p-downloader.git
cd p-downloader

# 2. Create virtual environment
python3 -m venv .venv

# 3. Activate virtual environment
source .venv/bin/activate

# 4. Verify python path
which python
```

---

## 3. Installing Dependencies

P-Downloader divides its dependencies into runtime and development groups.

### Production Dependencies (`requirements.txt`)
Includes PyQt6, Requests, aiohttp, Cryptography, and yt-dlp:
```bash
pip install -r requirements.txt
```

### Development Dependencies (`requirements-dev.txt`)
Includes pytest, flake8, and pyinstaller in addition to production dependencies:
```bash
pip install -r requirements-dev.txt
```

---

## 4. Launching the Application

### Option A: Desktop GUI Mode (Default)
Run `main.py` directly from the virtual environment:
```powershell
# Windows
.\.venv\Scripts\python.exe main.py

# Linux / macOS
python main.py
```
Alternatively, on Windows double-click `run_pdownloader.bat`, or on Linux/macOS run `./run_pdownloader.sh`.

### Option B: Headless CLI Mode
P-Downloader can run without a graphical desktop interface for automated scripts and servers:
```bash
# Download a file with 16 connections into current directory
python main.py --cli "https://example.com/large-archive.zip" --connections 16

# Specify output filename and destination
python main.py --cli "https://example.com/data.iso" --output "D:\Downloads\custom.iso" --connections 32

# Apply bandwidth throttling (e.g., 2 MB/s)
python main.py --cli "https://example.com/movie.mp4" --limit 2097152
```

---

## 5. Browser Extension Setup (Dev Mode)

To test browser interception and in-page video sniffing with Chrome, Edge, Brave, or Firefox:

1. **Register the Native Messaging Host**:
   Run the native host installer from your project root:
   ```bash
   python browser_extension/installer.py
   ```
   This registers the `com.pdownloader.native_host` manifest in the Windows Registry or the Linux/macOS browser manifest directories.

2. **Load Extension in Chromium Browsers**:
   - Open `chrome://extensions` (or `edge://extensions`, `brave://extensions`).
   - Enable **Developer mode** (toggle in top-right corner).
   - Click **Load unpacked**.
   - Select the `browser_extension/` directory from this repository.

3. **Load Extension in Firefox**:
   - Open `about:debugging#/runtime/this-firefox`.
   - Click **Load Temporary Add-on...**.
   - Select `browser_extension/manifest.firefox.json`.

---

## 6. Quick Smoke Test

Verify that everything is operational:

```powershell
# Run the unit test suite
python -m pytest tests/test_adaptive_concurrency.py tests/test_block_scheduler.py tests/test_retry_policy.py -v
```

All selected tests should pass cleanly!

