import json
import os
import tempfile
import unittest

from core.db import DownloadDB
from core.settings import (
    SETTINGS_SCHEMA,
    SettingType,
    SettingSection,
    get_setting_def,
    validate_setting,
    to_db_string,
    from_db_string,
    export_settings_dict,
    export_settings_json,
    import_settings_json,
)


class TestSettingsRegistry(unittest.TestCase):
    def test_schema_definitions(self):
        self.assertIn("connection_mode", SETTINGS_SCHEMA)
        self.assertIn("default_connections", SETTINGS_SCHEMA)
        self.assertIn("use_proxy", SETTINGS_SCHEMA)
        self.assertIn("theme", SETTINGS_SCHEMA)
        self.assertIn("video_concurrent_fragments", SETTINGS_SCHEMA)

        proxy_def = get_setting_def("use_proxy")
        self.assertIsNotNone(proxy_def)
        self.assertEqual(proxy_def.type, SettingType.BOOL)
        self.assertEqual(proxy_def.section, SettingSection.PROXY)

    def test_validate_bool(self):
        self.assertTrue(validate_setting("use_proxy", "1"))
        self.assertTrue(validate_setting("use_proxy", "true"))
        self.assertTrue(validate_setting("use_proxy", True))
        self.assertFalse(validate_setting("use_proxy", "0"))
        self.assertFalse(validate_setting("use_proxy", "false"))
        self.assertFalse(validate_setting("use_proxy", False))

        with self.assertRaises(ValueError):
            validate_setting("use_proxy", "not_a_bool")

    def test_validate_int_bounds(self):
        self.assertEqual(validate_setting("default_connections", "8"), 8)
        self.assertEqual(validate_setting("default_connections", 16), 16)

        # Min is 1, max is 32
        with self.assertRaises(ValueError):
            validate_setting("default_connections", 0)
        with self.assertRaises(ValueError):
            validate_setting("default_connections", 64)

    def test_validate_enum(self):
        # Case insensitive match
        self.assertEqual(validate_setting("proxy_proto", "http"), "HTTP")
        self.assertEqual(validate_setting("proxy_proto", "SOCKS5"), "SOCKS5")

        with self.assertRaises(ValueError):
            validate_setting("proxy_proto", "GOPHER")

    def test_db_coercion(self):
        # Bool to string "1"/"0"
        self.assertEqual(to_db_string("use_proxy", True), "1")
        self.assertEqual(to_db_string("use_proxy", False), "0")
        self.assertEqual(from_db_string("use_proxy", "1"), True)
        self.assertEqual(from_db_string("use_proxy", "0"), False)

        # Int coercion
        self.assertEqual(to_db_string("default_connections", 12), "12")
        self.assertEqual(from_db_string("default_connections", "12"), 12)

    def test_export_import_json(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test_settings.db")
            db = DownloadDB(db_path)
            try:
                # Set initial values
                db.set_typed_setting("default_connections", 10)
                db.set_typed_setting("use_proxy", True)
                db.set_typed_setting("proxy_proto", "SOCKS5")
                db.set_typed_setting("proxy_port", 1080)

                # Export to JSON
                exported_json = export_settings_json(db)
                data = json.loads(exported_json)
                self.assertEqual(data["default_connections"], 10)
                self.assertEqual(data["use_proxy"], True)
                self.assertEqual(data["proxy_proto"], "SOCKS5")
                self.assertEqual(data["proxy_port"], 1080)

                # Modify in JSON and import into fresh DB
                data["default_connections"] = 14
                data["proxy_port"] = 9050
                data["use_proxy"] = False

                applied = import_settings_json(db, json.dumps(data))
                self.assertEqual(applied["default_connections"], 14)
                self.assertEqual(applied["proxy_port"], 9050)
                self.assertEqual(applied["use_proxy"], False)

                # Verify via typed getter
                self.assertEqual(db.get_typed_setting("default_connections"), 14)
                self.assertEqual(db.get_typed_setting("proxy_port"), 9050)
                self.assertEqual(db.get_typed_setting("use_proxy"), False)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
