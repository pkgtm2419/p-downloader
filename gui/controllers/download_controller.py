"""
Download Controller (IM-07).
Encapsulates download engine orchestration, batch actions, and database filtering
for the P-Downloader user interface.
"""
import os
import subprocess
import sys
from typing import List, Dict, Any, Optional
from core.engine import DownloadEngine


class DownloadController:
    def __init__(self, engine: DownloadEngine):
        self.engine = engine

    def get_all_downloads(self) -> List[Dict[str, Any]]:
        """Retrieves all downloads from the database."""
        return self.engine.db.get_all_downloads()

    def filter_downloads(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Filters downloads by category, status, and search string."""
        items = self.get_all_downloads()
        filtered = []
        q = (search_query or "").strip().lower()

        for item in items:
            if category and category.lower() != "all":
                item_cat = (item.get("category") or "General").lower()
                if item_cat != category.lower():
                    continue

            if status and status.lower() != "all":
                item_st = (item.get("status") or "queued").lower()
                if item_st != status.lower():
                    continue

            if q:
                fn = (item.get("filename") or "").lower()
                url = (item.get("url") or "").lower()
                if q not in fn and q not in url:
                    continue

            filtered.append(item)

        return filtered

    def pause_download(self, task_id: str):
        """Pauses a single download."""
        self.engine.pause_download(task_id)

    def pause_multiple(self, task_ids: List[str]):
        """Pauses multiple downloads in batch."""
        for tid in task_ids:
            self.engine.pause_download(tid)

    def resume_download(self, task_id: str):
        """Resumes a single download."""
        self.engine.resume_download(task_id)

    def resume_multiple(self, task_ids: List[str]):
        """Resumes multiple downloads in batch."""
        for tid in task_ids:
            self.engine.resume_download(tid)

    def stop_download(self, task_id: str, delete_parts: bool = False):
        """Stops a download and optionally discards partial segments."""
        self.engine.stop_download(task_id, delete_parts)

    def stop_multiple(self, task_ids: List[str], delete_parts: bool = False):
        """Stops multiple downloads in batch."""
        for tid in task_ids:
            self.engine.stop_download(tid, delete_parts)

    def delete_download(self, task_id: str, delete_file: bool = False):
        """Deletes a download from database and optionally removes the downloaded file."""
        self.engine.delete_download(task_id, delete_file)

    def delete_multiple(self, task_ids: List[str], delete_files: bool = False):
        """Deletes multiple downloads in batch."""
        for tid in task_ids:
            self.engine.delete_download(tid, delete_files)

    def redownload(self, task_id: str):
        """Resets and restarts a download from beginning."""
        item = self.engine.db.get_download(task_id)
        if not item:
            return
        save_path = item.get("save_path", "")
        if save_path and os.path.exists(save_path):
            try:
                os.remove(save_path)
            except Exception:
                pass
        self.engine.resume_download(task_id)

    def open_file(self, task_id: str) -> bool:
        """Opens the completed downloaded file with system default handler."""
        item = self.engine.db.get_download(task_id)
        if not item:
            return False
        path = item.get("save_path", "")
        if path and os.path.exists(path):
            try:
                if sys.platform == "win32":
                    os.startfile(path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", path], check=False)
                else:
                    subprocess.run(["xdg-open", path], check=False)
                return True
            except Exception:
                return False
        return False

    def open_folder(self, task_id: str) -> bool:
        """Opens enclosing directory and highlights the downloaded file."""
        item = self.engine.db.get_download(task_id)
        if not item:
            return False
        path = item.get("save_path", "")
        if not path:
            return False
        folder = os.path.dirname(os.path.abspath(path))
        if os.path.exists(folder):
            try:
                if sys.platform == "win32":
                    subprocess.run(["explorer", f"/select,{os.path.abspath(path)}"], check=False)
                elif sys.platform == "darwin":
                    subprocess.run(["open", "-R", path], check=False)
                else:
                    subprocess.run(["xdg-open", folder], check=False)
                return True
            except Exception:
                return False
        return False
