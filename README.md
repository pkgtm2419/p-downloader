# P-Downloader (Pure Downloader)

A high-performance, clean-room desktop download accelerator built from scratch with Python and PyQt6.

---

## Features

- **Dynamic Multi-Connection Slicing**: Splits downloads into up to 32 parallel connections using HTTP `Range` requests to saturate bandwidth.
- **Resilient Pause & Resume**: Saves transfer state in `.pdownload` metadata files; seamlessly resumes interrupted downloads.
- **Categorized Library**: Automatically organizes downloads into `Compressed`, `Programs`, `Video`, `Music`, `Documents`, and `General`.
- **Desktop UI**:
  - Classic toolbar with Add URL, Resume, Pause, Stop All, Delete, and Options.
  - Left navigation sidebar with Category and Status trees.
  - Downloads table with real-time progress bars, speeds, and ETA calculations.
  - Transfer dialog with a live per-segment multi-connection progress visualizer.
  - System Tray integration with minimization and completion notifications.
- **Chrome & Edge Browser Integration**:
  - Includes a WebExtension (Manifest V3) and Native Messaging Host (`com.pdownloader.host`).
  - Right-click context menu "Download with P-Downloader" and automatic download interception.
- **CLI Mode**: Full-featured headless command-line interface for automated or scripted downloads.

---

## Project Structure

```
d:\p-downloader\
├── core\
│   ├── categories.py       # Extension to category mapper & path resolution
│   ├── db.py               # SQLite state persistence
│   ├── engine.py           # Download task lifecycle manager & queue
│   └── segment.py          # Multi-segment concurrent worker & resume logic
├── gui\
│   ├── add_dialog.py       # "Add URL" dialog with auto-clipboard & detection
│   ├── download_dialog.py  # Transfer status window with live segment bars
│   ├── main_window.py      # Main dashboard window
│   ├── settings_dialog.py  # User preferences & connections configuration
│   └── styles.py           # Clean modern styles & formatting helpers
├── browser_extension\
│   ├── background.js       # WebExtension service worker
│   ├── installer.py        # Windows Registry Native Messaging registrar
│   ├── manifest.json       # Manifest V3 extension configuration
│   └── pdownloader_native_host.py # Native binary framing host
├── tests\
│   ├── test_engine.py      # Unit tests for categories, DB, and segments
│   └── test_resume.py      # End-to-end multi-connection pause/resume test
├── main.py                 # Application launcher (GUI & CLI modes)
└── run_pdownloader.bat     # Windows one-click desktop launcher
```

---

## How to Run

### 1. GUI Mode (Desktop App)
Double-click `run_pdownloader.bat` or run:
```bash
python main.py
```

### 2. CLI Mode (Headless Downloader)
```bash
python main.py --cli --url "https://example.com/largefile.zip" --connections 16 --output "C:\Downloads\file.zip"
```

### 3. Browser Extension Installation
1. Register the native host:
   ```bash
   python browser_extension\installer.py
   ```
2. Open Chrome or Edge and navigate to `chrome://extensions` or `edge://extensions`.
3. Enable **Developer mode**.
4. Click **Load unpacked** and select `d:\p-downloader\browser_extension`.
