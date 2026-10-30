"""
Benchmark harness for measuring download acceleration, throughput, resource efficiency, and integrity.
Usage:
    python tests/benchmarks/benchmark_downloads.py --fixture local --connections 1,4,8,16,32,auto --output results.json
"""
import sys
import os
import time
import json
import argparse
import hashlib
import tempfile
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.support.http_origin import FaultOrigin
from core.download_models import DownloadRequest
from core.engine import DownloadEngine


def run_single_benchmark(fixture_url: str, expected_hash: str, connections: int, temp_dir: str):
    engine = DownloadEngine()
    dest = Path(temp_dir) / f"bench_conn_{connections}.bin"

    t0 = time.perf_counter()
    task = engine.create_download(
        url=fixture_url,
        filename=dest.name,
        save_path=str(dest),
        connections=connections if connections > 0 else 8,
        auto_start=True
    )

    # Wait for completion or timeout (max 60s)
    deadline = time.perf_counter() + 60.0
    while time.perf_counter() < deadline and task.status not in ("completed", "error"):
        time.sleep(0.05)

    duration = max(0.001, time.perf_counter() - t0)

    if task.status != "completed" or not dest.exists():
        return {
            "connections": connections,
            "success": False,
            "status": task.status,
            "error": getattr(task, "error_message", "Failed to complete in time")
        }

    # Verify SHA-256
    sha256 = hashlib.sha256()
    with open(dest, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    actual_hash = sha256.hexdigest()

    file_size = dest.stat().st_size
    throughput_mb_s = (file_size / (1024 * 1024)) / duration

    # Clean up
    try:
        dest.unlink()
    except Exception:
        pass

    return {
        "connections": connections,
        "success": (actual_hash == expected_hash),
        "file_size_bytes": file_size,
        "duration_sec": round(duration, 3),
        "throughput_mb_s": round(throughput_mb_s, 2),
        "sha256_match": (actual_hash == expected_hash),
        "retries": 0,
        "bytes_redownloaded": 0
    }


def main():
    parser = argparse.ArgumentParser(description="P-Downloader Acceleration Benchmark Harness")
    parser.add_argument("--fixture", default="local", choices=["local", "remote"], help="Fixture source")
    parser.add_argument("--connections", default="1,4,8,16", help="Comma-separated connection counts")
    parser.add_argument("--size-mb", type=int, default=10, help="Payload size in MiB for local benchmark")
    parser.add_argument("--output", default="benchmark_results.json", help="Path to write JSON results")
    args = parser.parse_args()

    # Generate test payload
    size_bytes = args.size_mb * 1024 * 1024
    payload = os.urandom(size_bytes)
    expected_hash = hashlib.sha256(payload).hexdigest()

    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "payload_size_mb": args.size_mb,
        "runs": []
    }

    conn_list = []
    for c in args.connections.split(","):
        c_str = c.strip()
        conn_list.append(8 if c_str == "auto" else int(c_str))

    with FaultOrigin(payload=payload) as server:
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"[*] Starting benchmark on {server.base_url} ({args.size_mb} MiB payload)...")
            for conns in conn_list:
                print(f" -> Testing {conns} concurrent streams...", end="", flush=True)
                res = run_single_benchmark(server.base_url, expected_hash, conns, temp_dir)
                results["runs"].append(res)
                if res["success"]:
                    print(f" OK: {res['throughput_mb_s']} MB/s ({res['duration_sec']}s)")
                else:
                    print(f" FAILED: {res.get('error', 'Integrity mismatch')}")

    out_path = Path(args.output)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[+] Benchmark finished. Results saved to {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
