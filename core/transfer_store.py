"""
Durable staging, atomic file publishing, and crash-safe journal management.
"""
import os
import json
import hashlib
import threading
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

@dataclass
class TransferState:
    task_id: str
    destination: str
    staging_path: str
    total_bytes: Optional[int]
    downloaded_bytes: int = 0
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    completed_blocks: List[int] = field(default_factory=list)
    status: str = "queued"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransferState':
        return cls(**data)


class BoundedBlockWriter:
    """
    Thread-safe writer that writes verified byte blocks directly at specific file offsets.
    Writes strictly to a staging path (.part) until full verification and publication.
    """
    def __init__(self, staging_path: str, preallocate_bytes: Optional[int] = None):
        self.staging_path = staging_path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(os.path.abspath(staging_path)), exist_ok=True)
        # Open in read+write binary mode, creating if missing
        if not os.path.exists(staging_path):
            with open(staging_path, "wb") as f:
                if preallocate_bytes and preallocate_bytes > 0:
                    # Sparse or zero seek
                    f.seek(preallocate_bytes - 1)
                    f.write(b"\0")
        self._file = open(staging_path, "r+b")

    def write_at(self, offset: int, data: bytes) -> None:
        """Write chunk at explicit file offset."""
        if not data:
            return
        with self._lock:
            self._file.seek(offset)
            self._file.write(data)

    def flush_checkpoint(self) -> None:
        """Flush OS write buffers to disk."""
        with self._lock:
            self._file.flush()
            try:
                os.fsync(self._file.fileno())
            except Exception:
                pass

    def close(self) -> None:
        """Flush and close underlying file handle."""
        with self._lock:
            if not self._file.closed:
                try:
                    self._file.flush()
                    os.fsync(self._file.fileno())
                except Exception:
                    pass
                self._file.close()


class TransferStore:
    """
    Manages transfer state persistence, journal checkpoints, and atomic publication.
    """
    def __init__(self, db_conn=None):
        self.db_conn = db_conn

    def _meta_path(self, staging_path: str) -> str:
        return staging_path + ".meta"

    def checkpoint(self, task_id: str, state: TransferState) -> None:
        """Save atomic state checkpoint to disk and SQLite journal."""
        meta_file = self._meta_path(state.staging_path)
        temp_meta = meta_file + f".tmp.{os.getpid()}"
        payload = json.dumps(state.to_dict(), indent=2)
        try:
            with open(temp_meta, "w", encoding="utf-8") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            # Atomic replace
            os.replace(temp_meta, meta_file)
        except Exception:
            if os.path.exists(temp_meta):
                try:
                    os.remove(temp_meta)
                except Exception:
                    pass

        if self.db_conn:
            try:
                with self.db_conn:
                    self.db_conn.execute("""
                        INSERT OR REPLACE INTO transfer_journals (task_id, staging_path, journal_json, updated_at)
                        VALUES (?, ?, ?, datetime('now'))
                    """, (task_id, state.staging_path, payload))
            except Exception:
                pass

    def load(self, task_id: str, staging_path: Optional[str] = None) -> Optional[TransferState]:
        """Load state from SQLite journal or .meta file."""
        if staging_path:
            meta_file = self._meta_path(staging_path)
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return TransferState.from_dict(data)
                except Exception:
                    pass

        if self.db_conn:
            try:
                cursor = self.db_conn.cursor()
                cursor.execute("SELECT journal_json FROM transfer_journals WHERE task_id = ?", (task_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    return TransferState.from_dict(json.loads(row[0]))
            except Exception:
                pass

        return None

    def resolve_unique_destination(self, destination: str) -> str:
        """
        Ensure destination file does not overwrite existing file unless it was
        the intended target. Append (1), (2), etc. if needed.
        """
        if not os.path.exists(destination):
            return destination
        dir_name = os.path.dirname(destination)
        base_name = os.path.basename(destination)
        name, ext = os.path.splitext(base_name)
        counter = 1
        while True:
            candidate = os.path.join(dir_name, f"{name} ({counter}){ext}")
            if not os.path.exists(candidate):
                return candidate
            counter += 1

    def publish(
        self,
        task_id: str,
        state: TransferState,
        expected_bytes: Optional[int] = None,
        checksum_sha256: Optional[str] = None
    ) -> str:
        """
        Verify integrity and atomically publish completed staging file to destination.
        Returns final publication destination path.
        """
        if not os.path.exists(state.staging_path):
            raise FileNotFoundError(f"Staging file not found: {state.staging_path}")

        actual_size = os.path.getsize(state.staging_path)
        if expected_bytes is not None and expected_bytes != actual_size:
            raise ValueError(
                f"File size mismatch: expected {expected_bytes} bytes, got {actual_size} bytes"
            )

        if checksum_sha256:
            hasher = hashlib.sha256()
            with open(state.staging_path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            actual_digest = hasher.hexdigest().lower()
            if actual_digest != checksum_sha256.lower():
                raise ValueError(
                    f"Checksum mismatch: expected {checksum_sha256}, got {actual_digest}"
                )

        final_dest = self.resolve_unique_destination(state.destination)
        os.makedirs(os.path.dirname(os.path.abspath(final_dest)), exist_ok=True)

        # Atomic move/rename
        os.replace(state.staging_path, final_dest)

        # Clean up meta file and database journal
        meta_file = self._meta_path(state.staging_path)
        if os.path.exists(meta_file):
            try:
                os.remove(meta_file)
            except Exception:
                pass

        if self.db_conn:
            try:
                with self.db_conn:
                    self.db_conn.execute("DELETE FROM transfer_journals WHERE task_id = ?", (task_id,))
            except Exception:
                pass

        return final_dest
