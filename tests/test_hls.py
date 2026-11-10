import unittest
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch
from core.hls_downloader import HLSParser, HLSDownloadTask, HLSDownloader

SAMPLE_MASTER_M3U8 = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360,CODECS="avc1.4d401e,mp4a.40.2"
360p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2500000,RESOLUTION=1280x720,CODECS="avc1.4d401f,mp4a.40.2"
720p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2"
1080p.m3u8
"""

SAMPLE_MEDIA_M3U8 = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:150
#EXT-X-KEY:METHOD=AES-128,URI="https://example.com/key.bin",IV=0x1234567890abcdef1234567890abcdef
#EXTINF:9.009,
segment_0.ts
#EXTINF:9.009,
segment_1.ts
#EXTINF:4.500,
segment_2.ts
#EXT-X-ENDLIST
"""

SAMPLE_MEDIA_NO_IV = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:42
#EXT-X-KEY:METHOD=AES-128,URI="https://example.com/key.bin"
#EXTINF:10.0,
seq_0.ts
#EXTINF:10.0,
seq_1.ts
#EXT-X-ENDLIST
"""

class TestHLSParser(unittest.TestCase):
    def test_is_master_playlist(self):
        self.assertTrue(HLSParser.is_master_playlist(SAMPLE_MASTER_M3U8))
        self.assertFalse(HLSParser.is_master_playlist(SAMPLE_MEDIA_M3U8))

    def test_parse_master_playlist(self):
        base_url = "https://example.com/video/"
        variants = HLSParser.parse_master_playlist(SAMPLE_MASTER_M3U8, base_url)
        self.assertEqual(len(variants), 3)

        # Sorted by bandwidth descending
        self.assertEqual(variants[0]["resolution"], "1920x1080")
        self.assertEqual(variants[0]["bandwidth"], 5000000)
        self.assertEqual(variants[0]["url"], "https://example.com/video/1080p.m3u8")

        self.assertEqual(variants[1]["resolution"], "1280x720")
        self.assertEqual(variants[2]["resolution"], "640x360")

    def test_parse_media_playlist_with_sequence(self):
        base_url = "https://example.com/video/"
        playlist = HLSParser.parse_media_playlist(SAMPLE_MEDIA_M3U8, base_url)
        self.assertEqual(playlist["segment_count"], 3)
        self.assertEqual(playlist["media_sequence"], 150)
        self.assertAlmostEqual(playlist["total_duration"], 22.518, places=2)

        key_info = playlist["key_info"]
        self.assertIsNotNone(key_info)
        self.assertEqual(key_info["method"], "AES-128")
        self.assertEqual(key_info["url"], "https://example.com/key.bin")
        self.assertEqual(key_info["iv"], "0x1234567890abcdef1234567890abcdef")

        self.assertEqual(playlist["segments"][0]["sequence_number"], 150)
        self.assertEqual(playlist["segments"][1]["sequence_number"], 151)
        self.assertEqual(playlist["segments"][2]["sequence_number"], 152)

    def test_parse_media_playlist_no_explicit_iv(self):
        base_url = "https://example.com/video/"
        playlist = HLSParser.parse_media_playlist(SAMPLE_MEDIA_NO_IV, base_url)
        self.assertEqual(playlist["media_sequence"], 42)
        self.assertIsNone(playlist["key_info"]["iv"])
        self.assertEqual(playlist["segments"][0]["sequence_number"], 42)
        self.assertEqual(playlist["segments"][1]["sequence_number"], 43)

    def test_hls_download_task_interface(self):
        task = HLSDownloadTask(
            task_id="hls001",
            url="https://example.com/stream.m3u8",
            save_path="test_video.mp4",
            connections=4
        )
        task.prepare()
        self.assertTrue(task.is_hls)
        self.assertEqual(task.status, "queued")
        self.assertTrue(task.supports_range)

    def test_aes_128_sequence_iv_decryption(self):
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import padding
        except ImportError:
            self.skipTest("cryptography not installed")

        aes_key = os.urandom(16)
        seq_num = 42
        iv_bytes = seq_num.to_bytes(16, byteorder="big")

        original_plaintext = b"HLS MPEG-TS segment payload content with padding!"
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(original_plaintext) + padder.finalize()

        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv_bytes), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

        # Decrypt matching core/hls_downloader.py logic
        decrypt_cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv_bytes), backend=default_backend())
        decryptor = decrypt_cipher.decryptor()
        raw_decrypted = decryptor.update(encrypted_data) + decryptor.finalize()

        unpadder = padding.PKCS7(128).unpadder()
        decrypted_text = unpadder.update(raw_decrypted) + unpadder.finalize()

        self.assertEqual(decrypted_text, original_plaintext)

    def test_hls_downloader_pause_behavior(self):
        temp_dir = tempfile.mkdtemp(prefix="pdl_test_hls_pause_")
        try:
            save_path = os.path.join(temp_dir, "output.ts")
            downloader = HLSDownloader("https://example.com/stream.m3u8", save_path)
            downloader.pause()
            self.assertTrue(downloader.is_paused)
            self.assertEqual(downloader.status, "paused")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    unittest.main()
