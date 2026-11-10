"""
Database migration engine for P-Downloader.
Tracks schema versions via PRAGMA user_version, executes forward-only
numbered migrations in transactions, and creates automatic pre-upgrade backups.
"""
import os
import re
import shutil
import sqlite3
import datetime
from pathlib import Path
from typing import List, Tuple, Optional

MIGRATIONS_DIR = Path(__file__).parent


def get_available_migrations() -> List[Tuple[int, Path]]:
    """Returns sorted list of (version_int, file_path) from core/db_migrations/."""
    migrations = []
    for f in MIGRATIONS_DIR.glob("*.sql"):
        m = re.match(r"^(\d{4})_", f.name)
        if m:
            version = int(m.group(1))
            migrations.append((version, f))
    migrations.sort(key=lambda x: x[0])
    return migrations


def get_db_version(conn: sqlite3.Connection) -> int:
    cursor = conn.cursor()
    cursor.execute("PRAGMA user_version")
    row = cursor.fetchone()
    return int(row[0]) if row else 0


def create_backup(db_path: str) -> Optional[str]:
    """Creates a timestamped backup before applying migrations on disk."""
    if not db_path or db_path == ":memory:":
        return None
    p = Path(db_path)
    if not p.is_file():
        return None
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = p.with_name(f"{p.name}.bak_{ts}")
    try:
        shutil.copy2(db_path, backup_path)
        return str(backup_path)
    except Exception:
        return None


def run_migrations(conn: sqlite3.Connection, db_path: Optional[str] = None):
    """
    Applies all pending forward migrations in ordered sequence.
    Safely executes statements inside transactions.
    """
    migrations = get_available_migrations()
    if not migrations:
        return

    latest_available = migrations[-1][0]
    current_version = get_db_version(conn)

    if current_version > latest_available:
        raise RuntimeError(
            f"Database schema version {current_version} is newer than application version {latest_available}. "
            "Please upgrade P-Downloader to open this database."
        )

    # Legacy database check: if user_version is 0 but tables exist, baseline to version 1 or run
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='downloads'")
    has_downloads = bool(cursor.fetchone())

    # Pre-migration backup if on disk and changes will be applied
    if current_version < latest_available and db_path and db_path != ":memory:":
        create_backup(db_path)

    for version, file_path in migrations:
        if version <= current_version:
            continue

        # If user_version is 0 and tables already exist, and we are processing 0001, just stamp version 1
        if version == 1 and has_downloads and current_version == 0:
            cursor.execute("PRAGMA user_version = 1")
            conn.commit()
            current_version = 1
            continue

        sql_content = file_path.read_text(encoding="utf-8")
        # Split statements by semicolon
        statements = [s.strip() for s in sql_content.split(";") if s.strip()]

        with conn:
            for stmt in statements:
                try:
                    conn.execute(stmt)
                except sqlite3.OperationalError as e:
                    # Gracefully handle duplicate columns if previously added ad-hoc
                    if "duplicate column name" in str(e).lower():
                        continue
                    raise

            cursor.execute(f"PRAGMA user_version = {version}")
        current_version = version
