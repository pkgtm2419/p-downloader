import unittest
from core.hls_downloader import HLSParser, HLSDownloadTask

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
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-KEY:METHOD=AES-128,URI="https://example.com/key.bin",IV=0x1234567890abcdef1234567890abcdef
#EXTINF:9.009,
segment_0.ts
#EXTINF:9.009,
segment_1.ts
#EXTINF:4.500,
segment_2.ts
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

    def test_parse_media_playlist(self):
        base_url = "https://example.com/video/"
        playlist = HLSParser.parse_media_playlist(SAMPLE_MEDIA_M3U8, base_url)
        self.assertEqual(playlist["segment_count"], 3)
        self.assertAlmostEqual(playlist["total_duration"], 22.518, places=2)

        key_info = playlist["key_info"]
        self.assertIsNotNone(key_info)
        self.assertEqual(key_info["method"], "AES-128")
        self.assertEqual(key_info["url"], "https://example.com/key.bin")
        self.assertEqual(key_info["iv"], "0x1234567890abcdef1234567890abcdef")

        self.assertEqual(playlist["segments"][0]["url"], "https://example.com/video/segment_0.ts")

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

if __name__ == "__main__":
    unittest.main()
