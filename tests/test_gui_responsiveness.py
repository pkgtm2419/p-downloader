"""
GUI responsiveness and settings dialog configuration tests.
"""
import unittest
import os
from PyQt6.QtWidgets import QApplication
from core.db import DownloadDB
from gui.settings_dialog import SettingsDialog

os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication([])

class TestGuiResponsiveness(unittest.TestCase):
    def setUp(self):
        self.db = DownloadDB(":memory:")
        self.dlg = SettingsDialog(self.db)

    def test_settings_dialog_has_v2_controls(self):
        """SettingsDialog includes connection mode and advanced stream configuration."""
        self.assertTrue(hasattr(self.dlg, "cmb_conn_mode"), "Missing cmb_conn_mode")
        self.assertTrue(hasattr(self.dlg, "spin_simultaneous"), "Missing spin_simultaneous")

    def test_save_and_reload_v2_settings(self):
        """Changes to settings UI are saved to DB and restored on reload."""
        self.dlg.cmb_conn_mode.setCurrentText("Fixed Streams")
        self.dlg.spin_simultaneous.setValue(4)
        self.dlg._save_settings()

        dlg2 = SettingsDialog(self.db)
        self.assertEqual(dlg2.cmb_conn_mode.currentText(), "Fixed Streams")
        self.assertEqual(dlg2.spin_simultaneous.value(), 4)


if __name__ == "__main__":
    unittest.main()
