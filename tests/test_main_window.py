import os
import unittest
from PyQt6.QtWidgets import QApplication
from core.db import DownloadDB
from core.engine import DownloadEngine
from gui.main_window import MainWindow


class TestMainWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.db = DownloadDB(":memory:")
        self.engine = DownloadEngine(self.db)
        self.window = MainWindow(self.engine)

    def tearDown(self):
        self.window.close()

    def test_main_window_init(self):
        self.assertIsNotNone(self.window)
        self.assertIn("P-Downloader", self.window.windowTitle())

    def test_menu_and_toolbar_actions(self):
        menubar = self.window.menuBar()
        self.assertIsNotNone(menubar)
        self.window._load_table_data()
        self.assertEqual(self.window.table.rowCount(), 0)
