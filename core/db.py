"""
SQLite database management for P-Downloader task persistence.
"""
import os
import sqlite3
from typing import List, Dict, Optional, Any
from pathlib import Path

DB_PATH = os.path.join(str(Path.home() / ".pdownloader"), "downloads.db")

def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    dir_name = os.path.dirname(db_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
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
    return conn

class DownloadDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = init_db(db_path)

    def add_download(self, item: Dict[str, Any]):
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO downloads (
                    id, url, filename, save_path, total_bytes, downloaded_bytes,
                    status, category, connections, supports_range, created_at, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
            """, (
                item["id"], item["url"], item["filename"], item["save_path"],
                item.get("total_bytes", 0), item.get("downloaded_bytes", 0),
                item.get("status", "queued"), item.get("category", "General"),
                item.get("connections", 8), 1 if item.get("supports_range", True) else 0,
                item.get("error_message", None)
            ))

    def update_status(self, download_id: str, status: str, downloaded_bytes: Optional[int] = None, error: Optional[str] = None):
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

    def update_url(self, download_id: str, new_url: str):
        with self.conn:
            self.conn.execute("""
                UPDATE downloads 
                SET url = ?, error_message = NULL, status = 'paused'
                WHERE id = ?
            """, (new_url, download_id))

    def get_all_downloads(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM downloads ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def get_download(self, download_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM downloads WHERE id = ?", (download_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_download(self, download_id: str):
        with self.conn:
            self.conn.execute("DELETE FROM downloads WHERE id = ?", (download_id,))

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def get_setting(self, key: str, default: str = "") -> str:
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
