"""
Unit tests for length-framed authenticated IPC protocol.
"""
import time
import unittest
from core.ipc import IPCServer, request_from_running_instance, get_or_create_ipc_token

class TestIPCProtocol(unittest.TestCase):
    def test_framed_request_response_roundtrip(self):
        """IPCServer processes framed request and returns framed response."""
        def handler(msg):
            action = msg.get("action")
            if action == "test_echo":
                return {"ok": True, "echo": msg.get("data")}
            return {"ok": False, "error": "unknown"}

        server = IPCServer(handler)
        self.assertTrue(server.start())

        try:
            req = {"action": "test_echo", "data": "hello_pdownloader"}
            resp = request_from_running_instance(req, timeout=2.0)
            self.assertIsNotNone(resp)
            self.assertTrue(resp.get("ok"))
            self.assertEqual(resp.get("echo"), "hello_pdownloader")
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
