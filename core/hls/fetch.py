"""
HLS Downloader Engine (IM-01).
Coordinates multi-threaded segment downloads, fMP4 init maps,
AES-128 key rotation, audio rendition muxing, and cooperative pause/cancel.
"""
import os
import time
import shutil
import tempfile
import threading
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable

import requests
from .parser import HLSParser
from .keys import HLSKeyManager
from .merge import merge_segments, mux_audio_video
from core.errors import AppError, ErrorCode


class HLSDownloader:
    def __init__(
        self,
        m3u8_url: str,
        save_path: str,
        max_workers: int = 8,
        headers: Optional[Dict[str, str]] = None,
        chosen_variant_url: Optional[str] = None
    ):
        self.m3u8_url = m3u8_url
        self.save_path = save_path
        self.max_workers = max_workers
        self.headers = headers or {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        self.chosen_variant_url = chosen_variant_url

        self.status = "idle"  # idle, fetching, downloading, merging, completed, error, paused, cancelled
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
            try:
                from core.db import DownloadDB
                proxies = DownloadDB().get_proxy_config()
                if proxies:
                    session.proxies.update(proxies)
            except Exception:
                pass

            resp = session.get(self.m3u8_url, timeout=15)
            resp.raise_for_status()
            content = resp.text

            target_m3u8 = self.chosen_variant_url or self.m3u8_url
            audio_m3u8_url = None

            # 1. Master playlist variant resolution
            if HLSParser.is_master_playlist(content):
                master_info = HLSParser.parse_master_playlist(content, self.m3u8_url)
                variants = master_info["variants"]
                if not variants:
                    raise AppError(ErrorCode.NO_MEDIA_FOUND, "No video stream variants found in master playlist.")

                selected_variant = variants[0]
                if self.chosen_variant_url:
                    for v in variants:
                        if v["url"] == self.chosen_variant_url:
                            selected_variant = v
                            break

                target_m3u8 = selected_variant["url"]

                # Check if variant requires separate audio rendition
                audio_gid = selected_variant.get("audio_group_id")
                if audio_gid and audio_gid in master_info.get("audio_groups", {}):
                    audio_tracks = master_info["audio_groups"][audio_gid]
                    if audio_tracks:
                        # Pick default or first audio track
                        audio_m3u8_url = audio_tracks[0]["url"]
                        for at in audio_tracks:
                            if at.get("is_default"):
                                audio_m3u8_url = at["url"]
                                break

                resp = session.get(target_m3u8, timeout=15)
                resp.raise_for_status()
                content = resp.text

            # 2. Parse main video media playlist
            playlist = HLSParser.parse_media_playlist(content, target_m3u8)
            segments = playlist["segments"]
            if not segments:
                raise AppError(ErrorCode.NO_MEDIA_FOUND, "No media segments found in stream.")

            self.total_segments = len(segments)
            self.status = "downloading"
            self._notify()

            key_mgr = HLSKeyManager(session)

            # 3. Download fMP4 initialization map if present (#EXT-X-MAP)
            init_map_path = None
            if playlist.get("init_map_url"):
                init_url = playlist["init_map_url"]
                init_resp = session.get(init_url, timeout=15)
                init_resp.raise_for_status()
                init_map_path = os.path.join(temp_dir, "init.mp4")
                with open(init_map_path, "wb") as f:
                    f.write(init_resp.content)

            # 4. Multi-threaded segment download worker
            segment_files: List[Optional[str]] = [None] * len(segments)
            bytes_lock = threading.Lock()
            last_time = time.time()
            bytes_since_last = 0

            def download_segment(index: int, seg_info: Dict[str, Any]):
                if self.is_cancelled or self.is_paused:
                    return index, None
                seg_url = seg_info["url"]
                is_fmp4_ext = seg_url.endswith(".m4s") or playlist.get("init_map_url") is not None
                ext = ".m4s" if is_fmp4_ext else ".ts"
                seg_path = os.path.join(temp_dir, f"seg_{index:06d}{ext}")

                for attempt in range(3):
                    if self.is_cancelled or self.is_paused:
                        return index, None
                    try:
                        headers = dict(self.headers)
                        if seg_info.get("byterange"):
                            parts = seg_info["byterange"].split("@")
                            length = int(parts[0])
                            offset = int(parts[1]) if len(parts) > 1 else 0
                            headers["Range"] = f"bytes={offset}-{offset + length - 1}"

                        r = session.get(seg_url, headers=headers, timeout=12)
                        r.raise_for_status()
                        data = r.content

                        # Decrypt if segment key info exists
                        if seg_info.get("key_info") and seg_info["key_info"].get("method") != "NONE":
                            seq_num = seg_info.get("sequence_number", index)
                            data = key_mgr.decrypt_segment(data, seg_info["key_info"], seq_num)

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

                    except AppError:
                        raise
                    except Exception:
                        if attempt == 2:
                            raise
                        time.sleep(0.5)

                return index, None

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(download_segment, i, seg): i for i, seg in enumerate(segments)}
                for future in as_completed(futures):
                    if self.is_cancelled or self.is_paused:
                        break
                    res = future.result()
                    if res and res[1]:
                        segment_files[res[0]] = res[1]

            if self.is_cancelled:
                self.status = "cancelled"
                self._notify()
                return

            if self.is_paused:
                self.status = "paused"
                self._notify()
                return

            if any(p is None for p in segment_files):
                raise AppError(
                    ErrorCode.INTERNAL,
                    f"HLS download incomplete: {segment_files.count(None)} segments failed to download."
                )

            # 5. Merge downloaded video segments
            self.status = "merging"
            self.speed = 0.0
            self._notify()

            video_merged_path = os.path.join(temp_dir, "video_merged.mp4" if playlist.get("init_map_url") else "video_merged.ts")
            merge_segments(
                segment_files,
                video_merged_path,
                init_map_path=init_map_path,
                is_fmp4=bool(playlist.get("init_map_url"))
            )

            # 6. If separate audio was required, download and mux it
            if audio_m3u8_url:
                audio_save_path = os.path.join(temp_dir, "audio_merged.aac")
                audio_downloader = HLSDownloader(
                    m3u8_url=audio_m3u8_url,
                    save_path=audio_save_path,
                    max_workers=self.max_workers,
                    headers=self.headers
                )
                audio_downloader._run()
                if os.path.isfile(audio_save_path):
                    mux_audio_video(video_merged_path, audio_save_path, self.save_path)
                else:
                    shutil.copyfile(video_merged_path, self.save_path)
            else:
                shutil.copyfile(video_merged_path, self.save_path)

            self.status = "completed"
            self._notify()

        except Exception as e:
            self.status = "error"
            self.error_message = str(e)
            self._notify()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
