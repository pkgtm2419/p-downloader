"""
Unit and integration tests for YouTube single video and playlist functionality.
"""
import unittest
from core.youtube_downloader import (
    is_youtube_url, is_youtube_playlist, extract_clean_youtube_url, probe_youtube,
    YouTubeDownloadTask
)

class TestYouTubePlaylist(unittest.TestCase):
    def test_url_detection(self):
        # Single video URLs
        self.assertTrue(is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertTrue(is_youtube_url("https://youtu.be/dQw4w9WgXcQ"))
        self.assertTrue(is_youtube_url("https://www.youtube.com/shorts/abcdef12345"))
        self.assertTrue(is_youtube_url("https://www.youtube.com/embed/dQw4w9WgXcQ"))
        
        # Playlist URLs
        self.assertTrue(is_youtube_url("https://www.youtube.com/playlist?list=PLrAXtmErZgOdP_8GzEsRv49tON-36365"))
        self.assertTrue(is_youtube_playlist("https://www.youtube.com/playlist?list=PLrAXtmErZgOdP_8GzEsRv49tON-36365"))
        
        # Non-youtube URLs
        self.assertFalse(is_youtube_url("https://example.com/video.mp4"))
        self.assertFalse(is_youtube_playlist("https://example.com/playlist.m3u8"))

    def test_clean_youtube_url_extraction(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=share&t=10"
        clean = extract_clean_youtube_url(url)
        self.assertIn("dQw4w9WgXcQ", clean)

    def test_probe_youtube_offline_fallback(self):
        # Even with an invalid/offline URL, probe_youtube returns a safe descriptor without raising an unhandled exception
        info = probe_youtube("https://www.youtube.com/watch?v=invalid_id_9999", timeout_sec=1)
        self.assertIsInstance(info, dict)
        self.assertIn("filename", info)
        self.assertIn("is_playlist", info)
        self.assertFalse(info["is_playlist"])

    def test_youtube_task_lifecycle(self):
        task = YouTubeDownloadTask(
            task_id="yt123",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            save_path="test_video.mp4"
        )
        self.assertEqual(task.status, "queued")
        task.pause()
        self.assertEqual(task.status, "paused")
        task.cancel()
        self.assertEqual(task.status, "cancelled")

if __name__ == "__main__":
    unittest.main()

