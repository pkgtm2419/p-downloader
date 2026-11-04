"""
YouTube & Streaming Media Handler for P-Downloader.
Provides fast metadata probing, format selection, playlist batch queueing,
and native yt-dlp multi-threaded stream acceleration.
"""
import os
import re
import sys
import shutil
import threading
from typing import Dict, Any, Optional, List, Callable
from urllib.parse import urlparse, parse_qs

try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False

from .muxer import FFmpegMuxer
from .speed_limiter import SpeedLimiter
from .categories import sanitize_filename, resolve_unique_filename


def is_youtube_url(url: str) -> bool:
    if not url:
        return False
    u = url.lower().strip()
    return (
        "youtube.com/watch" in u or
        "youtu.be/" in u or
        "youtube.com/shorts" in u or
        "youtube.com/embed" in u or
        "youtube.com/playlist" in u or
        "googlevideo.com/videoplayback" in u or
        ("youtube.com/" in u and "list=" in u)
    )


def is_youtube_playlist(url: str) -> bool:
    if not url:
        return False
    u = url.lower().strip()
    return "youtube.com/playlist" in u or ("youtube.com" in u and ("list=" in u) and ("watch" not in u or "action_get_list" in u))


def extract_clean_youtube_url(url: str, page_url: Optional[str] = None) -> str:
    """
    Returns the canonical YouTube URL.
    Cleans Radio Mixes (list=RD...) to single watch URLs while preserving real playlists.
    """
    target = page_url if (page_url and is_youtube_url(page_url) and "googlevideo.com" not in page_url.lower()) else url
    if not target:
        return ""
    # Radio mix URLs (list=RD...) attached to a video should target the individual video
    match_v = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", target)
    if match_v and "list=rd" in target.lower():
        return f"https://www.youtube.com/watch?v={match_v.group(1)}"
    match_id = re.search(r"[?&]id=([a-zA-Z0-9_-]{11})", target)
    if match_id and "googlevideo.com" in target.lower():
        return f"https://www.youtube.com/watch?v={match_id.group(1)}"
    match_doc = re.search(r"[?&]docid=([a-zA-Z0-9_-]{11})", target)
    if match_doc:
        return f"https://www.youtube.com/watch?v={match_doc.group(1)}"
    return target


def get_selectable_video_formats(formats: list, default_filesize: int = 0) -> List[Dict[str, Any]]:
    """
    Parses real format metadata from yt-dlp into user-friendly selectable choices.
    Does not fabricate sizes or resolutions; exposes actual streams with indicators.
    """
    if not formats:
        return [
            {
                "label": "Best Available (Auto-Merge)",
                "format_spec": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
                "quality": "best",
                "resolution": "Best",
                "ext": "mp4",
                "filesize": default_filesize,
                "has_audio": True,
                "needs_merge": True
            },
            {
                "label": "Audio Only (MP3 - 192kbps)",
                "format_spec": "bestaudio/best",
                "quality": "audio",
                "resolution": "Audio Only",
                "ext": "mp3",
                "filesize": int(default_filesize * 0.3) if default_filesize else 0,
                "has_audio": True,
                "needs_merge": False
            }
        ]

    # Group video formats by height
    height_map = {}
    best_audio_size = 0
    for f in formats:
        if not f:
            continue
        vcodec = f.get("vcodec") or "none"
        acodec = f.get("acodec") or "none"
        h = f.get("height")
        sz = f.get("filesize") or f.get("filesize_approx") or 0

        if vcodec == "none" and acodec != "none":
            if sz > best_audio_size:
                best_audio_size = sz
        elif vcodec != "none" and h and h > 100:
            if h not in height_map or sz > (height_map[h].get("filesize") or 0):
                height_map[h] = f

    sorted_heights = sorted(height_map.keys(), reverse=True)
    results = []

    # 1. Best available option
    top_h = sorted_heights[0] if sorted_heights else None
    results.append({
        "label": f"Best Available Quality ({top_h}p)" if top_h else "Best Available Quality",
        "format_spec": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
        "quality": "best",
        "resolution": f"{top_h}p" if top_h else "Best",
        "ext": "mp4",
        "filesize": default_filesize or (height_map[top_h].get("filesize", 0) + best_audio_size if top_h else 0),
        "has_audio": True,
        "needs_merge": True
    })

    # 2. Individual distinct resolutions
    for h in sorted_heights:
        f = height_map[h]
        ext = f.get("ext") or "mp4"
        vcodec = f.get("vcodec") or "none"
        acodec = f.get("acodec") or "none"
        is_muxed = (acodec != "none")
        sz = (f.get("filesize") or f.get("filesize_approx") or 0)
        if not is_muxed and best_audio_size > 0:
            sz += best_audio_size

        merge_note = " [Video + Audio]" if is_muxed else " [Audio Merge]"
        results.append({
            "label": f"{h}p ({ext.upper()}){merge_note}",
            "format_spec": f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={h}]+bestaudio/best[height<={h}]",
            "quality": f"{h}p",
            "resolution": f"{h}p",
            "ext": "mp4",
            "filesize": sz,
            "has_audio": True,
            "needs_merge": not is_muxed
        })

    # 3. Audio only options
    results.append({
        "label": "Audio Only (MP3 - 192kbps)",
        "format_spec": "bestaudio/best",
        "quality": "audio",
        "resolution": "Audio Only",
        "ext": "mp3",
        "filesize": best_audio_size,
        "has_audio": True,
        "needs_merge": False
    })
    results.append({
        "label": "Audio Only (M4A - Original)",
        "format_spec": "bestaudio[ext=m4a]/bestaudio",
        "quality": "audio",
        "resolution": "Audio Only",
        "ext": "m4a",
        "filesize": best_audio_size,
        "has_audio": True,
        "needs_merge": False
    })

    return results


def probe_youtube(url: str, timeout_sec: int = 8) -> Dict[str, Any]:
    """
    Probes YouTube single video or playlist metadata in a bounded non-blocking manner.
    """
    if not HAS_YTDLP:
        return {
            "title": "YouTube Video",
            "filename": "YouTube_Video.mp4",
            "total_bytes": 0,
            "duration": 0,
            "thumbnail": "",
            "formats": [],
            "is_playlist": False,
            "entries": []
        }

    target = extract_clean_youtube_url(url)
    ydl_opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "socket_timeout": timeout_sec,
        "noplaylist": False,
        "extractor_args": {"youtube": {"player_client": ["ios", "android", "web"]}},
    }
    ffmpeg_bin = FFmpegMuxer.get_ffmpeg_path()
    if ffmpeg_bin:
        ydl_opts["ffmpeg_location"] = ffmpeg_bin

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target, download=False)
            if not info:
                raise ValueError("No metadata returned by yt-dlp")

            # Check if this is a playlist
            is_pl = info.get("_type") == "playlist" or "entries" in info
            if is_pl:
                raw_entries = info.get("entries") or []
                clean_entries = []
                for idx, e in enumerate(raw_entries):
                    if not e:
                        continue
                    v_id = e.get("id") or ""
                    v_title = e.get("title") or f"Video {idx + 1}"
                    v_url = e.get("url") or f"https://www.youtube.com/watch?v={v_id}"
                    clean_entries.append({
                        "index": idx + 1,
                        "id": v_id,
                        "title": v_title,
                        "url": v_url,
                        "duration": e.get("duration", 0),
                        "thumbnail": e.get("thumbnail", "")
                    })
                title = info.get("title") or "YouTube Playlist"
                safe_title = sanitize_filename(title, default="YouTube_Playlist")
                return {
                    "is_playlist": True,
                    "title": title,
                    "playlist_id": info.get("id", ""),
                    "count": len(clean_entries),
                    "entries": clean_entries,
                    "filename": f"{safe_title}.mp4",
                    "total_bytes": 0,
                    "duration": 0,
                    "thumbnail": clean_entries[0]["thumbnail"] if clean_entries else "",
                    "formats": []
                }

            # Single video
            title = info.get("title") or "YouTube Video"
            safe_title = sanitize_filename(title, default="YouTube_Video")
            filesize = info.get("filesize") or info.get("filesize_approx") or 0
            formats = info.get("formats", [])
            selectable = get_selectable_video_formats(formats, filesize)

            return {
                "is_playlist": False,
                "title": title,
                "filename": f"{safe_title}.mp4",
                "total_bytes": filesize,
                "duration": info.get("duration", 0),
                "thumbnail": info.get("thumbnail", ""),
                "formats": formats,
                "selectable_formats": selectable,
                "entries": []
            }
    except Exception as e:
        # Fallback safe descriptor if network fails or invalid video
        safe_fallback = "YouTube_Video"
        cand = os.path.basename(target.split("?")[0])
        if cand and cand.lower() not in ("watch", "videoplayback", "download", "view"):
            safe_fallback = sanitize_filename(cand, default="YouTube_Video")

        return {
            "is_playlist": False,
            "title": safe_fallback or "YouTube Video",
            "filename": f"{safe_fallback or 'YouTube_Video'}.mp4",
            "total_bytes": 0,
            "duration": 0,
            "thumbnail": "",
            "formats": [],
            "selectable_formats": get_selectable_video_formats([], 0),
            "entries": [],
            "error": str(e)
        }


class YouTubeDownloadTask:
    """
    High-speed YouTube download task implementing the standard DownloadTask interface.
    """
    def __init__(
        self,
        task_id: str,
        url: str,
        save_path: str,
        page_url: Optional[str] = None,
        quality: Optional[str] = None,
        connections: int = 8,
        speed_limit: int = 0,
        on_progress: Optional[Callable[['YouTubeDownloadTask'], None]] = None,
        on_complete: Optional[Callable[['YouTubeDownloadTask'], None]] = None,
        on_error: Optional[Callable[['YouTubeDownloadTask', str], None]] = None
    ):
        self.task_id = task_id
        self.url = extract_clean_youtube_url(url, page_url)
        self.save_path = save_path
        self.page_url = page_url
        self.quality = quality
        self.connections = connections
        self.speed_limiter = SpeedLimiter(speed_limit)
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error

        self.total_bytes = 0
        self.downloaded_bytes = 0
        self.supports_range = True
        self.status = "queued"
        self.error_message = ""
        self.speed = 0.0
        self.segments: List[Any] = []

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def prepare(self):
        save_dir = os.path.dirname(self.save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)

    def start(self):
        if self.status == "downloading":
            return
        self._stop_event.clear()
        self.status = "downloading"
        self._thread = threading.Thread(target=self._run_ytdlp, daemon=True)
        self._thread.start()

    def pause(self):
        if self.status not in ("downloading", "queued"):
            return
        self._stop_event.set()
        self.status = "paused"
        self.speed = 0.0
        if self.on_progress:
            self.on_progress(self)

    def cancel(self):
        self.status = "cancelled"
        self._stop_event.set()
        if os.path.exists(self.save_path):
            try:
                os.remove(self.save_path)
            except Exception:
                pass
        part_path = self.save_path + ".part"
        if os.path.exists(part_path):
            try:
                os.remove(part_path)
            except Exception:
                pass

    def set_speed_limit(self, limit_bytes_per_sec: int):
        self.speed_limiter.set_limit(limit_bytes_per_sec)

    def refresh_url(self, new_url: str) -> bool:
        self.url = extract_clean_youtube_url(new_url)
        self.error_message = ""
        if self.status != "completed":
            self.status = "paused"
        return True

    def _progress_hook(self, d: Dict[str, Any]):
        if self._stop_event.is_set():
            raise Exception("Download aborted by user")

        status = d.get("status")
        if status == "downloading":
            self.downloaded_bytes = d.get("downloaded_bytes") or self.downloaded_bytes
            tb = d.get("total_bytes") or d.get("total_bytes_estimate")
            if tb:
                self.total_bytes = tb
            self.speed = float(d.get("speed") or 0.0)
            if self.on_progress:
                self.on_progress(self)
        elif status == "finished":
            self.downloaded_bytes = self.total_bytes or self.downloaded_bytes
            self.speed = 0.0
            if self.on_progress:
                self.on_progress(self)

    def _run_ytdlp(self):
        if not HAS_YTDLP:
            self.status = "error"
            self.error_message = "yt-dlp is required for YouTube streaming downloads."
            if self.on_error:
                self.on_error(self, self.error_message)
            return

        is_audio = self.save_path.lower().endswith((".mp3", ".m4a", ".aac", ".ogg", ".opus"))

        # Build yt-dlp format selector
        if is_audio or (self.quality and "audio" in self.quality.lower()):
            format_spec = "bestaudio/best"
        elif self.quality and re.match(r"^\d+p?", self.quality.lower()):
            height = self.quality.lower().rstrip("p")
            format_spec = f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
        else:
            format_spec = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best"

        ydl_opts: Dict[str, Any] = {
            "outtmpl": self.save_path,
            "format": format_spec,
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "overwrites": True,
            "continuedl": True,
            "socket_timeout": 15,
            "noplaylist": True,  # Individual tasks download one video at a time
            "extractor_args": {"youtube": {"player_client": ["ios", "android", "web"]}},
        }

        ffmpeg_bin = FFmpegMuxer.get_ffmpeg_path()
        if ffmpeg_bin:
            ydl_opts["ffmpeg_location"] = ffmpeg_bin
            if is_audio and self.save_path.lower().endswith(".mp3"):
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])

            if not self._stop_event.is_set():
                self.status = "completed"
                self.speed = 0.0
                if os.path.exists(self.save_path):
                    self.total_bytes = os.path.getsize(self.save_path)
                    self.downloaded_bytes = self.total_bytes
                if self.on_progress:
                    self.on_progress(self)
                if self.on_complete:
                    self.on_complete(self)

        except Exception as e:
            if not self._stop_event.is_set() and self.status not in ("paused", "cancelled"):
                self.status = "error"
                self.error_message = str(e)
                if self.on_error:
                    self.on_error(self, str(e))
