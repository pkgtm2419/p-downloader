# Troubleshooting & FAQ

This document provides answers and recovery steps for common runtime and development issues encountered when working with **P-Downloader**.

---

## 1. Common Issues & Solutions

### Q: Download fails with HTTP 401, 403, or 410 (Expired URL)
**Cause**: Cloud file lockers (Google Drive, Dropbox, Rapidgator, MEGA) generate temporary pre-signed links that expire after a few hours or after an IP change.  
**Solution**:
1. Select the failed or paused download in the main window.
2. Click **Refresh Link** (or right-click -> *Refresh Download Address*).
3. The **Refresh Dialog** ([`gui/refresh_dialog.py`](file:///gui/refresh_dialog.py)) will open.
4. Generate a new download link in your web browser and paste it into the dialog.
5. P-Downloader verifies that the remote file size and ETag match the existing `.part` staging file, and resumes downloading immediately without losing progress.

---

### Q: Download gets stuck or slows down near 99%
**Cause**: One or two slow network streams are lagging behind while the rest have finished (the "straggler tail" problem).  
**Solution**:
- P-Downloader includes automatic **Hedged Tail Scheduling** ([`core/block_scheduler.py`](file:///core/block_scheduler.py)), which automatically duplicates pending blocks across idle streams.
- If you notice persistent slowdowns, check whether the server is throttling your IP address. You can temporarily reduce the connection count to 4 in *Settings* -> *Connection Limits*.

---

### Q: Browser extension reports "Cannot connect to P-Downloader Native Host"
**Cause**: The native messaging host manifest has not been registered in your operating system registry or user directory, or the path in the manifest is invalid.  
**Solution**:
1. Close all browser instances completely.
2. Open a terminal in the P-Downloader folder and run:
   ```powershell
   python browser_extension/installer.py
   ```
3. Verify that the output confirms successful registration for your installed browsers.
4. Reopen your browser and reload the extension.

---

### Q: High resolution YouTube video (1080p / 4K) lacks audio or fails to merge
**Cause**: YouTube delivers 1080p and 4K streams as separate video and audio tracks (DASH format). P-Downloader requires **FFmpeg** to merge these streams into a finished MP4 or MKV container.  
**Solution**:
1. Check if FFmpeg is installed by opening a terminal and running:
   ```bash
   ffmpeg -version
   ```
2. If FFmpeg is missing, install it:
   - **Windows**: `winget install Gyan.FFmpeg`
   - **Linux**: `sudo apt install ffmpeg`
   - **macOS**: `brew install ffmpeg`
3. Restart P-Downloader. The engine will automatically detect FFmpeg on your `PATH`.

---

### Q: Multi-Adapter Bonding is not increasing download speed
**Cause**: Socket source binding requires two or more physical network adapters (e.g., Ethernet + Wi-Fi) with independent external internet routes.  
**Solution**:
1. Verify both adapters are connected to separate internet gateways (e.g., home broadband via Ethernet and mobile hotspot via Wi-Fi). If both adapters connect to the same router, ISP bandwidth limits will remain unchanged.
2. In P-Downloader, open **Options** -> **Settings** -> **Network**.
3. Confirm that the detected adapters are selected and active.

---

### Q: Windows Defender flags PyInstaller executable as a false positive
**Cause**: PyInstaller-compiled single-file binaries are occasionally flagged by generic heuristic analysis engines because malware frequently uses packers.  
**Solution**:
- For local builds, add the `dist/` directory to Windows Defender's exclusion list.
- For production releases, signing the binary with an Authenticode code-signing certificate eliminates false positives.

---

## 2. Configuration & State File Locations

| File / Directory | Location (Windows) | Location (Linux / macOS) | Purpose |
| :--- | :--- | :--- | :--- |
| **SQLite Database** | `%APPDATA%\P-Downloader\downloads.db` | `~/.config/pdownloader/downloads.db` | Task queue, history, categories, and settings. |
| **Credentials Vault**| `%USERPROFILE%\.pdownloader\vault.key` | `~/.pdownloader/vault.key` | Fernet encryption key for saved site passwords. |
| **IPC Auth Token** | `%USERPROFILE%\.pdownloader\.ipc_token` | `~/.pdownloader/.ipc_token` | Session token protecting local IPC commands. |
| **Temporary Staging**| Destination folder + `.part` | Destination folder + `.part` | Byte-level staging container for in-progress files. |
| **Journal State** | Destination folder + `.pdownload` | Destination folder + `.pdownload` | Atomic JSON progress metadata and block states. |

