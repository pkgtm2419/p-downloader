import http.server
import os
import socketserver
import tempfile
import threading
import time
import unittest

from core.hls.fetch import HLSDownloader
from core.hls.parser import HLSParser


class LiveStreamMockHandler(http.server.SimpleHTTPRequestHandler):
    poll_count = 0

    def do_GET(self):
        if self.path == "/live.m3u8":
            LiveStreamMockHandler.poll_count += 1
            if LiveStreamMockHandler.poll_count == 1:
                # First poll: segments 0 and 1
                playlist = (
                    "#EXTM3U\n"
                    "#EXT-X-VERSION:3\n"
                    "#EXT-X-TARGETDURATION:2\n"
                    "#EXT-X-MEDIA-SEQUENCE:0\n"
                    "#EXTINF:2.0,\n"
                    "seg_0.ts\n"
                    "#EXTINF:2.0,\n"
                    "seg_1.ts\n"
                )
            elif LiveStreamMockHandler.poll_count == 2:
                # Second poll: sliding window has segments 1 and 2
                playlist = (
                    "#EXTM3U\n"
                    "#EXT-X-VERSION:3\n"
                    "#EXT-X-TARGETDURATION:2\n"
                    "#EXT-X-MEDIA-SEQUENCE:1\n"
                    "#EXTINF:2.0,\n"
                    "seg_1.ts\n"
                    "#EXTINF:2.0,\n"
                    "seg_2.ts\n"
                )
            else:
                # Final poll: add #EXT-X-ENDLIST
                playlist = (
                    "#EXTM3U\n"
                    "#EXT-X-VERSION:3\n"
                    "#EXT-X-TARGETDURATION:2\n"
                    "#EXT-X-MEDIA-SEQUENCE:2\n"
                    "#EXTINF:2.0,\n"
                    "seg_2.ts\n"
                    "#EXTINF:2.0,\n"
                    "seg_3.ts\n"
                    "#EXT-X-ENDLIST\n"
                )
            body = playlist.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.apple.mpegurl")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path.startswith("/seg_") and self.path.endswith(".ts"):
            # Return identifiable 188-byte chunk per segment
            seg_num = self.path[len("/seg_"):-len(".ts")]
            content = f"SEGMENT_{seg_num}".encode("utf-8").ljust(188, b"X")
            self.send_response(200)
            self.send_header("Content-Type", "video/mp2t")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Quiet logging


class TestHLSLiveStreamRecording(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        LiveStreamMockHandler.poll_count = 0
        cls.server = socketserver.TCPServer(("127.0.0.1", 0), LiveStreamMockHandler)
        cls.port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        LiveStreamMockHandler.poll_count = 0

    def test_live_stream_polling_and_endlist(self):
        with tempfile.TemporaryDirectory() as td:
            out_file = os.path.join(td, "live_recording.ts")
            url = f"http://127.0.0.1:{self.port}/live.m3u8"

            downloader = HLSDownloader(m3u8_url=url, save_path=out_file)
            downloader.start()

            # Wait for completion (polls 1, 2, 3 until ENDLIST)
            for _ in range(60):
                if downloader.status in ("completed", "error"):
                    break
                time.sleep(0.2)

            self.assertEqual(downloader.status, "completed")
            self.assertTrue(os.path.isfile(out_file))
            self.assertGreater(os.path.getsize(out_file), 0)

            # Check that segments were captured in order
            with open(out_file, "rb") as f:
                data = f.read()
            self.assertIn(b"SEGMENT_0", data)
            self.assertIn(b"SEGMENT_1", data)
            self.assertIn(b"SEGMENT_2", data)
            self.assertIn(b"SEGMENT_3", data)

    def test_live_stream_manual_stop(self):
        LiveStreamMockHandler.poll_count = 0
        with tempfile.TemporaryDirectory() as td:
            out_file = os.path.join(td, "live_stopped.ts")
            url = f"http://127.0.0.1:{self.port}/live.m3u8"

            downloader = HLSDownloader(m3u8_url=url, save_path=out_file)
            downloader.start()

            # Let it record at least 1 segment
            for _ in range(30):
                if downloader.downloaded_segments >= 1:
                    break
                time.sleep(0.1)

            # Stop live recording gracefully
            downloader.stop_live()

            for _ in range(30):
                if downloader.status == "completed":
                    break
                time.sleep(0.1)

            self.assertEqual(downloader.status, "completed")
            self.assertTrue(os.path.isfile(out_file))
            self.assertGreater(os.path.getsize(out_file), 0)


if __name__ == "__main__":
    unittest.main()
