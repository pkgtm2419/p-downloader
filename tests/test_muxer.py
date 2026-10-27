import os
import unittest
from core.muxer import FFmpegMuxer

class TestFFmpegMuxer(unittest.TestCase):
    def test_ffmpeg_detection(self):
        # Should not raise any exception
        path = FFmpegMuxer.get_ffmpeg_path()
        avail = FFmpegMuxer.is_available()
        self.assertEqual(bool(path), avail)

    def test_mux_missing_files(self):
        success, msg = FFmpegMuxer.mux_audio_video("non_existent_v.mp4", "non_existent_a.m4a", "out.mp4")
        self.assertFalse(success)
        self.assertTrue("not found" in msg.lower())

    def test_remux_missing_file(self):
        success, msg = FFmpegMuxer.remux_to_mp4("non_existent.ts", "out.mp4")
        self.assertFalse(success)
        self.assertTrue("not found" in msg.lower())

if __name__ == "__main__":
    unittest.main()
