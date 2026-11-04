# GUI Architecture & Frontend Design

This document details the graphical user interface (GUI) architecture of **P-Downloader**, built with **PyQt6**.

---

## 1. GUI Hierarchy & Layout

The user interface follows a modern, dark-themed, desktop-native layout modeled for maximum clarity and high-DPI crispness.

```
┌────────────────────────────────────────────────────────────────────────┐
│  Top Menu Bar (File, View, Downloads, Queue, Options, Help)            │
├────────────────────────────────────────────────────────────────────────┤
│  Main Toolbar (Add URL, Resume, Pause, Stop, Delete, Settings, Schedule)│
├───────────────┬────────────────────────────────────────────────────────┤
│ Categories    │ Downloads Table View (QTableWidget / QTreeView)        │
│ Sidebar       │ ┌────────────────────────────────────────────────────┐ │
│               │ │ Filename │ Size │ Status │ Progress │ Speed │ ETA  │ │
│ - All (42)    │ ├────────────────────────────────────────────────────┤ │
│ - Compressed  │ │ archive  │ 2 GB │ 78.4%  │ [████░]  │ 14MB/s│ 25s  │ │
│ - Documents   │ │ data.iso │ 4 GB │ Paused │ [██░░░]  │ 0 KB/s│ --   │ │
│ - Music       │ └────────────────────────────────────────────────────┘ │
│ - Programs    ├────────────────────────────────────────────────────────┤
│ - Video       │ Segment Visualizer & Speed Graph                       │
│ - Finished    │ [Segment 1 ████] [Segment 2 ██░░] [Segment 3 ████]     │
└───────────────┴────────────────────────────────────────────────────────┘
│  Status Bar (Global Speed: 14.2 MB/s | Active: 2 | System Tray Ready)  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Event-Driven Reactive Architecture

PyQt6 widgets execute exclusively on the GUI main thread. To display real-time updates (download speeds, byte counts, dynamic progress bars) without blocking UI rendering or causing lag:

1. **Decoupled Engine Signals**:
   `DownloadEngine` inherits from `QObject` and defines typed Qt signals (`task_progress`, `task_started`, `task_completed`, `task_failed`).
2. **Batching UI Repaints**:
   Progress signals are throttled at the worker level to ~10-20 Hz (every 50-100 ms). Flooding the Qt event loop with thousands of repaints per second would cause CPU spikes; periodic updates maintain silky-smooth 60 FPS scrolling and interactions.
3. **Model/View Table Updates**:
   When rows update, only the specific modified cell widgets (`QTableWidgetItem` / `QProgressBar`) receive updates rather than re-rendering the entire table.

---

## 3. Custom High-DPI Styling (`gui/styles.py`)

All styling is consolidated into [`gui/styles.py`](file:///gui/styles.py) utilizing Qt Style Sheets (QSS) with an IDM-grade dark visual palette:

- **Background Colors**: Deep navy/slate tones (`#121820`, `#1a2230`, `#222d3d`).
- **Accent & Primary**: Vibrant electric cyan/blue (`#00a8ff`, `#0078d4`).
- **Status Colors**:
  - Downloading: Emerald Green (`#00e676`)
  - Paused: Amber Orange (`#ff9100`)
  - Failed / Error: Crimson Red (`#ff1744`)
  - Queued: Light Slate (`#90a4ae`)

High-DPI scaling is enabled at startup before instantiating `QApplication`:
```python
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
```

---

## 4. Segment Progress Visualizer

One of P-Downloader's standout visual capabilities is the **Multi-Segment Visualizer** displayed in [`gui/download_dialog.py`](file:///gui/download_dialog.py):

- **Visual Striping**: Renders a custom-painted progress bar representing the entire file range (byte `0` to byte `N`).
- **Dynamic Slice Filling**: As individual range workers claim blocks and write data, their sub-ranges are rendered in real time.
- **Worker Allocation**: Displays which network adapter (Wi-Fi, Ethernet) or thread is currently driving each segment.

---

## 5. Modal Dialogs & Workflows

| Dialog Module | Purpose & Trigger | Key Features |
| :--- | :--- | :--- |
| [`gui/add_dialog.py`](file:///gui/add_dialog.py) | **Add Download URL** (Toolbar or Ctrl+N) | Auto-reads clipboard for URLs; detects file categories; allows setting connection count, target folder, and referrer headers. |
| [`gui/download_dialog.py`](file:///gui/download_dialog.py) | **Active Download Progress** | Displays real-time speed curve, segment visualizer, ETA, transferred byte counters, Pause/Resume, and speed limiters. |
| [`gui/batch_dialog.py`](file:///gui/batch_dialog.py) | **Batch Import** | Accepts multi-line URL lists or patterned wildcard URLs (`image[001-100].jpg`) to enqueue bulk items in one click. |
| [`gui/grabber_dialog.py`](file:///gui/grabber_dialog.py) | **Web Site Grabber** | Recursively crawls web domains using [`core/spider.py`](file:///core/spider.py) to download all images, documents, or media files. |
| [`gui/refresh_dialog.py`](file:///gui/refresh_dialog.py) | **Refresh Expired Link** (401/403/410) | Allows user to paste a refreshed pre-signed URL without losing existing partial `.part` download progress. |
| [`gui/site_logins_dialog.py`](file:///gui/site_logins_dialog.py) | **Site Logins Vault** | Manages encrypted domain credentials and HTTP Bearer tokens injected automatically on matching hostnames. |
| [`gui/scheduler_dialog.py`](file:///gui/scheduler_dialog.py) | **Queue Scheduler** | Configures timed queues, start/stop hours, speed limits during peak times, and auto-shutdown actions upon queue finish. |
| [`gui/settings_dialog.py`](file:///gui/settings_dialog.py) | **Global Preferences** | Network adapter bonding selection, global speed limits, antivirus scanner path, default save paths, and file associations. |
| [`gui/video_quality_dialog.py`](file:///gui/video_quality_dialog.py) | **Video Stream Selector** | Displays parsed YouTube/HLS video streams, bitrates, audio formats, and resolution options (4K, 1080p, 720p, MP3). |

---

## 6. System Tray & Background Notifications

When minimized or closed with "Minimize to Tray" enabled:
- Hides the main taskbar icon and parks an icon in the Windows/Linux/macOS system tray.
- Right-clicking the tray icon surfaces quick controls: *Pause All, Resume All, Add URL, Speed Limiter presets, Exit*.
- Emits native OS toast notifications upon download completions or critical errors.

