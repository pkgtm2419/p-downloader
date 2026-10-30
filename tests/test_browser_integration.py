"""
Integration tests for end-to-end browser handoff acknowledgment and IPC.
"""
import os
import tempfile
import unittest
from core.db import DownloadDB, init_db
from core.engine import DownloadEngine
from core.browser_handoff import HandoffStore
from core.download_models import DownloadRequest, DownloadKind
from core.ipc import IPCServer, request_from_running_instance

class TestBrowserIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_integration.db")
        self.db = DownloadDB(self.db_path)
        self.engine = DownloadEngine(self.db)
        self.handoff_store = HandoffStore(self.db.conn)

        def ipc_handler(msg: dict):
            action = msg.get("action")
            url = msg.get("url")
            if action == "reserve" and url:
                req = DownloadRequest(
                    url=url,
                    filename=msg.get("filename"),
                    destination=msg.get("destination"),
                    kind=DownloadKind.HTTP
                )
                offer = self.handoff_store.reserve(req, capture_id=msg.get("captureId"))
                return {
                    "ok": True,
                    "state": offer.state,
                    "handoffId": offer.handoff_id,
                    "expiresAt": offer.expires_at_utc
                }
            elif action == "commit":
                hid = msg.get("handoffId")
                tid = self.handoff_store.commit(hid, engine=self.engine)
                return {"ok": True, "state": "COMMITTED", "taskId": tid}
            elif action == "status":
                hid = msg.get("handoffId")
                offer = self.handoff_store.get_status(hid)
                if offer:
                    return {"ok": True, "state": offer.state, "taskId": offer.task_id}
                return {"ok": False, "error": "NOT_FOUND"}
            return {"ok": False, "error": "unknown"}

        self.ipc_server = IPCServer(ipc_handler)
        self.assertTrue(self.ipc_server.start())

    def tearDown(self):
        self.ipc_server.stop()
        self.db.close()
        self.temp_dir.cleanup()

    def test_end_to_end_reserve_and_commit_flow(self):
        """Simulate browser extension reserving and committing download ownership."""
        # 1. RESERVE request
        reserve_req = {
            "action": "reserve",
            "captureId": "cap_e2e_001",
            "url": "https://example.com/asset.zip",
            "filename": "asset.zip"
        }
        res1 = request_from_running_instance(reserve_req, timeout=2.0)
        self.assertIsNotNone(res1)
        self.assertTrue(res1.get("ok"))
        self.assertEqual(res1.get("state"), "PREPARED")
        handoff_id = res1.get("handoffId")
        self.assertTrue(handoff_id)

        # 2. COMMIT request
        commit_req = {
            "action": "commit",
            "handoffId": handoff_id
        }
        res2 = request_from_running_instance(commit_req, timeout=2.0)
        self.assertIsNotNone(res2)
        self.assertTrue(res2.get("ok"))
        self.assertEqual(res2.get("state"), "COMMITTED")
        task_id = res2.get("taskId")
        self.assertTrue(task_id)

        # 3. Idempotent commit repeat
        res3 = request_from_running_instance(commit_req, timeout=2.0)
        self.assertEqual(res3.get("taskId"), task_id)

        # 4. STATUS check
        status_req = {
            "action": "status",
            "handoffId": handoff_id
        }
        res4 = request_from_running_instance(status_req, timeout=2.0)
        self.assertEqual(res4.get("state"), "COMMITTED")
        self.assertEqual(res4.get("taskId"), task_id)


if __name__ == "__main__":
    unittest.main()
