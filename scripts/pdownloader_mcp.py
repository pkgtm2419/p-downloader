"""
Model Context Protocol (MCP) Server for P-Downloader.
Enables AI assistants (Claude Desktop, Cursor, VS Code) to manage, add, pause,
and observe downloads via JSON-RPC over stdio.
"""
import sys
import json
import os
from typing import Any, Optional, Dict, List

# Add root directory to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from core.db import DownloadDB
from core.engine import DownloadEngine


def send_response(req_id: Any, result: Any = None, error: Any = None):
    resp = {"jsonrpc": "2.0", "id": req_id}
    if error:
        resp["error"] = error
    else:
        resp["result"] = result
    out = json.dumps(resp) + "\n"
    sys.stdout.write(out)
    sys.stdout.flush()


def handle_initialize(req_id: Any):
    send_response(req_id, {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {}
        },
        "serverInfo": {
            "name": "p-downloader-mcp",
            "version": "1.1.0"
        }
    })


def handle_tools_list(req_id: Any):
    tools = [
        {
            "name": "pdl_list_downloads",
            "description": "Lists all current and past downloads in P-Downloader with progress and status.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status_filter": {
                        "type": "string",
                        "description": "Optional status filter: 'downloading', 'paused', 'completed', or 'error'"
                    }
                }
            }
        },
        {
            "name": "pdl_add_download",
            "description": "Adds a new download (HTTP/HTTPS, YouTube/Streaming Video, Magnet, FTP) to P-Downloader.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL or Magnet link to download"},
                    "destination": {"type": "string", "description": "Optional destination file path"},
                    "category": {"type": "string", "description": "Optional category (Video, Music, Documents, etc.)"},
                    "start_now": {"type": "boolean", "description": "Whether to start immediately (default: true)"}
                },
                "required": ["url"]
            }
        },
        {
            "name": "pdl_pause_download",
            "description": "Pauses an active download in P-Downloader.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The task ID to pause"}
                },
                "required": ["task_id"]
            }
        },
        {
            "name": "pdl_resume_download",
            "description": "Resumes a paused download in P-Downloader.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The task ID to resume"}
                },
                "required": ["task_id"]
            }
        },
        {
            "name": "pdl_get_status",
            "description": "Gets overall P-Downloader system health, active speeds, and task counts.",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        }
    ]
    send_response(req_id, {"tools": tools})


def handle_tools_call(req_id: Any, name: str, args: dict, db: DownloadDB, engine: DownloadEngine):
    if name == "pdl_list_downloads":
        all_dls = db.get_all_downloads()
        status_filter = args.get("status_filter")
        if status_filter:
            all_dls = [d for d in all_dls if d.get("status") == status_filter]
        send_response(req_id, {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(all_dls, indent=2)
                }
            ]
        })

    elif name == "pdl_add_download":
        url = args.get("url")
        dest = args.get("destination")
        cat = args.get("category")
        start_now = args.get("start_now", True)

        task = engine.create_download(
            url=url,
            save_path=dest,
            category=cat,
            auto_start=start_now
        )
        send_response(req_id, {
            "content": [
                {
                    "type": "text",
                    "text": f"Successfully created download task {task.task_id} for {task.save_path} (status: {task.status})"
                }
            ]
        })

    elif name == "pdl_pause_download":
        tid = args.get("task_id")
        engine.pause_download(tid)
        send_response(req_id, {
            "content": [{"type": "text", "text": f"Paused download {tid}"}]
        })

    elif name == "pdl_resume_download":
        tid = args.get("task_id")
        engine.resume_download(tid)
        send_response(req_id, {
            "content": [{"type": "text", "text": f"Resumed download {tid}"}]
        })

    elif name == "pdl_get_status":
        dls = db.get_all_downloads()
        active = sum(1 for d in dls if d.get("status") == "downloading")
        completed = sum(1 for d in dls if d.get("status") == "completed")
        paused = sum(1 for d in dls if d.get("status") == "paused")

        info = {
            "active_tasks": active,
            "completed_tasks": completed,
            "paused_tasks": paused,
            "total_tasks": len(dls)
        }
        send_response(req_id, {
            "content": [{"type": "text", "text": json.dumps(info, indent=2)}]
        })
    else:
        send_response(req_id, error={"code": -32601, "message": f"Method not found: {name}"})


def main():
    db = DownloadDB()
    engine = DownloadEngine(db)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        method = req.get("method")
        req_id = req.get("id")

        if method == "initialize":
            handle_initialize(req_id)
        elif method == "tools/list":
            handle_tools_list(req_id)
        elif method == "tools/call":
            params = req.get("params", {})
            handle_tools_call(req_id, params.get("name"), params.get("arguments", {}), db, engine)
        elif method == "ping":
            send_response(req_id, {})
        else:
            send_response(req_id, error={"code": -32601, "message": f"Unknown method: {method}"})


if __name__ == "__main__":
    main()
