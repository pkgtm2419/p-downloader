"""
Advanced HLS correctness tests (IM-01 / B1-B8).
Verifies fMP4 init map parsing, audio group rendition extraction,
per-segment key rotation, byte-ranges, and DRM protection rejection.
"""
import unittest

from core.hls.parser import HLSParser
from core.hls.keys import HLSKeyManager
from core.hls.merge import merge_segments
from core.errors import AppError, ErrorCode

SAMPLE_FMP4_PLAYLIST = """#EXTM3U
#EXT-X-VERSION:7
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:1
#EXT-X-MAP:URI="init.mp4",BYTERANGE="800@0"
#EXTINF:6.0,
#EXT-X-BYTERANGE:150000@800
segment_1.m4s
#EXTINF:6.0,
#EXT-X-BYTERANGE:160000@150800
segment_2.m4s
#EXT-X-ENDLIST
"""

SAMPLE_AUDIO_MASTER = """#EXTM3U
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio-eng",NAME="English",DEFAULT=YES,AUTOSELECT=YES,URI="audio/en.m3u8"
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio-esp",NAME="Spanish",DEFAULT=NO,AUTOSELECT=YES,URI="audio/es.m3u8"
#EXT-X-STREAM-INF:BANDWIDTH=2000000,RESOLUTION=1280x720,AUDIO="audio-eng"
video/720p.m3u8
"""

SAMPLE_KEY_ROTATION_PLAYLIST = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:50
#EXT-X-KEY:METHOD=AES-128,URI="https://example.com/key1.bin",IV=0x00000000000000000000000000000001
#EXTINF:10.0,
seg1.ts
#EXT-X-KEY:METHOD=AES-128,URI="https://example.com/key2.bin",IV=0x00000000000000000000000000000002
#EXTINF:10.0,
seg2.ts
#EXT-X-KEY:METHOD=NONE
#EXTINF:10.0,
seg3.ts
#EXT-X-ENDLIST
"""


class TestHLSCorrectness(unittest.TestCase):
    def test_fmp4_init_map_and_byteranges(self):
        base_url = "https://example.com/stream/"
        playlist = HLSParser.parse_media_playlist(SAMPLE_FMP4_PLAYLIST, base_url)

        self.assertEqual(playlist["init_map_url"], "https://example.com/stream/init.mp4")
        self.assertEqual(playlist["init_map_byterange"], "800@0")
        self.assertFalse(playlist["is_live"])
        self.assertEqual(len(playlist["segments"]), 2)

        seg1 = playlist["segments"][0]
        self.assertEqual(seg1["byterange"], "150000@800")
        self.assertEqual(seg1["sequence_number"], 1)

    def test_separate_audio_renditions(self):
        base_url = "https://example.com/master/"
        master = HLSParser.parse_master_playlist(SAMPLE_AUDIO_MASTER, base_url)

        self.assertEqual(len(master), 1)
        variant = master[0]
        self.assertEqual(variant["audio_group_id"], "audio-eng")

        self.assertIn("audio-eng", master.audio_groups)
        audio_tracks = master.audio_groups["audio-eng"]
        self.assertEqual(len(audio_tracks), 1)
        self.assertEqual(audio_tracks[0]["name"], "English")
        self.assertEqual(audio_tracks[0]["url"], "https://example.com/master/audio/en.m3u8")
        self.assertTrue(audio_tracks[0]["is_default"])

    def test_key_rotation(self):
        base_url = "https://example.com/vod/"
        playlist = HLSParser.parse_media_playlist(SAMPLE_KEY_ROTATION_PLAYLIST, base_url)
        segments = playlist["segments"]
        self.assertEqual(len(segments), 3)

        # seg1 has key1
        self.assertEqual(segments[0]["key_info"]["url"], "https://example.com/key1.bin")
        # seg2 has key2
        self.assertEqual(segments[1]["key_info"]["url"], "https://example.com/key2.bin")
        # seg3 has NONE
        self.assertEqual(segments[2]["key_info"]["method"], "NONE")

    def test_drm_protected_rejection(self):
        key_mgr = HLSKeyManager()
        drm_key_info = {
            "method": "SAMPLE-AES",
            "url": "https://example.com/widevine.key"
        }
        with self.assertRaises(AppError) as ctx:
            key_mgr.decrypt_segment(b"encrypted_sample_bytes", drm_key_info, 1)
        self.assertEqual(ctx.exception.code, ErrorCode.DRM_PROTECTED)
        self.assertIn("protected encryption", ctx.exception.message)


if __name__ == "__main__":
    unittest.main()
