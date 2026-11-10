"""
Unit and integration tests for Phase 4:
Web Remote server, Local IPC server, IDM CLI normalization, and MCP JSON-RPC protocol.
"""
import os
import sys
import json
import time
import socket
import unittest
import urllib.request
from unittest.mock import MagicMock

from main import normalize_idm_args
from core.db import DownloadDB
from core.engine import DownloadEngine
from core.remote_server import RemoteServer
from core.ipc import LocalIPCServer, request_from_running_instance
import scripts.pdownloader_mcp as mcp


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class TestRemoteAndMCP(unittest.TestCase):
    def setUp(self):
        self.db = DownloadDB(":memory:")
        self.engine = DownloadEngine(self.db)

    def tearDown(self):
        try:
            self.db.close()
        except Exception:
            pass

    def test_idm_cli_normalization(self):
        args = ["/d", "https://example.com/file.zip", "/p", "C:\\Downloads", "/f", "file.zip", "/n", "/q", "/s", "/a", "/h"]
        normalized = normalize_idm_args(args)
        expected = [
            "--url", "https://example.com/file.zip",
            "--output-dir", "C:\\Downloads",
            "--filename", "file.zip",
            "--silent",
            "--quit-on-finish",
            "--start-queue",
            "--queue-only",
            "--hangup"
        ]
        self.assertEqual(normalized, expected)

    def test_idm_cli_case_insensitivity(self):
        args = ["/D", "https://example.com/video.mp4", "/P", "D:\\Videos", "/F", "vid.mp4", "/N"]
        normalized = normalize_idm_args(args)
        self.assertEqual(normalized, [
            "--url", "https://example.com/video.mp4",
            "--output-dir", "D:\\Videos",
            "--filename", "vid.mp4",
            "--silent"
        ])

    def test_local_ipc_server(self):
        port = get_free_port()
        ipc = LocalIPCServer(self.engine, host="127.0.0.1", port=port)
        started = ipc.start()
        self.assertTrue(started, "LocalIPCServer failed to start")

        try:
            # 1. Add download via IPC
            res = request_from_running_instance(
                {"action": "download", "url": "https://example.com/data.bin", "startNow": False},
                port=port
            )
            self.assertIsNotNone(res)
            self.assertTrue(res.get("ok"))
            task_id = res.get("taskId")
            self.assertTrue(task_id)

            # 2. Check status via IPC
            res_status = request_from_running_instance(
                {"action": "status", "taskId": task_id},
                port=port
            )
            self.assertIsNotNone(res_status)
            self.assertTrue(res_status.get("ok"))
            self.assertEqual(res_status.get("taskId"), task_id)
        finally:
            ipc.stop()

    def test_remote_server_rest_and_html(self):
        port = get_free_port()
        server = RemoteServer(engine=self.engine, host="127.0.0.1", port=port, use_tls=False)
        server.start()
        time.sleep(0.1)

        try:
            # 1. Test GET HTML dashboard
            req = urllib.request.Request(f"http://127.0.0.1:{port}/")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                self.assertEqual(resp.status, 200)
                html = resp.read().decode("utf-8")
                self.assertIn("P-Downloader Remote", html)

            # 2. Test GET /api/downloads
            req_api = urllib.request.Request(f"http://127.0.0.1:{port}/api/downloads")
            with urllib.request.urlopen(req_api, timeout=2.0) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertIsInstance(data, list)

            # 3. Test POST /api/download/add
            post_body = json.dumps({"url": "https://example.com/test.zip"}).encode("utf-8")
            req_post = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/download/add",
                data=post_body,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req_post, timeout=2.0) as resp:
                self.assertEqual(resp.status, 200)
                res_json = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(res_json.get("ok"))
                self.assertTrue("task_id" in res_json)
        finally:
            server.stop()

    def test_mcp_tools_and_rpc(self):
        # Test tools list handler
        saved_stdout = sys.stdout
        from io import StringIO
        buf = StringIO()
        sys.stdout = buf

        try:
            mcp.handle_initialize(1)
            init_out = json.loads(buf.getvalue().strip())
            self.assertEqual(init_out.get("id"), 1)
            self.assertEqual(init_out["result"]["serverInfo"]["name"], "p-downloader-mcp")

            buf.truncate(0)
            buf.seek(0)
            mcp.handle_tools_list(2)
            tools_out = json.loads(buf.getvalue().strip())
            tool_names = [t["name"] for t in tools_out["result"]["tools"]]
            self.assertIn("pdl_list_downloads", tool_names)
            self.assertIn("pdl_add_download", tool_names)
            self.assertIn("pdl_get_status", tool_names)

            buf.truncate(0)
            buf.seek(0)
            mcp.handle_tools_call(3, "pdl_get_status", {}, self.db, self.engine)
            status_out = json.loads(buf.getvalue().strip())
            self.assertEqual(status_out.get("id"), 3)
            self.assertTrue("content" in status_out["result"])
        finally:
            sys.stdout = saved_stdout


if __name__ == "__main__":
    unittest.main()
