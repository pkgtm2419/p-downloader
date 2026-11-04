"""
Unit tests for Browser Extension Manager and Packaging.
"""
import os
import sys
import tempfile
import zipfile
import unittest

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

from gui.extension_dialog import ExtensionDialog
from browser_extension.installer import detect_installed_browsers, EXTENSION_ID

class TestExtensionManager(unittest.TestCase):
    def test_browser_detection(self):
        detected = detect_installed_browsers()
        self.assertIsInstance(detected, dict)

    def test_extension_dialog_instantiation(self):
        dlg = ExtensionDialog()
        self.assertIsNotNone(dlg)
        self.assertIn("Browser Extension", dlg.windowTitle())

    def test_package_extension_zip(self):
        ext_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "browser_extension"))
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = os.path.join(tmp_dir, "test-extension.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                for root, dirs, files in os.walk(ext_dir):
                    for f in files:
                        full_p = os.path.join(root, f)
                        rel_p = os.path.relpath(full_p, ext_dir)
                        if "__pycache__" in rel_p or rel_p.endswith((".pyc", ".tmp")):
                            continue
                        z.write(full_p, rel_p)

            self.assertTrue(os.path.isfile(zip_path))
            self.assertGreater(os.path.getsize(zip_path), 1000)

            # Verify manifest is inside
            with zipfile.ZipFile(zip_path, "r") as z:
                names = z.namelist()
                self.assertIn("manifest.json", names)
                self.assertIn("background.js", names)
                self.assertIn("content.js", names)

if __name__ == "__main__":
    unittest.main()

