import unittest
from core.antivirus import AntivirusScanner

class TestAntivirusScanner(unittest.TestCase):
    def test_scanner_detection(self):
        # Should not raise exception
        path = AntivirusScanner.get_defender_path()
        avail = AntivirusScanner.is_available()
        self.assertEqual(bool(path), avail)

    def test_scan_missing_file(self):
        is_clean, msg = AntivirusScanner.scan_file("non_existent_file.xyz")
        self.assertFalse(is_clean)
        self.assertIn("not found", msg.lower())

if __name__ == "__main__":
    unittest.main()
