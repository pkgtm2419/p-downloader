"""
Unit and integration tests for Phase 6:
Themes, Accessibility metadata, Internationalization (i18n) & RTL Layouts, and Memory Optimization.
"""
import unittest

from gui.styles import list_themes, get_theme_stylesheet, format_bytes, format_speed, format_eta
from core.i18n import is_rtl, t, set_current_language, get_current_language, SUPPORTED_LANGUAGES
from core.db import DownloadDB


class TestUIThemesAndI18n(unittest.TestCase):
    def test_theme_registry_and_generation(self):
        themes = list_themes()
        self.assertEqual(len(themes), 9)
        self.assertIn("fluent_light", themes)
        self.assertIn("fluent_dark", themes)
        self.assertIn("classic_98", themes)
        self.assertIn("aero_neon", themes)
        self.assertIn("dracula", themes)
        self.assertIn("nord", themes)
        self.assertIn("monokai", themes)
        self.assertIn("cyberpunk", themes)
        self.assertIn("high_contrast", themes)

        for th in themes:
            qss = get_theme_stylesheet(th)
            self.assertIsInstance(qss, str)
            self.assertTrue(len(qss) > 200, f"Theme {th} stylesheet is unexpectedly short")
            self.assertIn("QMainWindow", qss)
            self.assertIn("QPushButton", qss)

    def test_formatting_utilities(self):
        self.assertEqual(format_bytes(0), "0 B")
        self.assertEqual(format_bytes(1024), "1.00 KB")
        self.assertEqual(format_bytes(1048576), "1.00 MB")
        self.assertEqual(format_speed(2097152), "2.00 MB/s")
        self.assertEqual(format_eta(1000, 0), "--:--:--")
        self.assertEqual(format_eta(60, 1), "00:01:00")

    def test_i18n_translations_and_rtl(self):
        self.assertTrue(is_rtl("ar"))
        self.assertTrue(is_rtl("he"))
        self.assertTrue(is_rtl("ur"))
        self.assertFalse(is_rtl("en"))
        self.assertFalse(is_rtl("es"))
        self.assertFalse(is_rtl("zh"))

        self.assertEqual(t("add_url", "es"), "Añadir URL")
        self.assertEqual(t("pause", "ar"), "إيقاف مؤقت")
        self.assertEqual(t("resume", "zh"), "继续")
        self.assertEqual(t("delete", "ru"), "Удалить")
        self.assertEqual(t("completed", "fr"), "Terminé")
        self.assertEqual(t("unknown_key_xyz", "en"), "unknown_key_xyz")

        # Test stateful language setting
        set_current_language("de")
        self.assertEqual(get_current_language(), "de")
        self.assertEqual(t("downloading"), "Herunterladen")
        set_current_language("en")

    def test_database_memory_pragmas(self):
        db = DownloadDB(":memory:")
        cursor = db.conn.cursor()
        cursor.execute("PRAGMA cache_size")
        cache_size = cursor.fetchone()[0]
        # On SQLite, PRAGMA cache_size = -2000 sets it to 2000 KiB (approx -2000)
        self.assertEqual(cache_size, -2000)
        db.close()


if __name__ == "__main__":
    unittest.main()
