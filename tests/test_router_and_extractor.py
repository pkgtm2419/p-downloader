"""
Tests for Intelligent Router, Universal Media Extractor, and Extractor Updater (Phase 1).
"""
import unittest
from unittest.mock import MagicMock, patch
from core.download_models import DownloadKind
from core.router import classify_target, is_streaming_site
from core.extractor import (
    is_media_url,
    extract_canonical_media_url,
    get_selectable_video_formats,
    probe_media,
    UniversalMediaTask
)
from core.updater_ytdlp import check_for_ytdlp_updates


class TestRouterAndExtractor(unittest.TestCase):
    def test_router_classification(self):
        # 1. Torrents
        self.assertEqual(classify_target("magnet:?xt=urn:btih:abcdef"), DownloadKind.TORRENT)
        self.assertEqual(classify_target("https://example.com/archlinux.torrent"), DownloadKind.TORRENT)
        self.assertEqual(classify_target("https://example.com/get", content_type="application/x-bittorrent"), DownloadKind.TORRENT)

        # 2. FTP
        self.assertEqual(classify_target("ftp://ftp.freebsd.org/pub/releases.iso"), DownloadKind.FTP)
        self.assertEqual(classify_target("ftps://secure.ftp.org/data.zip"), DownloadKind.FTP)

        # 3. HLS
        self.assertEqual(classify_target("https://stream.provider.com/live/master.m3u8"), DownloadKind.HLS)
        self.assertEqual(classify_target("https://stream.provider.com/playlist", content_type="application/x-mpegURL"), DownloadKind.HLS)

        # 4. DASH
        self.assertEqual(classify_target("https://dash.edgesuite.net/envivio/dash.mpd"), DownloadKind.DASH)
        self.assertEqual(classify_target("https://video.com/manifest", content_type="application/dash+xml"), DownloadKind.DASH)

        # 5. Streaming Sites (Universal Media)
        self.assertEqual(classify_target("https://vimeo.com/123456789"), DownloadKind.MEDIA)
        self.assertEqual(classify_target("https://twitter.com/user/status/987654321"), DownloadKind.MEDIA)
        self.assertEqual(classify_target("https://www.reddit.com/r/videos/comments/xyz/cool_clip/"), DownloadKind.MEDIA)
        self.assertEqual(classify_target("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), DownloadKind.MEDIA)
        self.assertEqual(classify_target("https://www.twitch.tv/videos/12345"), DownloadKind.MEDIA)

        # 6. Direct Binary Downloads
        self.assertEqual(classify_target("https://releases.ubuntu.com/22.04/ubuntu.iso"), DownloadKind.HTTP)
        self.assertEqual(classify_target("https://github.com/project/releases/archive.zip"), DownloadKind.HTTP)
        self.assertEqual(classify_target("https://cdn.site.com/get_file", content_type="application/octet-stream"), DownloadKind.HTTP)

    def test_is_media_url_and_canonical_url(self):
        self.assertTrue(is_media_url("https://vimeo.com/76979871"))
        self.assertTrue(is_media_url("https://v.redd.it/abcdef123"))
        self.assertTrue(is_media_url("https://tiktok.com/@user/video/123"))
        self.assertFalse(is_media_url("https://files.pythonhosted.org/packages/package.tar.gz"))

        # Radio mix url cleaning
        clean_yt = extract_canonical_media_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=RDMM")
        self.assertEqual(clean_yt, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_selectable_video_formats(self):
        raw_formats = [
            {"format_id": "137", "ext": "mp4", "height": 1080, "vcodec": "avc1", "acodec": "none", "filesize": 50000000},
            {"format_id": "136", "ext": "mp4", "height": 720, "vcodec": "avc1", "acodec": "none", "filesize": 25000000},
            {"format_id": "140", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2", "filesize": 5000000}
        ]

        choices = get_selectable_video_formats(raw_formats, default_filesize=55000000)
        self.assertTrue(len(choices) >= 3)
        resolutions = [c["resolution"] for c in choices]
        self.assertIn("1080p", resolutions)
        self.assertIn("720p", resolutions)
        self.assertIn("Audio Only", resolutions)

    @patch("core.extractor.yt_dlp.YoutubeDL")
    def test_probe_media_drm_detection(self, mock_ydl_cls):
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.side_effect = Exception("ERROR: DRM protected stream (Widevine required)")

        with self.assertRaises(RuntimeError) as ctx:
            probe_media("https://protected.streaming.com/watch?id=123")
        self.assertIn("DRM-protected", str(ctx.exception))

    def test_updater_version_check(self):
        with patch("core.updater_ytdlp.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "tag_name": "2026.12.31",
                "html_url": "https://github.com/yt-dlp/yt-dlp/releases/tag/2026.12.31"
            }
            mock_get.return_value = mock_resp

            res = check_for_ytdlp_updates()
            self.assertEqual(res["latest_version"], "2026.12.31")


if __name__ == "__main__":
    unittest.main()
