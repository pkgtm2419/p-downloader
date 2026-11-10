"""
Central Download Engine controlling queues, persistence, and task lifecycles.
"""
import os
import uuid
import threading
from typing import Dict, List, Optional, Callable, Any
from .db import DownloadDB
from .segment import DownloadTask, probe_url
from .categories import (
    get_category_for_filename,
    get_default_save_path,
    sanitize_filename,
    resolve_unique_filename,
    is_generic_route_name
)


class DownloadEngine:
    def __init__(self, db: Optional[DownloadDB] = None):
        self.db = db or DownloadDB()
        self.tasks: Dict[str, DownloadTask] = {}
        self.listeners: List[Callable[[DownloadTask], None]] = []

        # Reconcile any orphaned 'downloading' tasks on startup
        try:
            with self.db.conn:
                self.db.conn.execute("UPDATE downloads SET status = 'paused' WHERE status = 'downloading'")
        except Exception:
            pass

    def add_listener(self, callback: Callable[[DownloadTask], None]):
        self.listeners.append(callback)

    def _notify_listeners(self, task: DownloadTask):
        for cb in self.listeners:
            try:
                cb(task)
            except Exception:
                pass

    def create_from_request(
        self,
        request,
        auto_start: bool = True
    ) -> DownloadTask:
        from core.browser_context import headers_for_target
        hdrs = None
        if getattr(request, "context", None):
            try:
                hdrs = headers_for_target(request.context, request.url)
            except Exception:
                pass
        return self.create_download(
            url=request.url,
            filename=request.filename,
            save_path=request.destination,
            connections=request.connections or 8,
            auto_start=auto_start,
            headers=hdrs,
            context=getattr(request, "context", None)
        )

    def create_download(
        self,
        url: str,
        filename: Optional[str] = None,
        save_path: Optional[str] = None,
        category: Optional[str] = None,
        connections: int = 8,
        auto_start: bool = True,
        page_url: Optional[str] = None,
        quality: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        context: Optional[Any] = None
    ) -> DownloadTask:
        if context and not headers:
            try:
                from core.browser_context import headers_for_target
                headers = headers_for_target(context, url)
            except Exception:
                pass

        from core.extractor import is_media_url
        is_yt = is_media_url(url) or (page_url and is_media_url(page_url))

        # Check if filename is missing or a generic route name (like 'watch')
        needs_filename = not filename or is_generic_route_name(filename)
        if needs_filename or not save_path:
            info = None
            try:
                info = probe_url(page_url if (page_url and is_yt) else url)
                if needs_filename and info and info.get("filename"):
                    cand = info["filename"]
                    if not is_generic_route_name(cand):
                        filename = cand
                        needs_filename = False
            except Exception:
                pass

            if needs_filename:
                if is_yt:
                    is_audio = quality and "audio" in quality.lower()
                    filename = "YouTube_Audio.mp3" if is_audio else "YouTube_Video.mp4"
                else:
                    import urllib.parse
                    clean_part = urllib.parse.urlparse(url).path.rstrip("/").split("/")[-1].split("?")[0]
                    if clean_part and not is_generic_route_name(clean_part):
                        filename = clean_part
                    else:
                        filename = "download.bin"

        # Ensure correct extension for YouTube and media
        if is_yt:
            is_audio = (quality and "audio" in quality.lower()) or (save_path and save_path.lower().endswith((".mp3", ".m4a")))
            valid_exts = (".mp3", ".m4a") if is_audio else (".mp4", ".mkv", ".webm")
            if not any(filename.lower().endswith(ext) for ext in valid_exts):
                stem = os.path.splitext(filename)[0]
                filename = f"{stem}.mp3" if is_audio else f"{stem}.mp4"

        filename = sanitize_filename(filename)

        if not category:
            category = get_category_for_filename(filename)

        if not save_path:
            save_path = get_default_save_path(filename, category)

        # Prevent silent overwriting
        save_dir = os.path.dirname(save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            unique_name = resolve_unique_filename(save_dir, os.path.basename(save_path))
            save_path = os.path.join(save_dir, unique_name)
            filename = unique_name

        task_id = str(uuid.uuid4())[:8]

        # Automatic streaming media routing (YouTube, Vimeo, Reddit, X, TikTok, Twitch, etc.)
        if is_yt:
            from core.extractor import UniversalMediaTask
            task = UniversalMediaTask(
                task_id=task_id,
                url=url,
                save_path=save_path,
                page_url=page_url,
                quality=quality,
                connections=connections,
                headers=headers,
                on_progress=self._on_task_progress,
                on_complete=self._on_task_complete,
                on_error=self._on_task_error
            )
        # Automatic HLS / M3U8 routing
        elif ".m3u8" in url.lower() or (filename and filename.lower().endswith(".m3u8")):
            from core.hls_downloader import HLSDownloadTask
            if save_path.lower().endswith(".m3u8"):
                save_path = save_path[:-5] + ".mp4"
            if filename.lower().endswith(".m3u8"):
                filename = filename[:-5] + ".mp4"

            task = HLSDownloadTask(
                task_id=task_id,
                url=url,
                save_path=save_path,
                connections=connections,
                headers=headers,
                on_progress=self._on_task_progress,
                on_complete=self._on_task_complete,
                on_error=self._on_task_error
            )
        # Automatic FTP / FTPS routing
        elif url.lower().startswith(("ftp://", "ftps://")):
            from core.ftp_downloader import FTPDownloadTask
            task = FTPDownloadTask(
                task_id=task_id,
                url=url,
                save_path=save_path,
                connections=1,
                headers=headers,
                on_progress=self._on_task_progress,
                on_complete=self._on_task_complete,
                on_error=self._on_task_error
            )
        # Automatic BitTorrent / Magnet routing
        elif url.lower().startswith("magnet:?") or (filename and filename.lower().endswith(".torrent")) or url.lower().endswith(".torrent"):
            from core.torrent import TorrentDownloadTask
            task = TorrentDownloadTask(
                task_id=task_id,
                url=url,
                save_path=save_path,
                connections=connections,
                on_progress=self._on_task_progress,
                on_complete=self._on_task_complete,
                on_error=self._on_task_error
            )
        else:
            task = DownloadTask(
                task_id=task_id,
                url=url,
                save_path=save_path,
                connections=connections,
                headers=headers,
                on_progress=self._on_task_progress,
                on_complete=self._on_task_complete,
                on_error=self._on_task_error
            )

        task.prepare()

        import json
        is_ftp = url.lower().startswith(("ftp://", "ftps://"))
        is_torrent = url.lower().startswith("magnet:?") or (filename and filename.lower().endswith(".torrent")) or url.lower().endswith(".torrent")
        kind = "youtube" if is_yt else ("hls" if (".m3u8" in url.lower() or (filename and filename.lower().endswith(".m3u8"))) else ("ftp" if is_ftp else ("torrent" if is_torrent else "http")))

        # Save to database
        self.db.add_download({
            "id": task_id,
            "url": url,
            "filename": filename,
            "save_path": save_path,
            "total_bytes": task.total_bytes,
            "downloaded_bytes": task.downloaded_bytes,
            "status": "downloading" if auto_start else "queued",
            "category": category or get_category_for_filename(filename),
            "connections": connections,
            "supports_range": task.supports_range,
            "kind": kind,
            "headers_json": json.dumps(headers) if headers else None
        })

        self.tasks[task_id] = task

        if auto_start:
            task.start()

        self._notify_listeners(task)
        return task

    def pause_download(self, task_id: str):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.pause()
            self.db.update_status(task_id, "paused", task.downloaded_bytes)
            self._notify_listeners(task)

    def resume_download(self, task_id: str):
        task = self.tasks.get(task_id)
        if not task:
            row = self.db.get_download(task_id)
            if not row:
                return
            import json
            hdrs = None
            if row.get("headers_json"):
                try:
                    hdrs = json.loads(row["headers_json"])
                except Exception:
                    pass

            from core.extractor import is_media_url, UniversalMediaTask
            kind = row.get("kind", "")
            if kind in ("youtube", "media") or is_media_url(row["url"]):
                task = UniversalMediaTask(
                    task_id=task_id,
                    url=row["url"],
                    save_path=row["save_path"],
                    connections=row.get("connections", 8),
                    headers=hdrs,
                    on_progress=self._on_task_progress,
                    on_complete=self._on_task_complete,
                    on_error=self._on_task_error
                )
            elif kind == "hls" or ".m3u8" in row["url"].lower():
                from core.hls_downloader import HLSDownloadTask
                task = HLSDownloadTask(
                    task_id=task_id,
                    url=row["url"],
                    save_path=row["save_path"],
                    connections=row.get("connections", 8),
                    headers=hdrs,
                    on_progress=self._on_task_progress,
                    on_complete=self._on_task_complete,
                    on_error=self._on_task_error
                )
            elif kind == "ftp" or row["url"].lower().startswith(("ftp://", "ftps://")):
                from core.ftp_downloader import FTPDownloadTask
                task = FTPDownloadTask(
                    task_id=task_id,
                    url=row["url"],
                    save_path=row["save_path"],
                    connections=1,
                    headers=hdrs,
                    on_progress=self._on_task_progress,
                    on_complete=self._on_task_complete,
                    on_error=self._on_task_error
                )
            elif kind == "torrent" or row["url"].lower().startswith("magnet:?") or row["url"].lower().endswith(".torrent"):
                from core.torrent import TorrentDownloadTask
                task = TorrentDownloadTask(
                    task_id=task_id,
                    url=row["url"],
                    save_path=row["save_path"],
                    connections=row.get("connections", 50),
                    on_progress=self._on_task_progress,
                    on_complete=self._on_task_complete,
                    on_error=self._on_task_error
                )
            else:
                task = DownloadTask(
                    task_id=task_id,
                    url=row["url"],
                    save_path=row["save_path"],
                    connections=row.get("connections", 8),
                    headers=hdrs,
                    on_progress=self._on_task_progress,
                    on_complete=self._on_task_complete,
                    on_error=self._on_task_error
                )
            task.prepare()
            self.tasks[task_id] = task

        task.start()
        self.db.update_status(task_id, "downloading")
        self._notify_listeners(task)

    def stop_download(self, task_id: str, delete_file: bool = False):
        task = self.tasks.get(task_id)
        if task:
            task.cancel()
        row = self.db.get_download(task_id)
        save_path = row["save_path"] if row else None
        self.db.delete_download(task_id)
        self.tasks.pop(task_id, None)

        if delete_file and save_path and os.path.exists(save_path):
            try:
                os.remove(save_path)
            except Exception:
                pass

        if task:
            task.status = "cancelled"
            self._notify_listeners(task)

    def pause_all(self):
        for task in list(self.tasks.values()):
            if task.status == "downloading":
                self.pause_download(task.task_id)

    def resume_all(self):
        for task in list(self.tasks.values()):
            if task.status == "paused":
                self.resume_download(task.task_id)
        for row in self.db.get_all_downloads():
            if row["status"] in ("paused", "queued") and row["id"] not in self.tasks:
                self.resume_download(row["id"])

    def refresh_download(self, task_id: str, new_url: str, resume_now: bool = True) -> bool:
        self.db.update_url(task_id, new_url)
        task = self.tasks.get(task_id)
        if task:
            task.refresh_url(new_url)
        else:
            row = self.db.get_download(task_id)
            if row:
                task = DownloadTask(
                    task_id=task_id,
                    url=new_url,
                    save_path=row["save_path"],
                    connections=row.get("connections", 8),
                    on_progress=self._on_task_progress,
                    on_complete=self._on_task_complete,
                    on_error=self._on_task_error
                )
                task.prepare()
                self.tasks[task_id] = task

        if resume_now and task:
            task.start()
            self.db.update_status(task_id, "downloading")

        if task:
            self._notify_listeners(task)
        return True

    def set_speed_limit(self, limit_bytes_per_sec: int):
        for task in self.tasks.values():
            task.set_speed_limit(limit_bytes_per_sec)

    def _on_task_progress(self, task: DownloadTask):
        self._notify_listeners(task)

    def _on_task_complete(self, task: DownloadTask):
        self.db.update_status(task.task_id, "completed", task.total_bytes)
        self._notify_listeners(task)

        if self.db.get_setting("antivirus_enabled", "1") == "1":
            def scan_worker():
                try:
                    from core.antivirus import AntivirusScanner
                    custom_av = self.db.get_setting("antivirus_path", "")
                    clean, msg = AntivirusScanner.scan_file(task.save_path, custom_av)
                    if not clean:
                        self.db.update_status(task.task_id, "error", task.total_bytes, f"Security Alert: {msg}")
                        self._notify_listeners(task)
                except Exception:
                    pass
            threading.Thread(target=scan_worker, daemon=True).start()

    def _on_task_error(self, task: DownloadTask, error_msg: str):
        self.db.update_status(task.task_id, "error", task.downloaded_bytes, error_msg)
        self._notify_listeners(task)
