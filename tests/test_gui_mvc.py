import os
import unittest
from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication([])

from core.db import DownloadDB
from core.engine import DownloadEngine
from gui.models.download_table_model import DownloadTableModel, COLUMNS
from gui.controllers.download_controller import DownloadController


class TestGuiMVC(unittest.TestCase):
    def setUp(self):
        self.db = DownloadDB(":memory:")
        self.engine = DownloadEngine(self.db)
        self.controller = DownloadController(self.engine)
        self.model = DownloadTableModel()

    def tearDown(self):
        self.db.close()

    def test_table_model_columns_and_headers(self):
        self.assertEqual(self.model.columnCount(), 8)
        self.assertEqual(self.model.columnCount(), len(COLUMNS))
        self.assertEqual(self.model.headerData(0, Qt.Orientation.Horizontal), "File Name")
        self.assertEqual(self.model.headerData(1, Qt.Orientation.Horizontal), "Size")
        self.assertEqual(self.model.headerData(7, Qt.Orientation.Horizontal), "Actions")

    def test_table_model_data_and_lookup(self):
        sample_items = [
            {
                "task_id": "task_1",
                "filename": "archive.zip",
                "total_bytes": 10485760,  # 10 MB
                "downloaded_bytes": 5242880,  # 5 MB
                "status": "downloading",
                "speed": 1048576,  # 1 MB/s
                "category": "Compressed",
                "url": "https://example.com/archive.zip",
                "save_path": "C:/Downloads/archive.zip"
            },
            {
                "task_id": "task_2",
                "filename": "song.mp3",
                "total_bytes": 3145728,
                "downloaded_bytes": 3145728,
                "status": "completed",
                "speed": 0.0,
                "category": "Music",
                "url": "https://example.com/song.mp3",
                "save_path": "C:/Downloads/song.mp3"
            }
        ]

        self.model.set_items(sample_items)
        self.assertEqual(self.model.rowCount(), 2)

        # Row 0 tests
        idx_fn = self.model.index(0, 0)
        self.assertEqual(self.model.data(idx_fn, Qt.ItemDataRole.DisplayRole), "archive.zip")

        idx_sz = self.model.index(0, 1)
        self.assertIn("MB", self.model.data(idx_sz, Qt.ItemDataRole.DisplayRole))

        idx_st = self.model.index(0, 2)
        self.assertEqual(self.model.data(idx_st, Qt.ItemDataRole.DisplayRole), "Downloading")

        idx_prog = self.model.index(0, 3)
        self.assertIn("50.0%", self.model.data(idx_prog, Qt.ItemDataRole.DisplayRole))

        idx_cat = self.model.index(0, 6)
        self.assertEqual(self.model.data(idx_cat, Qt.ItemDataRole.DisplayRole), "Compressed")

        # Row 1 tests
        idx_song_st = self.model.index(1, 2)
        self.assertEqual(self.model.data(idx_song_st, Qt.ItemDataRole.DisplayRole), "Completed")

        # Lookup methods
        self.assertEqual(self.model.get_task_id(0), "task_1")
        self.assertEqual(self.model.get_task_id(1), "task_2")
        self.assertEqual(self.model.find_row_by_task_id("task_1"), 0)
        self.assertEqual(self.model.find_row_by_task_id("task_2"), 1)
        self.assertEqual(self.model.find_row_by_task_id("non_existent"), -1)

    def test_controller_filtering(self):
        self.db.add_download({
            "id": "t1",
            "url": "https://example.com/video.mp4",
            "filename": "video.mp4",
            "save_path": "/tmp/video.mp4",
            "total_bytes": 1000,
            "category": "Video"
        })
        self.db.add_download({
            "id": "t2",
            "url": "https://example.com/doc.pdf",
            "filename": "doc.pdf",
            "save_path": "/tmp/doc.pdf",
            "total_bytes": 500,
            "category": "Documents"
        })

        all_downloads = self.controller.get_all_downloads()
        self.assertEqual(len(all_downloads), 2)

        # Filter by Category
        video_downloads = self.controller.filter_downloads(category="Video")
        self.assertEqual(len(video_downloads), 1)
        self.assertEqual(video_downloads[0]["filename"], "video.mp4")

        # Filter by Search Query
        doc_downloads = self.controller.filter_downloads(search_query="pdf")
        self.assertEqual(len(doc_downloads), 1)
        self.assertEqual(doc_downloads[0]["filename"], "doc.pdf")


if __name__ == "__main__":
    unittest.main()
