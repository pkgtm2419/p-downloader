"""
Unit tests for P-Downloader core functionality.
"""
import os
import unittest
import tempfile
from pathlib import Path
from core.categories import get_category_for_filename, get_default_save_path
from core.db import DownloadDB
from core.segment import Segment, probe_url
from core.engine import DownloadEngine

class TestPDownloader(unittest.TestCase):
    def test_category_mapping(self):
        self.assertEqual(get_category_for_filename("archive.zip"), "Compressed")
        self.assertEqual(get_category_for_filename("document.pdf"), "Documents")
        self.assertEqual(get_category_for_filename("song.mp3"), "Music")
        self.assertEqual(get_category_for_filename("setup.exe"), "Programs")
        self.assertEqual(get_category_for_filename("movie.mp4"), "Video")
        self.assertEqual(get_category_for_filename("unknown.xyz"), "General")

    def test_database_operations(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name
        
        try:
            db = DownloadDB(db_path)
            # Add item
            item = {
                "id": "test1234",
                "url": "https://example.com/file.zip",
                "filename": "file.zip",
                "save_path": "C:\\Downloads\\file.zip",
                "total_bytes": 1048576,
                "downloaded_bytes": 0,
                "status": "queued",
                "category": "Compressed",
                "connections": 8,
                "supports_range": True
            }
            db.add_download(item)

            retrieved = db.get_download("test1234")
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved["filename"], "file.zip")
            self.assertEqual(retrieved["total_bytes"], 1048576)

            # Update status
            db.update_status("test1234", "completed", 1048576)
            retrieved = db.get_download("test1234")
            self.assertEqual(retrieved["status"], "completed")
            self.assertEqual(retrieved["downloaded_bytes"], 1048576)

            # Settings
            db.set_setting("test_key", "test_val")
            self.assertEqual(db.get_setting("test_key"), "test_val")

            # Delete
            db.delete_download("test1234")
            self.assertIsNone(db.get_download("test1234"))
            db.close()
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_segment_calculations(self):
        seg = Segment(0, 0, 999)
        self.assertEqual(seg.total_size, 1000)
        self.assertEqual(seg.current_offset, 0)
        seg.downloaded = 500
        self.assertEqual(seg.current_offset, 500)
        
        d = seg.to_dict()
        seg2 = Segment.from_dict(d)
        self.assertEqual(seg2.index, 0)
        self.assertEqual(seg2.start, 0)
        self.assertEqual(seg2.end, 999)
        self.assertEqual(seg2.downloaded, 500)

if __name__ == "__main__":
    unittest.main()
