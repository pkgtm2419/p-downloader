import unittest
from core.youtube_downloader import is_youtube_url, extract_clean_youtube_url, YouTubeDownloadTask


class TestYouTubeDownloader(unittest.TestCase):
    def test_is_youtube_url(self):
        self.assertTrue(is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertTrue(is_youtube_url("https://youtu.be/dQw4w9WgXcQ"))
        self.assertTrue(is_youtube_url("https://www.youtube.com/shorts/abcdefghijk"))
        self.assertTrue(is_youtube_url("https://rr1---sn-4g5edn6r.googlevideo.com/videoplayback?id=123"))
        self.assertFalse(is_youtube_url("https://example.com/video.mp4"))
        self.assertFalse(is_youtube_url(""))

    def test_extract_clean_youtube_url(self):
        url = "https://rr1---sn-4g5edn6r.googlevideo.com/videoplayback?expire=123&id=dQw4w9WgXcQ&itag=18"
        clean = extract_clean_youtube_url(url, page_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(clean, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_task_init(self):
        task = YouTubeDownloadTask(
            task_id="yt01",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            save_path="Downloads/test.mp4",
            quality="1080p"
        )
        self.assertEqual(task.status, "queued")
        self.assertEqual(task.quality, "1080p")
        self.assertTrue(task.supports_range)


if __name__ == "__main__":
    unittest.main()
