"""
Durable browser download reservation, ownership negotiation, and handoff state machine.
"""
import uuid
import json
import time
import hashlib
import sqlite3
from typing import Optional, Dict, Any
from dataclasses import dataclass
from .download_models import DownloadRequest, DownloadKind

@dataclass(frozen=True)
class HandoffOffer:
    handoff_id: str
    capture_id: str
    request_fingerprint: str
    expires_at_utc: float
    state: str  # PREPARED, COMMITTED, RELEASED, EXPIRED
    task_id: Optional[str] = None

class HandoffStore:
    """
    Manages transactional two-phase ownership handoffs between browser and desktop.
    """
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._init_table()

    def _init_table(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS browser_handoffs (
                    handoff_id TEXT PRIMARY KEY,
                    capture_id TEXT UNIQUE,
                    url TEXT NOT NULL,
                    filename TEXT,
                    destination TEXT,
                    request_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    task_id TEXT,
                    expires_at_utc REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def reserve(
        self,
        request: DownloadRequest,
        capture_id: Optional[str] = None,
        ttl_seconds: float = 30.0
    ) -> HandoffOffer:
        """
        Create a durable PREPARED reservation. Does not start transfer.
        Idempotent on capture_id.
        """
        cap_id = capture_id or f"cap_{uuid.uuid4().hex[:12]}"
        now = time.time()
        expires_at = now + ttl_seconds
        req_fp = hashlib.sha256(request.url.encode("utf-8")).hexdigest()[:16]

        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SELECT handoff_id, state, task_id, expires_at_utc FROM browser_handoffs WHERE capture_id = ?", (cap_id,))
            row = cursor.fetchone()
            if row:
                return HandoffOffer(
                    handoff_id=row[0],
                    capture_id=cap_id,
                    request_fingerprint=req_fp,
                    expires_at_utc=row[3],
                    state=row[1],
                    task_id=row[2]
                )

            handoff_id = f"hnd_{uuid.uuid4().hex[:16]}"
            req_data = {
                "url": request.url,
                "filename": request.filename,
                "destination": request.destination,
                "kind": request.kind.value if hasattr(request.kind, "value") else str(request.kind),
                "connections": request.connections
            }
            cursor.execute("""
                INSERT INTO browser_handoffs
                (handoff_id, capture_id, url, filename, destination, request_json, state, expires_at_utc)
                VALUES (?, ?, ?, ?, ?, ?, 'PREPARED', ?)
            """, (
                handoff_id,
                cap_id,
                request.url,
                request.filename,
                request.destination,
                json.dumps(req_data),
                expires_at
            ))

            return HandoffOffer(
                handoff_id=handoff_id,
                capture_id=cap_id,
                request_fingerprint=req_fp,
                expires_at_utc=expires_at,
                state="PREPARED"
            )

    def commit(self, handoff_id: str, engine=None) -> str:
        """
        Commit ownership after browser confirms cancellation.
        Idempotent: returns existing task_id if already committed.
        """
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT state, task_id, request_json, url, filename, destination FROM browser_handoffs WHERE handoff_id = ?",
                (handoff_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Unknown handoff_id: {handoff_id}")

            state, task_id, req_json, url, filename, destination = row
            if state == "COMMITTED" and task_id:
                return task_id

            if not task_id:
                task_id = str(uuid.uuid4())[:8]

            if engine:
                req_dict = json.loads(req_json)
                engine.create_download(
                    url=url,
                    filename=filename,
                    save_path=destination,
                    connections=req_dict.get("connections") or 8,
                    auto_start=True
                )

            cursor.execute(
                "UPDATE browser_handoffs SET state = 'COMMITTED', task_id = ? WHERE handoff_id = ?",
                (task_id, handoff_id)
            )
            return task_id

    def release(self, handoff_id: str) -> None:
        """Release reservation when browser cancels or declines."""
        with self.conn:
            self.conn.execute(
                "UPDATE browser_handoffs SET state = 'RELEASED' WHERE handoff_id = ?",
                (handoff_id,)
            )

    def get_status(self, handoff_id: str) -> Optional[HandoffOffer]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT handoff_id, capture_id, url, state, task_id, expires_at_utc FROM browser_handoffs WHERE handoff_id = ?",
            (handoff_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        now = time.time()
        state = row[3]
        if state == "PREPARED" and now > row[5]:
            state = "EXPIRED"

        req_fp = hashlib.sha256(row[2].encode("utf-8")).hexdigest()[:16]
        return HandoffOffer(
            handoff_id=row[0],
            capture_id=row[1],
            request_fingerprint=req_fp,
            expires_at_utc=row[5],
            state=state,
            task_id=row[4]
        )
