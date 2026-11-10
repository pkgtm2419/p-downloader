"""
Unit tests for database migration runner (IM-03).
Verifies schema versioning, incremental upgrades, backup creation,
and refusal to downgrade newer databases.
"""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from core.db_migrations.runner import (
    run_migrations, get_db_version, get_available_migrations, create_backup
)
from core.db import DownloadDB


class TestDBMigrations(unittest.TestCase):
    def test_available_migrations_discovery(self):
        migrations = get_available_migrations()
        self.assertTrue(len(migrations) >= 2)
        versions = [m[0] for m in migrations]
        self.assertEqual(versions, sorted(versions))
        self.assertEqual(versions[0], 1)
        self.assertEqual(versions[1], 2)

    def test_fresh_database_migrates_to_latest(self):
        conn = sqlite3.connect(":memory:")
        run_migrations(conn)
        version = get_db_version(conn)
        self.assertEqual(version, 2)

        # Verify all contract columns exist
        cursor = conn.cursor()
        cols = [r[1] for r in cursor.execute("PRAGMA table_info(downloads)").fetchall()]
        expected_cols = ["id", "url", "filename", "save_path", "kind", "headers_json", "page_url", "context_blob", "route_reason", "expected_checksum"]
        for col in expected_cols:
            self.assertIn(col, cols)
        conn.close()

    def test_legacy_v0_database_incremental_upgrade(self):
        conn = sqlite3.connect(":memory:")
        # Manually create old v1.0.0 table with user_version = 0
        conn.execute("""
            CREATE TABLE downloads (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                filename TEXT NOT NULL,
                save_path TEXT NOT NULL,
                total_bytes INTEGER DEFAULT 0,
                downloaded_bytes INTEGER DEFAULT 0,
                status TEXT DEFAULT 'queued'
            )
        """)
        conn.execute("INSERT INTO downloads (id, url, filename, save_path) VALUES ('t1', 'http://example.com/stream.m3u8', 'f1', 'p1')")
        conn.execute("INSERT INTO downloads (id, url, filename, save_path) VALUES ('t2', 'https://youtube.com/watch?v=123', 'f2', 'p2')")
        conn.commit()

        self.assertEqual(get_db_version(conn), 0)

        # Run migrations
        run_migrations(conn)
        self.assertEqual(get_db_version(conn), 2)

        # Verify kind was automatically inferred
        cursor = conn.cursor()
        cursor.execute("SELECT id, kind FROM downloads")
        rows = dict(cursor.fetchall())
        self.assertEqual(rows["t1"], "hls")
        self.assertEqual(rows["t2"], "extractor")
        conn.close()

    def test_refuse_newer_database(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA user_version = 999")
        conn.commit()

        with self.assertRaises(RuntimeError) as ctx:
            run_migrations(conn)
        self.assertIn("newer than application version", str(ctx.exception))
        conn.close()

    def test_backup_creation_on_disk(self):
        with tempfile.TemporaryDirectory() as td:
            db_file = os.path.join(td, "test.db")
            conn = sqlite3.connect(db_file)
            conn.execute("CREATE TABLE t (id INT)")
            conn.commit()
            conn.close()

            bak = create_backup(db_file)
            self.assertIsNotNone(bak)
            self.assertTrue(os.path.exists(bak))


if __name__ == "__main__":
    unittest.main()
