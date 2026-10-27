"""
YouTube and Streaming Media Downloader for P-Downloader.
Leverages yt-dlp to download YouTube and media streams with format selection,
resumption, real-time progress callbacks, and audio/video muxing.
"""
import os
import re
import threading
import time
from typing import Optional, Callable, Dict, Any, List

try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False

from core.speed_limiter import SpeedLimiter
from core.muxer import FFmpegMuxer


def is_youtube_url(url: str) -> bool:
    if not url:
        return False
    u = url.lower()
    return (
        "youtube.com/watch" in u or
        "youtu.be/" in u or
        "youtube.com/shorts" in u or
        "youtube.com/embed" in u or
        "googlevideo.com/videoplayback" in u
    )


def extract_clean_youtube_url(url: str, page_url: Optional[str] = None) -> str:
    """
    Returns the canonical YouTube watch URL from either page_url or raw stream url.
    """
    if page_url and is_youtube_url(page_url) and "googlevideo.com" not in page_url.lower():
        return page_url
    if is_youtube_url(url) and "googlevideo.com" not in url.lower():
        return url
    # If it is a googlevideo.com URL, attempt to find docid or id parameter
    match = re.search(r"[?&]id=([a-zA-Z0-9_-]{11})", url)
    if match:
        return f"https://www.youtube.com/watch?v={match.group(1)}"
    match_doc = re.search(r"[?&]docid=([a-zA-Z0-9_-]{11})", url)
    if match_doc:
        return f"https://www.youtube.com/watch?v={match_doc.group(1)}"
    return url


def probe_youtube(url: str) -> Dict[str, Any]:
    """
    Extracts video metadata using yt-dlp without downloading.
    """
    if not HAS_YTDLP:
        return {
            "title": "YouTube Video",
            "filename": "YouTube_Video.mp4",
            "total_bytes": 0,
            "duration": 0,
            "thumbnail": "",
            "formats": []
        }

    target = extract_clean_youtube_url(url)
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    ffmpeg_bin = FFmpegMuxer.get_ffmpeg_path()
    if ffmpeg_bin:
        ydl_opts["ffmpeg_location"] = os.path.dirname(ffmpeg_bin)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(target, download=False)
        title = info.get("title") or "YouTube Video"
        # Sanitize filename
        safe_title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', title).strip(". ")
        filesize = info.get("filesize") or info.get("filesize_approx") or 0
        formats = info.get("formats", [])
        return {
            "title": title,
            "filename": f"{safe_title}.mp4",
            "total_bytes": filesize,
            "duration": info.get("duration", 0),
            "thumbnail": info.get("thumbnail", ""),
            "formats": formats
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
        # Probe metadata if total_bytes is 0
        try:
            info = probe_youtube(self.url)
            if info.get("total_bytes"):
                self.total_bytes = info["total_bytes"]
        except Exception:
            pass

    def start(self):
        if self.status == "downloading":
            return
        self._stop_event.clear()
        self.status = "downloading"
        self._thread = threading.Thread(target=self._run_ytdlp, daemon=True)
        self._thread.start()

    def pause(self):
        if self.status != "downloading":
            return
        self._stop_event.set()
        self.status = "paused"
        self.speed = 0.0
        if self._thread:
            self._thread.join(timeout=1.0)
        if self.on_progress:
            self.on_progress(self)

    def cancel(self):
        self.status = "cancelled"
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
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
        if is_audio:
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
        }

        ffmpeg_bin = FFmpegMuxer.get_ffmpeg_path()
        if ffmpeg_bin:
            ydl_opts["ffmpeg_location"] = os.path.dirname(ffmpeg_bin)
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
