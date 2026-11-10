"""
SQLite database management for P-Downloader task persistence.
Thread-safe with re-entrant locking and safe directory fallbacks.
"""
import os
import sqlite3
import threading
from typing import List, Dict, Optional, Any
from pathlib import Path

def get_default_db_path() -> str:
    try:
        p = Path.home() / ".pdownloader"
        p.mkdir(parents=True, exist_ok=True)
        return str(p / "downloads.db")
    except Exception:
        local_dir = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data")))
        try:
            local_dir.mkdir(parents=True, exist_ok=True)
            return str(local_dir / "downloads.db")
        except Exception:
            return ":memory:"

DB_PATH = get_default_db_path()

def init_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    if not db_path:
        db_path = get_default_db_path()
    try:
        if db_path != ":memory:":
            dir_name = os.path.dirname(db_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
        conn = sqlite3.connect(db_path, check_same_thread=False)
    except Exception:
        conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                filename TEXT NOT NULL,
                save_path TEXT NOT NULL,
                total_bytes INTEGER DEFAULT 0,
                downloaded_bytes INTEGER DEFAULT 0,
                status TEXT DEFAULT 'queued',
                category TEXT DEFAULT 'General',
                connections INTEGER DEFAULT 8,
                supports_range INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transfer_journals (
                task_id TEXT PRIMARY KEY,
                staging_path TEXT NOT NULL,
                journal_json TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(downloads)")
        cols = [r[1] for r in cursor.fetchall()]
        if "kind" not in cols:
            conn.execute("ALTER TABLE downloads ADD COLUMN kind TEXT DEFAULT 'http'")
        if "headers_json" not in cols:
            conn.execute("ALTER TABLE downloads ADD COLUMN headers_json TEXT")
    return conn

class DownloadDB:
    def __init__(self, db_path: Optional[str] = None):
        self._lock = threading.RLock()
        self.db_path = db_path or get_default_db_path()
        self.conn = init_db(self.db_path)

    def get_proxy_url(self) -> Optional[str]:
        """Returns the configured proxy URL (e.g. http://127.0.0.1:8080 or socks5://...) or None."""
        if self.get_setting("use_proxy", "0") != "1":
            return None
        proto = self.get_setting("proxy_proto", "HTTP").lower()
        host = self.get_setting("proxy_host", "").strip()
        port = self.get_setting("proxy_port", "8080").strip()
        if not host:
            return None
        return f"{proto}://{host}:{port}"

    def get_proxy_config(self) -> Optional[Dict[str, str]]:
        """Returns requests-compatible proxies dict or None if proxy is disabled."""
        url = self.get_proxy_url()
        if not url:
            return None
        return {
            "http": url,
            "https": url
        }

    def add_download(self, item: Dict[str, Any]):
        with self._lock:
            try:
                with self.conn:
                    self.conn.execute("""
                        INSERT OR REPLACE INTO downloads (
                            id, url, filename, save_path, total_bytes, downloaded_bytes,
                            status, category, connections, supports_range, created_at, error_message,
                            kind, headers_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?)
                    """, (
                        item["id"], item["url"], item["filename"], item["save_path"],
                        item.get("total_bytes", 0), item.get("downloaded_bytes", 0),
                        item.get("status", "queued"), item.get("category", "General"),
                        item.get("connections", 8), 1 if item.get("supports_range", True) else 0,
                        item.get("error_message", None),
                        item.get("kind", "http"),
                        item.get("headers_json", None)
                    ))
            except Exception:
                pass

    def update_status(self, download_id: str, status: str, downloaded_bytes: Optional[int] = None, error: Optional[str] = None):
        with self._lock:
            try:
                with self.conn:
                    if downloaded_bytes is not None:
                        self.conn.execute("""
                            UPDATE downloads 
                            SET status = ?, downloaded_bytes = ?, error_message = ?
                            WHERE id = ?
                        """, (status, downloaded_bytes, error, download_id))
                    else:
                        self.conn.execute("""
                            UPDATE downloads 
                            SET status = ?, error_message = ?
                            WHERE id = ?
                        """, (status, error, download_id))
                    
                    if status == "completed":
                        self.conn.execute("""
                            UPDATE downloads SET completed_at = datetime('now') WHERE id = ?
                        """, (download_id,))
            except Exception:
                pass

    def update_url(self, download_id: str, new_url: str):
        with self._lock:
            try:
                with self.conn:
                    self.conn.execute("""
                        UPDATE downloads 
                        SET url = ?, error_message = NULL, status = 'paused'
                        WHERE id = ?
                    """, (new_url, download_id))
            except Exception:
                pass

    def get_all_downloads(self) -> List[Dict[str, Any]]:
        with self._lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT * FROM downloads ORDER BY created_at DESC")
                return [dict(row) for row in cursor.fetchall()]
            except Exception:
                return []

    def get_download(self, download_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT * FROM downloads WHERE id = ?", (download_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
            except Exception:
                return None

    def delete_download(self, download_id: str):
        with self._lock:
            try:
                with self.conn:
                    self.conn.execute("DELETE FROM downloads WHERE id = ?", (download_id,))
            except Exception:
                pass

    def close(self):
        with self._lock:
            try:
                self.conn.close()
            except Exception:
                pass

    def get_setting(self, key: str, default: str = "") -> str:
        with self._lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row["value"] if row else default
            except Exception:
                return default

    def set_setting(self, key: str, value: str):
        with self._lock:
            try:
                with self.conn:
                    self.conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
            except Exception:
                pass
