"""
Central Download Engine controlling queues, persistence, and task lifecycles.
"""
import uuid
from typing import Dict, List, Optional, Callable
from .db import DownloadDB
from .segment import DownloadTask, probe_url
from .categories import get_category_for_filename, get_default_save_path

class DownloadEngine:
    def __init__(self, db: Optional[DownloadDB] = None):
        self.db = db or DownloadDB()
        self.tasks: Dict[str, DownloadTask] = {}
        self.listeners: List[Callable[[DownloadTask], None]] = []

    def add_listener(self, callback: Callable[[DownloadTask], None]):
        self.listeners.append(callback)

    def _notify_listeners(self, task: DownloadTask):
        for cb in self.listeners:
            try:
                cb(task)
            except Exception:
                pass

    def create_download(
        self,
        url: str,
        filename: Optional[str] = None,
        save_path: Optional[str] = None,
        category: Optional[str] = None,
        connections: int = 8,
        auto_start: bool = True
    ) -> DownloadTask:
        # Probe metadata if filename/save_path not specified
        if not filename or not save_path:
            info = probe_url(url)
            if not filename:
                filename = info["filename"]
            if not category:
                category = get_category_for_filename(filename)
            if not save_path:
                save_path = get_default_save_path(filename, category)

        task_id = str(uuid.uuid4())[:8]

        task = DownloadTask(
            task_id=task_id,
            url=url,
            save_path=save_path,
            connections=connections,
            on_progress=self._on_task_progress,
            on_complete=self._on_task_complete,
            on_error=self._on_task_error
        )
        task.prepare()

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
            "supports_range": task.supports_range
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
            # Reconstruct task from DB
            row = self.db.get_download(task_id)
            if not row:
                return
            task = DownloadTask(
                task_id=task_id,
                url=row["url"],
                save_path=row["save_path"],
                connections=row.get("connections", 8),
                on_progress=self._on_task_progress,
                on_complete=self._on_task_complete,
                on_error=self._on_task_error
            )
            task.prepare()
            self.tasks[task_id] = task

        task.start()
        self.db.update_status(task_id, "downloading")
        self._notify_listeners(task)

    def delete_download(self, task_id: str, delete_file: bool = False):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.cancel()
            del self.tasks[task_id]
        
        row = self.db.get_download(task_id)
        if row and delete_file:
            import os
            if os.path.exists(row["save_path"]):
                try:
                    os.remove(row["save_path"])
                except Exception:
                    pass

        self.db.delete_download(task_id)

    def pause_all(self):
        for task in list(self.tasks.values()):
            if task.status == "downloading":
                self.pause_download(task.task_id)

    def resume_all(self):
        # Resume active tasks
        for task in list(self.tasks.values()):
            if task.status == "paused":
                self.resume_download(task.task_id)
        # Check DB for queued or paused
        for row in self.db.get_all_downloads():
            if row["status"] in ("paused", "queued") and row["id"] not in self.tasks:
                self.resume_download(row["id"])

    def refresh_download(self, task_id: str, new_url: str, resume_now: bool = True) -> bool:
        """
        Updates the URL of an expired or existing task, updates SQLite DB and metadata,
        and seamlessly resumes download from exact previous offsets.
        """
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
        """
        Applies a speed limit across all active tasks.
        """
        for task in self.tasks.values():
            task.set_speed_limit(limit_bytes_per_sec)

    def _on_task_progress(self, task: DownloadTask):
        self._notify_listeners(task)

    def _on_task_complete(self, task: DownloadTask):
        self.db.update_status(task.task_id, "completed", task.total_bytes)
        self._notify_listeners(task)

    def _on_task_error(self, task: DownloadTask, error_msg: str):
        self.db.update_status(task.task_id, "error", task.downloaded_bytes, error_msg)
        self._notify_listeners(task)
