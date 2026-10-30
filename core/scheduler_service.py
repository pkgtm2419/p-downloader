"""
Scheduler and Queue Automation Service for P-Downloader.
Controls time-based queue starts and stops, simultaneous download limits,
and automatic Windows power management (Sleep, Shutdown, VPN disconnect) upon queue completion.
"""
import sys
import os
import time
import ctypes
import threading
import subprocess
from datetime import datetime
from typing import Optional, Callable, Dict, Any

class SchedulerService:
    def __init__(self, engine, on_exit_requested: Optional[Callable[[], None]] = None):
        self.engine = engine
        self.on_exit_requested = on_exit_requested
        self.running = False
        self._thread: Optional[threading.Thread] = None

        self._last_started_date: Optional[str] = None
        self._last_stopped_date: Optional[str] = None
        self._completion_handled = False
        self._had_active_downloads = False

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="SchedulerServiceThread")
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _run_loop(self):
        while self.running:
            try:
                self._check_schedule()
                self._manage_concurrency()
                self._check_completion()
            except Exception:
                pass
            time.sleep(1.0)

    def _check_schedule(self):
        db = self.engine.db
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        current_time_str = now.strftime("%H:%M:%S")

        # 1. Start Schedule Check
        start_enabled = db.get_setting("sched_start_enabled", "0") == "1"
        start_time = db.get_setting("sched_start_time", "02:00:00")
        if start_enabled and self._last_started_date != today_str:
            if self._time_matches(current_time_str, start_time):
                self._last_started_date = today_str
                self._completion_handled = False
                self.engine.resume_all()

        # 2. Stop Schedule Check
        stop_enabled = db.get_setting("sched_stop_enabled", "0") == "1"
        stop_time = db.get_setting("sched_stop_time", "07:00:00")
        if stop_enabled and self._last_stopped_date != today_str:
            if self._time_matches(current_time_str, stop_time):
                self._last_stopped_date = today_str
                self.engine.pause_all()

    def _time_matches(self, current_time: str, target_time: str) -> bool:
        """Compares HH:MM:SS or HH:MM."""
        curr_parts = [int(p) for p in current_time.split(":")[:2]]
        target_parts = [int(p) for p in target_time.split(":")[:2]]
        return curr_parts == target_parts

    def _manage_concurrency(self):
        """
        Enforces simultaneous download limits across the active queue.
        Only picks up tasks that are QUEUED waiting for an available slot.
        Paused tasks are never automatically resumed.
        """
        db = self.engine.db
        try:
            max_simultaneous = int(db.get_setting("simultaneous_downloads", "2"))
        except (ValueError, TypeError):
            max_simultaneous = 2

        active_tasks = [t for t in self.engine.tasks.values() if t.status == "downloading"]
        if active_tasks:
            self._had_active_downloads = True

        if len(active_tasks) < max_simultaneous:
            # Only start tasks that are queued waiting for a slot.
            # Never automatically resume tasks that were paused by the user.
            queued_tasks = [t for t in self.engine.tasks.values() if t.status == "queued"]
            slots_available = max_simultaneous - len(active_tasks)
            for t in queued_tasks[:slots_available]:
                self.engine.resume_download(t.task_id)

    def _check_completion(self):
        """
        Executes configured completion actions (Sleep, Shutdown, Exit)
        when all active tasks are completed.
        """
        db = self.engine.db
        active_count = sum(1 for t in self.engine.tasks.values() if t.status == "downloading")

        if active_count > 0:
            self._completion_handled = False
            return

        if self._had_active_downloads and not self._completion_handled and active_count == 0:
            # Check if all tasks in memory are completed
            all_done = all(t.status in ("completed", "error") for t in self.engine.tasks.values())
            if all_done and len(self.engine.tasks) > 0:
                self._completion_handled = True
                self._execute_completion_actions()

    def _execute_completion_actions(self):
        db = self.engine.db

        # 1. Disconnect Internet / VPN
        if db.get_setting("sched_action_hangup", "0") == "1":
            try:
                subprocess.Popen(["rasdial", "/disconnect"], **({"creationflags": 0x08000000} if sys.platform == "win32" else {}))
            except Exception:
                pass

        # 2. Put Computer to Sleep
        if db.get_setting("sched_action_sleep", "0") == "1":
            try:
                if sys.platform == "win32":
                    ctypes.windll.PowrProf.SetSuspendState(0, 1, 0)
            except Exception:
                pass

        # 3. Shutdown Computer
        if db.get_setting("sched_action_shutdown", "0") == "1":
            try:
                if sys.platform == "win32":
                    subprocess.Popen(
                        ["shutdown.exe", "/s", "/t", "60", "/c", "P-Downloader queue completed."],
                        **({"creationflags": 0x08000000} if sys.platform == "win32" else {})
                    )
            except Exception:
                pass

        # 4. Exit Application
        if db.get_setting("sched_action_exit", "0") == "1":
            if self.on_exit_requested:
                self.on_exit_requested()
            else:
                sys.exit(0)
