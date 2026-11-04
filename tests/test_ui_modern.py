"""
UI, Light Theme, Collapsible Sidebar, and Action Menu tests for P-Downloader.
"""
import os
import sys
import unittest

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt6.QtWidgets import QApplication, QPushButton
from PyQt6.QtGui import QFont

app = QApplication.instance() or QApplication(sys.argv)
app.setFont(QFont("Segoe UI", 10))

from core.db import DownloadDB
from core.engine import DownloadEngine
from core.categories import sanitize_filename, resolve_unique_filename, is_generic_route_name
from gui.main_window import MainWindow
from gui.add_dialog import AddDownloadDialog
from gui.youtube_dialog import YouTubeDownloadDialog
from gui.styles import MAIN_STYLESHEET, LIGHT_THEME_STYLESHEET, format_bytes, format_speed, format_eta


class TestModernUI(unittest.TestCase):
    def setUp(self):
        self.db = DownloadDB(":memory:")
        self.engine = DownloadEngine(self.db)
        self.window = MainWindow(self.engine)

    def tearDown(self):
        self.window.close()
        self.db.close()

    def test_main_window_renders_cleanly(self):
        self.assertIsNotNone(self.window)
        self.assertIn("P-Downloader", self.window.windowTitle())
        self.assertEqual(self.window.table.columnCount(), 8)
        self.assertEqual(self.window.table.horizontalHeaderItem(7).text(), "Actions")
        self.assertEqual(self.window.table.verticalHeader().defaultSectionSize(), 48)
        self.assertIsNotNone(self.window.empty_widget)

    def test_light_theme_is_default(self):
        self.assertEqual(MAIN_STYLESHEET, LIGHT_THEME_STYLESHEET)
        self.assertIn("#f8fafc", MAIN_STYLESHEET)
        self.assertIn("#0f172a", MAIN_STYLESHEET)
        self.assertIn("#f4f7fb", MAIN_STYLESHEET)

    def test_sidebar_collapsed_by_default(self):
        # Must start collapsed by default (68px wide)
        self.assertTrue(self.window.sidebar_is_collapsed)
        self.assertEqual(self.window.sidebar_widget.width(), 68)
        self.assertEqual(self.window.btn_toggle_sidebar.toolTip(), "Expand Sidebar (Ctrl+B)")
        # Tooltip is preserved for hover
        self.assertIn("All Downloads", self.window.item_all.toolTip(0))

    def test_sidebar_toggle_expand_and_collapse(self):
        # Toggle to expanded (230px wide)
        self.window._toggle_sidebar()
        self.assertFalse(self.window.sidebar_is_collapsed)
        self.assertEqual(self.window.sidebar_widget.width(), 230)
        self.assertEqual(self.window.btn_toggle_sidebar.toolTip(), "Collapse Sidebar (Ctrl+B)")

        # Toggle back to collapsed (68px wide)
        self.window._toggle_sidebar()
        self.assertTrue(self.window.sidebar_is_collapsed)
        self.assertEqual(self.window.sidebar_widget.width(), 68)
        self.assertEqual(self.window.btn_toggle_sidebar.toolTip(), "Expand Sidebar (Ctrl+B)")

    def test_add_download_dialog_workflow(self):
        dlg = AddDownloadDialog(self.window, initial_url="https://example.com/archive.zip")
        self.assertEqual(dlg.txt_url.text(), "https://example.com/archive.zip")
        self.assertTrue(dlg.btn_start.isEnabled())
        # Check result dictionary contract
        res = dlg.get_result()
        self.assertEqual(res["url"], "https://example.com/archive.zip")
        self.assertTrue(res["auto_start"])
        dlg.close()

    def test_add_download_dialog_video_quality_selection(self):
        dlg = AddDownloadDialog(self.window, initial_url="https://www.youtube.com/watch?v=jx0qbW_YTCs")
        fake_info = {
            "is_youtube": True,
            "title": "Aap Ki Kashish",
            "filename": "Aap_Ki_Kashish.mp4",
            "total_bytes": 16865250,
            "duration": 312,
            "selectable_formats": [
                {"label": "Best Available (360p)", "quality": "best", "resolution": "360p", "ext": "mp4", "filesize": 16865250, "has_audio": True, "needs_merge": False},
                {"label": "Audio Only (MP3)", "quality": "audio", "resolution": "Audio Only", "ext": "mp3", "filesize": 5000000, "has_audio": True, "needs_merge": False}
            ]
        }
        dlg._on_probe_success(fake_info)
        self.assertFalse(dlg.sec_quality_group.isHidden())
        self.assertGreaterEqual(dlg.cmb_quality.count(), 2)

        # Select MP3 option
        dlg.cmb_quality.setCurrentIndex(1)
        self.assertTrue(dlg.txt_filename.text().endswith(".mp3"))
        dlg.close()

    def test_generic_route_names_filtered(self):
        self.assertTrue(is_generic_route_name("watch"))
        self.assertTrue(is_generic_route_name("videoplayback"))
        self.assertTrue(is_generic_route_name("download"))
        self.assertFalse(is_generic_route_name("Aap_Ki_Kashish.mp4"))

    def test_unique_filename_resolution(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            fn1 = resolve_unique_filename(td, "song.mp4")
            self.assertEqual(fn1, "song.mp4")
            with open(os.path.join(td, "song.mp4"), "w") as f:
                f.write("test")
            fn2 = resolve_unique_filename(td, "song.mp4")
            self.assertEqual(fn2, "song (1).mp4")

    def test_live_table_completion_synchronization(self):
        task = self.engine.create_download(
            url="https://example.com/test_sync.bin",
            filename="test_sync.bin",
            auto_start=False
        )
        self.window._load_table_data()
        self.assertEqual(self.window.table.rowCount(), 1)
        st_cell = self.window.table.item(0, 2)
        self.assertEqual(st_cell.text(), "Queued")

        # Simulate completion
        task.status = "completed"
        task.total_bytes = 1000
        task.downloaded_bytes = 1000
        self.window._handle_engine_update_on_gui(task)

        # Re-check row
        st_cell = self.window.table.item(0, 2)
        self.assertEqual(st_cell.text(), "Finished")
        pbar = self.window.table.cellWidget(0, 3)
        self.assertEqual(pbar.value(), 100)

    def test_format_helpers(self):
        self.assertEqual(format_bytes(0), "0 B")
        self.assertEqual(format_bytes(1048576), "1.00 MB")
        self.assertEqual(format_speed(1048576), "1.00 MB/s")
        self.assertEqual(format_eta(1048576, 1048576), "00:00:01")


if __name__ == "__main__":
    unittest.main()
