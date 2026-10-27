"""
HLS (HTTP Live Streaming) .m3u8 Downloader Engine for P-Downloader.
Parses master and media playlists, downloads segments in parallel using thread pools,
handles AES-128 decryption if needed, and joins segments into playable media (.mp4 / .ts).
"""
import os
import re
import time
import shutil
import tempfile
import threading
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable, Tuple
import requests

from core.muxer import FFmpegMuxer

class HLSParser:
    """
    Parses HLS .m3u8 master and media playlists.
    """
    @staticmethod
    def is_master_playlist(content: str) -> bool:
        return "#EXT-X-STREAM-INF" in content

    @staticmethod
    def parse_master_playlist(content: str, base_url: str) -> List[Dict[str, Any]]:
        """
        Parses master playlist into available stream variants.
        Returns list of dicts with: resolution, bandwidth, codecs, url.
        """
        variants = []
        lines = [line.strip() for line in content.splitlines() if line.strip()]

        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF:"):
                info = line[len("#EXT-X-STREAM-INF:"):]
                bandwidth = 0
                resolution = "Unknown"
                codecs = ""

                bw_match = re.search(r'BANDWIDTH=(\d+)', info)
                if bw_match:
                    bandwidth = int(bw_match.group(1))

                res_match = re.search(r'RESOLUTION=(\d+x\d+)', info)
                if res_match:
                    resolution = res_match.group(1)

                codec_match = re.search(r'CODECS="([^"]+)"', info)
                if codec_match:
                    codecs = codec_match.group(1)

                # Next line is the URL
                if i + 1 < len(lines) and not lines[i + 1].startswith("#"):
                    stream_url = urljoin(base_url, lines[i + 1])
                    variants.append({
                        "resolution": resolution,
                        "bandwidth": bandwidth,
                        "codecs": codecs,
                        "url": stream_url
                    })

        # Sort variants by bandwidth descending (highest quality first)
        variants.sort(key=lambda x: x["bandwidth"], reverse=True)
        return variants

    @staticmethod
    def parse_media_playlist(content: str, base_url: str) -> Dict[str, Any]:
        """
        Parses media playlist segments, duration, and encryption keys.
        """
        segments = []
        key_info = None
        total_duration = 0.0

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        current_duration = 0.0

        for line in lines:
            if line.startswith("#EXT-X-KEY:"):
                # Parse encryption key: METHOD=AES-128,URI="...",IV=0x...
                method_match = re.search(r'METHOD=([^,\s]+)', line)
                uri_match = re.search(r'URI="([^"]+)"', line)
                iv_match = re.search(r'IV=([^,\s]+)', line)

                method = method_match.group(1) if method_match else "NONE"
                key_url = urljoin(base_url, uri_match.group(1)) if uri_match else ""
                iv_val = iv_match.group(1) if iv_match else None

                key_info = {
                    "method": method,
                    "url": key_url,
                    "iv": iv_val
                }

            elif line.startswith("#EXTINF:"):
                dur_match = re.search(r'#EXTINF:([\d.]+)', line)
                if dur_match:
                    current_duration = float(dur_match.group(1))

            elif not line.startswith("#"):
                seg_url = urljoin(base_url, line)
                segments.append({
                    "url": seg_url,
                    "duration": current_duration,
                    "key_info": key_info
                })
                total_duration += current_duration
                current_duration = 0.0

        return {
            "segments": segments,
            "total_duration": total_duration,
            "segment_count": len(segments),
            "key_info": key_info
        }


class HLSDownloader:
    """
    Downloads an HLS stream to a local video file.
    """
    def __init__(
        self,
        m3u8_url: str,
        save_path: str,
        max_workers: int = 8,
        headers: Optional[Dict[str, str]] = None
    ):
        self.m3u8_url = m3u8_url
        self.save_path = save_path
        self.max_workers = max_workers
        self.headers = headers or {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        self.status = "idle" # idle, fetching, downloading, merging, completed, error, paused, cancelled
        self.error_message = ""
        self.total_segments = 0
        self.downloaded_segments = 0
        self.total_bytes = 0
        self.downloaded_bytes = 0
        self.speed = 0.0

        self.is_paused = False
        self.is_cancelled = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []

    def add_callback(self, cb: Callable[[Dict[str, Any]], None]):
        self._callbacks.append(cb)

    def _notify(self):
        state = {
            "status": self.status,
            "total_segments": self.total_segments,
            "downloaded_segments": self.downloaded_segments,
            "downloaded_bytes": self.downloaded_bytes,
            "speed": self.speed,
            "error_message": self.error_message,
            "save_path": self.save_path
        }
        for cb in self._callbacks:
            try:
                cb(state)
            except Exception:
                pass

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self.is_paused = False
        self.is_cancelled = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def pause(self):
        self.is_paused = True
        self.status = "paused"
        self._notify()

    def cancel(self):
        self.is_cancelled = True
        self.status = "cancelled"
        self._notify()

    def _run(self):
        temp_dir = tempfile.mkdtemp(prefix="pdl_hls_")
        try:
            self.status = "fetching"
            self._notify()

            session = requests.Session()
            session.headers.update(self.headers)

            resp = session.get(self.m3u8_url, timeout=15)
            resp.raise_for_status()
            content = resp.text

            target_m3u8 = self.m3u8_url
            # If master playlist, select highest quality variant
            if HLSParser.is_master_playlist(content):
                variants = HLSParser.parse_master_playlist(content, self.m3u8_url)
                if not variants:
                    raise ValueError("No video stream variants found in master playlist.")
                target_m3u8 = variants[0]["url"]
                resp = session.get(target_m3u8, timeout=15)
                resp.raise_for_status()
                content = resp.text

            # Parse media playlist
            playlist = HLSParser.parse_media_playlist(content, target_m3u8)
            segments = playlist["segments"]
            if not segments:
                raise ValueError("No media segments found in stream.")

            self.total_segments = len(segments)
            self.status = "downloading"
            self._notify()

            # Pre-fetch encryption key if present
            aes_key = None
            if playlist.get("key_info") and playlist["key_info"]["method"] == "AES-128":
                key_url = playlist["key_info"]["url"]
                if key_url:
                    key_resp = session.get(key_url, timeout=15)
                    key_resp.raise_for_status()
                    aes_key = key_resp.content

            # Download worker function
            segment_files: List[Optional[str]] = [None] * len(segments)
            bytes_lock = threading.Lock()
            last_time = time.time()
            bytes_since_last = 0

            def download_segment(index: int, seg_info: Dict[str, Any]):
                if self.is_cancelled or self.is_paused:
                    return None
                seg_url = seg_info["url"]
                seg_path = os.path.join(temp_dir, f"seg_{index:06d}.ts")

                for attempt in range(3):
                    try:
                        r = session.get(seg_url, timeout=12)
                        r.raise_for_status()
                        data = r.content

                        # Optional AES-128 decryption
                        if aes_key:
                            try:
                                from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
                                from cryptography.hazmat.backends import default_backend
                                iv = seg_info["key_info"].get("iv")
                                if iv:
                                    iv_bytes = bytes.fromhex(iv.replace("0x", "").zfill(32))
                                else:
                                    iv_bytes = index.to_bytes(16, byteorder="big")
                                cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv_bytes), backend=default_backend())
                                decryptor = cipher.decryptor()
                                data = decryptor.update(data) + decryptor.finalize()
                            except ImportError:
                                # cryptography not installed, write raw data
                                pass

                        with open(seg_path, "wb") as f:
                            f.write(data)

                        with bytes_lock:
                            nonlocal bytes_since_last, last_time
                            seg_len = len(data)
                            self.downloaded_bytes += seg_len
                            self.downloaded_segments += 1
                            bytes_since_last += seg_len

                            now = time.time()
                            dt = now - last_time
                            if dt >= 0.5:
                                self.speed = bytes_since_last / dt
                                bytes_since_last = 0
                                last_time = now
                                self._notify()

                        return index, seg_path

                    except Exception:
                        if attempt == 2:
                            raise
                        time.sleep(0.5)

                return None

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(download_segment, i, seg): i for i, seg in enumerate(segments)}
                for future in as_completed(futures):
                    if self.is_cancelled:
                        break
                    idx, path = future.result()
                    if path:
                        segment_files[idx] = path

            if self.is_cancelled:
                self.status = "cancelled"
                self._notify()
                return

            # Merging segments into final file
            self.status = "merging"
            self.speed = 0.0
            self._notify()

            os.makedirs(os.path.dirname(os.path.abspath(self.save_path)), exist_ok=True)
            merged_ts = os.path.join(temp_dir, "combined.ts")

            with open(merged_ts, "wb") as outfile:
                for seg_path in segment_files:
                    if seg_path and os.path.isfile(seg_path):
                        with open(seg_path, "rb") as infile:
                            shutil.copyfileobj(infile, outfile, 64 * 1024)

            # If output is .mp4 and FFmpeg is available, remux to MP4 for maximum compatibility
            if self.save_path.lower().endswith(".mp4") and FFmpegMuxer.is_available():
                ok, msg = FFmpegMuxer.remux_to_mp4(merged_ts, self.save_path)
                if not ok:
                    # Fallback to direct copy
                    shutil.copyfile(merged_ts, self.save_path)
            else:
                shutil.copyfile(merged_ts, self.save_path)

            self.status = "completed"
            self._notify()

        except Exception as e:
            self.status = "error"
            self.error_message = str(e)
            self._notify()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

class HLSDownloadTask:
    """
    Adapter implementing the DownloadTask interface for HLS streams,
    allowing unified management within DownloadEngine and GUI views.
    """
    def __init__(
        self,
        task_id: str,
        url: str,
        save_path: str,
        connections: int = 8,
        speed_limit: int = 0,
        on_progress: Optional[Callable[['HLSDownloadTask'], None]] = None,
        on_complete: Optional[Callable[['HLSDownloadTask'], None]] = None,
        on_error: Optional[Callable[['HLSDownloadTask', str], None]] = None
    ):
        self.task_id = task_id
        self.url = url
        self.save_path = save_path
        self.connections = connections
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error

        self.total_bytes = 0
        self.downloaded_bytes = 0
        self.supports_range = True
        self.segments = []
        self.status = "queued"
        self.speed = 0.0
        self.error_message = ""
        self.is_hls = True

        self.downloader = HLSDownloader(url, save_path, max_workers=connections)
        self.downloader.add_callback(self._on_hls_state)

    def prepare(self):
        # Ready to download
        self.status = "queued"

    def start(self):
        self.status = "downloading"
        self.downloader.start()

    def pause(self):
        self.status = "paused"
        self.downloader.pause()

    def resume(self):
        self.status = "downloading"
        self.downloader.start()

    def cancel(self):
        self.status = "cancelled"
        self.downloader.cancel()

    def set_speed_limit(self, limit: int):
        pass

    def _on_hls_state(self, state: Dict[str, Any]):
        self.downloaded_bytes = state.get("downloaded_bytes", 0)
        self.speed = state.get("speed", 0.0)
        st = state.get("status", "")

        if st == "completed":
            self.status = "completed"
            if self.on_complete:
                self.on_complete(self)
        elif st == "error":
            self.status = "error"
            self.error_message = state.get("error_message", "HLS stream download failed")
            if self.on_error:
                self.on_error(self, self.error_message)
        elif st in ("downloading", "merging", "fetching"):
            self.status = "downloading"
            if self.on_progress:
                self.on_progress(self)

