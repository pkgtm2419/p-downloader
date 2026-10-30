"""
Site Logins and Credentials Manager for P-Downloader.
Manages domain-specific HTTP authentication (Basic, Digest, Bearer tokens)
for automatic authentication on premium file hosts, private repositories, and intranets.
"""
import base64
import sqlite3
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
from .db import DownloadDB, DB_PATH

class CredentialsManager:
    _instance = None

    def __new__(cls, db=None):
        # Allow per-instance creation when db is explicitly provided (test isolation)
        if db is not None:
            instance = super().__new__(cls)
            instance._init(db)
            return instance
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init(None)
        return cls._instance

    def _init(self, db=None):
        self.db = db or DownloadDB()
        self._init_table()

    def _init_table(self):
        with self.db.conn:
            self.db.conn.execute("""
                CREATE TABLE IF NOT EXISTS site_logins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT UNIQUE NOT NULL,
                    username TEXT,
                    password TEXT,
                    auth_type TEXT DEFAULT 'basic',
                    token TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def set_login(self, domain: str, username: str = "", password: str = "", auth_type: str = "basic", token: str = ""):
        domain = domain.strip().lower()
        if "://" in domain:
            domain = urlparse(domain).netloc.split(":")[0]
        with self.db.conn:
            self.db.conn.execute("""
                INSERT OR REPLACE INTO site_logins (domain, username, password, auth_type, token)
                VALUES (?, ?, ?, ?, ?)
            """, (domain, username, password, auth_type, token))

    def get_login(self, domain: str) -> Optional[Dict[str, Any]]:
        domain = domain.strip().lower()
        if "://" in domain:
            domain = urlparse(domain).netloc.split(":")[0]
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM site_logins WHERE domain = ?", (domain,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_all_logins(self) -> List[Dict[str, Any]]:
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM site_logins ORDER BY domain ASC")
        return [dict(r) for r in cur.fetchall()]

    def delete_login(self, domain: str):
        domain = domain.strip().lower()
        if "://" in domain:
            domain = urlparse(domain).netloc.split(":")[0]
        with self.db.conn:
            self.db.conn.execute("DELETE FROM site_logins WHERE domain = ?", (domain,))

    def get_auth_headers_for_url(self, url: str) -> Dict[str, str]:
        headers = {}
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.split(":")[0].lower()
            login = self.get_login(domain)
            if not login:
                # Check parent domain (e.g., sub.example.com -> example.com)
                parts = domain.split(".")
                if len(parts) > 2:
                    parent_domain = ".".join(parts[-2:])
                    login = self.get_login(parent_domain)

            if login:
                auth_type = login.get("auth_type", "basic").lower()
                if auth_type == "bearer" and login.get("token"):
                    headers["Authorization"] = f"Bearer {login['token']}"
                elif auth_type == "basic" and (login.get("username") or login.get("password")):
                    raw_cred = f"{login.get('username', '')}:{login.get('password', '')}"
                    encoded = base64.b64encode(raw_cred.encode("utf-8")).decode("ascii")
                    headers["Authorization"] = f"Basic {encoded}"
        except Exception:
            pass
        return headers
