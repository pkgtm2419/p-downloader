"""
Pause and resume integration test for P-Downloader.
Uses an in-process ThreadingHTTPServer with Range header support to ensure fast,
deterministic, and 100% offline-compatible CI testing across all runner environments.
"""
import io
import os
import time
import zipfile
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from core.segment import DownloadTask

class MockRangeHandler(BaseHTTPRequestHandler):
    payload = b""

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(self.payload)))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Disposition", 'attachment; filename="test-archive.zip"')
        self.end_headers()

    def do_GET(self):
        range_header = self.headers.get("Range")
        if range_header and range_header.startswith("bytes="):
            byte_range = range_header.split("=")[1]
            parts = byte_range.split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else len(self.payload) - 1
            if end >= len(self.payload):
                end = len(self.payload) - 1

            chunk = self.payload[start:end + 1]
            self.send_response(206)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(self.payload)}")
            self.send_header("Content-Length", str(len(chunk)))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            self.wfile.write(chunk)
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(self.payload)))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            self.wfile.write(self.payload)

    def log_message(self, format, *args):
        pass  # Suppress request logging during test output


class TestPauseResume(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a valid test zip archive in memory (~256 KB)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("test_file_1.txt", "P-Downloader Test Data" * 2000)
            zf.writestr("test_file_2.bin", os.urandom(150000))
        MockRangeHandler.payload = zip_buffer.getvalue()

        # Start multi-threaded HTTP server on ephemeral port
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MockRangeHandler)
        cls.port = cls.server.server_port
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_pause_and_resume(self):
        url = f"http://127.0.0.1:{self.port}/test-archive.zip"
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "resume-test.zip")

            task = DownloadTask(
                task_id="resumetest",
                url=url,
                save_path=save_path,
                connections=4
            )
            task.prepare()
            self.assertTrue(task.supports_range)
            self.assertEqual(task.total_bytes, len(MockRangeHandler.payload))

            # Start download
            task.start()

            # Wait until some data has been downloaded (or download progresses)
            for _ in range(50):
                if task.downloaded_bytes > 5000 or task.status == "completed":
                    break
                time.sleep(0.05)

            # If not yet completed, pause and verify
            if task.status != "completed":
                task.pause()
                self.assertEqual(task.status, "paused")
                self.assertGreater(task.downloaded_bytes, 0)
                self.assertTrue(os.path.exists(task.meta_file))

                # Resume download
                task.start()

            # Wait for completion
            for _ in range(60):
                if task.status == "completed":
                    break
                time.sleep(0.1)

            self.assertEqual(task.status, "completed")
            self.assertEqual(task.downloaded_bytes, task.total_bytes)
            self.assertFalse(os.path.exists(task.meta_file))

            # Verify downloaded archive integrity
            with zipfile.ZipFile(save_path, "r") as zf:
                bad = zf.testzip()
                self.assertIsNone(bad)
                self.assertEqual(len(zf.namelist()), 2)


if __name__ == "__main__":
    unittest.main()
