"""
Tests for Debrid Multi-Provider Client and Archive Extraction Pipeline (Phase 3).
"""
import os
import unittest
import tempfile
import shutil
import zipfile
import tarfile
from unittest.mock import MagicMock, patch

from core.debrid import DebridManager, RealDebridClient, AllDebridClient
from core.extractor_archive import (
    is_archive,
    is_first_volume_or_single_archive,
    group_archive_volumes,
    extract_archive
)
from core.db import DownloadDB


class TestDebridAndArchive(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="pdl_test_deb_arc_")
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.db = DownloadDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_debrid_hoster_detection(self):
        dm = DebridManager(self.db)
        self.assertTrue(dm.is_debrid_host("https://rapidgator.net/file/12345/file.rar.html"))
        self.assertTrue(dm.is_debrid_host("https://1fichier.com/?abcdef123"))
        self.assertTrue(dm.is_debrid_host("https://mega.nz/file/xyz#123"))
        self.assertFalse(dm.is_debrid_host("https://github.com/project/repo.zip"))
        self.assertFalse(dm.is_debrid_host("https://releases.ubuntu.com/iso.img"))

    @patch("core.debrid.real_debrid.requests.post")
    def test_real_debrid_unrestrict(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "id": "UNRESTRICT_123",
            "filename": "LargeArchive.part1.rar",
            "download": "https://12.download.real-debrid.com/d/xyz/LargeArchive.part1.rar",
            "filesize": 104857600
        }
        mock_post.return_value = mock_resp

        self.db.set_setting("debrid_rd_token", "fake_rd_token_123")
        dm = DebridManager(self.db)

        unrestricted, direct_url, meta = dm.unrestrict_link("https://rapidgator.net/file/123/LargeArchive.part1.rar")
        self.assertTrue(unrestricted)
        self.assertEqual(direct_url, "https://12.download.real-debrid.com/d/xyz/LargeArchive.part1.rar")
        self.assertEqual(meta["filename"], "LargeArchive.part1.rar")

    def test_archive_volume_detection_and_grouping(self):
        self.assertTrue(is_archive("data.zip"))
        self.assertTrue(is_archive("backup.tar.gz"))
        self.assertTrue(is_archive("movie.part01.rar"))
        self.assertTrue(is_archive("archive.7z.001"))
        self.assertFalse(is_archive("document.pdf"))

        self.assertTrue(is_first_volume_or_single_archive("data.zip"))
        self.assertTrue(is_first_volume_or_single_archive("movie.part01.rar"))
        self.assertTrue(is_first_volume_or_single_archive("movie.part1.rar"))
        self.assertFalse(is_first_volume_or_single_archive("movie.part02.rar"))
        self.assertFalse(is_first_volume_or_single_archive("archive.7z.002"))

        # Grouping
        files = [
            "series.part3.rar",
            "series.part1.rar",
            "series.part2.rar",
            "bonus.zip"
        ]
        groups = group_archive_volumes(files)
        self.assertIn("series", groups)
        self.assertEqual(groups["series"], ["series.part1.rar", "series.part2.rar", "series.part3.rar"])
        self.assertIn("bonus", groups)

    def test_zip_extraction_and_zip_slip_defense(self):
        zip_path = os.path.join(self.temp_dir, "safe_archive.zip")
        dest_dir = os.path.join(self.temp_dir, "unpacked")

        # Create valid zip
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("subfolder/file1.txt", "Content of file 1")
            zf.writestr("file2.txt", "Content of file 2")

        ok, msg, files = extract_archive(zip_path, dest_dir=dest_dir)
        self.assertTrue(ok)
        self.assertTrue(os.path.isfile(os.path.join(dest_dir, "subfolder", "file1.txt")))
        self.assertTrue(os.path.isfile(os.path.join(dest_dir, "file2.txt")))

        # Test Zip Slip attack payload is rejected
        slip_zip = os.path.join(self.temp_dir, "slip.zip")
        with zipfile.ZipFile(slip_zip, "w") as zf:
            zf.writestr("../../evil.txt", "Malicious content")

        slip_dest = os.path.join(self.temp_dir, "slip_unpacked")
        ok_slip, msg_slip, _ = extract_archive(slip_zip, dest_dir=slip_dest)
        self.assertFalse(ok_slip)
        self.assertIn("Zip Slip", msg_slip)

    def test_tar_extraction(self):
        tar_path = os.path.join(self.temp_dir, "test.tar.gz")
        dest_dir = os.path.join(self.temp_dir, "tar_unpacked")

        sample_txt = os.path.join(self.temp_dir, "test_file.txt")
        with open(sample_txt, "w") as f:
            f.write("Hello Tar")

        with tarfile.open(tar_path, "w:gz") as tf:
            tf.add(sample_txt, arcname="inside_tar.txt")

        ok, msg, files = extract_archive(tar_path, dest_dir=dest_dir)
        self.assertTrue(ok)
        self.assertTrue(os.path.isfile(os.path.join(dest_dir, "inside_tar.txt")))


if __name__ == "__main__":
    unittest.main()
