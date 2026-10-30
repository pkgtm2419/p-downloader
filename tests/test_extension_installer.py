"""
Tests for browser extension native host installer and manifest compliance.
Ensures no wildcards in native origins and valid per-browser registration.
"""
import unittest
import json
from pathlib import Path
from browser_extension.installer import (
    HOST_NAME,
    EXTENSION_ID,
    register_native_host,
    install_native_manifest
)

PROJECT_ROOT = Path(__file__).parent.parent

class TestExtensionInstaller(unittest.TestCase):
    def test_no_wildcard_in_resources_manifest(self):
        """Native host template in resources must never contain wildcard allowed origins."""
        manifest_path = PROJECT_ROOT / "resources" / "com.pdownloader.host.json"
        self.assertTrue(manifest_path.exists(), "com.pdownloader.host.json must exist")
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        origins = data.get("allowed_origins", [])
        for origin in origins:
            self.assertNotIn("*", origin, f"Wildcard origin forbidden: {origin}")
            self.assertTrue(origin.startswith("chrome-extension://"), "Must be a valid chrome-extension origin")

    def test_firefox_manifest_json_exists_and_valid(self):
        """Firefox-specific webextension manifest must define gecko ID."""
        ff_manifest = PROJECT_ROOT / "browser_extension" / "manifest.firefox.json"
        self.assertTrue(ff_manifest.exists(), "manifest.firefox.json must exist")
        with open(ff_manifest, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("browser_specific_settings", data)
        gecko_id = data["browser_specific_settings"].get("gecko", {}).get("id")
        self.assertEqual(gecko_id, "pdownloader@ultra.download")

    def test_register_native_host_interface(self):
        """register_native_host returns structured InstallResult."""
        res = register_native_host("chrome", EXTENSION_ID)
        self.assertTrue(res.success)
        self.assertEqual(res.browser, "chrome")
        self.assertTrue(Path(res.manifest_path).exists())

    def test_firefox_registration_generates_allowed_extensions(self):
        """Firefox native host manifest uses allowed_extensions and not allowed_origins."""
        res = register_native_host("firefox", "pdownloader@ultra.download")
        self.assertTrue(res.success)
        self.assertEqual(res.browser, "firefox")
        with open(res.manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("allowed_extensions", data)
        self.assertNotIn("allowed_origins", data)
        self.assertIn("pdownloader@ultra.download", data["allowed_extensions"])


if __name__ == "__main__":
    unittest.main()
