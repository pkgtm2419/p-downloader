"""
Universal Streaming Media Extraction & Acceleration Engine for P-Downloader.
Extracts video, audio, and subtitle streams from 1,000+ streaming sites (YouTube, Vimeo,
X/Twitter, TikTok, Reddit, Instagram, Facebook, Twitch, Crunchyroll, news sites)
using multi-threaded fragment acceleration, origin-authenticated session forwarding,
and DRM detection.
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
from .router import is_streaming_site


def is_youtube_url(url: str) -> bool:
    """Checks if a URL belongs to YouTube specifically."""
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


def is_media_url(url: str) -> bool:
    """Returns True if the URL is from YouTube or any other supported streaming site."""
    return is_youtube_url(url) or is_streaming_site(url)


def is_youtube_playlist(url: str) -> bool:
    if not url:
        return False
    u = url.lower().strip()
    return "youtube.com/playlist" in u or ("youtube.com" in u and ("list=" in u) and ("watch" not in u or "action_get_list" in u))


def extract_canonical_media_url(url: str, page_url: Optional[str] = None) -> str:
    """
    Returns canonical clean URL for YouTube, Vimeo, Reddit, and other streaming sites.
    """
    target = page_url if (page_url and is_media_url(page_url) and "googlevideo.com" not in page_url.lower()) else url
    if not target:
        return ""

    # Clean YouTube radio mix URLs
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


extract_clean_youtube_url = extract_canonical_media_url


def get_selectable_video_formats(formats: list, default_filesize: int = 0) -> List[Dict[str, Any]]:
    """
    Parses stream format metadata from yt-dlp into user-friendly selectable choices.
    Supports 8K, 4K, 1440p, 1080p, 720p, 480p, 360p, and audio-only streams (MP3/M4A).
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


def probe_media(
    url: str,
    timeout_sec: int = 10,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Probes video/audio metadata across 1,000+ streaming sites using yt-dlp.
    """
    if not HAS_YTDLP:
        return {
            "title": "Online Video",
            "filename": "Video.mp4",
            "total_bytes": 0,
            "duration": 0,
            "thumbnail": "",
            "formats": [],
            "is_playlist": False,
            "entries": []
        }

    target = extract_canonical_media_url(url)
    ydl_opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "socket_timeout": timeout_sec,
        "noplaylist": False,
        "extractor_args": {"youtube": {"player_client": ["ios", "android", "web"]}},
    }

    if headers:
        ydl_opts["http_headers"] = headers

    ffmpeg_bin = FFmpegMuxer.get_ffmpeg_path()
    if ffmpeg_bin:
        ydl_opts["ffmpeg_location"] = ffmpeg_bin

    try:
        from core.db import DownloadDB
        proxy_url = DownloadDB().get_proxy_url()
        if proxy_url:
            ydl_opts["proxy"] = proxy_url
    except Exception:
        pass

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target, download=False)
            if not info:
                raise ValueError("No metadata returned by extractor")

            # Check if this is a playlist
            is_pl = info.get("_type") == "playlist" or "entries" in info
            if is_pl:
                raw_entries = info.get("entries") or []
                clean_entries = []
                for idx, e in enumerate(raw_entries):
                    if not e:
                        continue
                    clean_entries.append({
                        "index": idx + 1,
                        "id": e.get("id"),
                        "title": e.get("title") or f"Item {idx + 1}",
                        "url": e.get("url") or (f"https://www.youtube.com/watch?v={e.get('id')}" if e.get("id") else target),
                        "duration": e.get("duration", 0),
                        "selected": True
                    })

                return {
                    "is_playlist": True,
                    "title": info.get("title", "Streaming Playlist"),
                    "filename": sanitize_filename(info.get("title", "Playlist")),
                    "entries": clean_entries,
                    "count": len(clean_entries),
                    "thumbnail": info.get("thumbnail", ""),
                    "formats": [],
                    "selectable_formats": [],
                    "total_bytes": 0,
                    "duration": 0
                }

            # Single video item
            title = info.get("title", "Video")
            ext = info.get("ext", "mp4")
            raw_formats = info.get("formats", [])
            dur = info.get("duration", 0)
            thumb = info.get("thumbnail", "")

            filesize = info.get("filesize") or info.get("filesize_approx") or 0
            selectable = get_selectable_video_formats(raw_formats, default_filesize=filesize)

            safe_fn = sanitize_filename(f"{title}.{ext}")
            return {
                "is_playlist": False,
                "title": title,
                "filename": safe_fn,
                "total_bytes": filesize,
                "duration": dur,
                "thumbnail": thumb,
                "formats": raw_formats,
                "selectable_formats": selectable,
                "entries": []
            }
    except Exception as e:
        err_msg = str(e)
        if "DRM" in err_msg or "Widevine" in err_msg or "PlayReady" in err_msg:
            raise RuntimeError("This stream is DRM-protected (Widevine/PlayReady) and cannot be recorded.")
        return {
            "title": "Online Video",
            "filename": "Video.mp4",
            "total_bytes": 0,
            "duration": 0,
            "thumbnail": "",
            "formats": [],
            "selectable_formats": [],
            "is_playlist": False,
            "entries": []
        }


probe_youtube = probe_media


class UniversalMediaTask:
    """
    Universal high-speed streaming media download task for 1,000+ sites.
    Features 8x parallel fragment downloads, audio muxing, and proxy support.
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
        headers: Optional[Dict[str, str]] = None,
        on_progress: Optional[Callable[['UniversalMediaTask'], None]] = None,
        on_complete: Optional[Callable[['UniversalMediaTask'], None]] = None,
        on_error: Optional[Callable[['UniversalMediaTask', str], None]] = None
    ):
        self.task_id = task_id
        self.url = extract_canonical_media_url(url, page_url)
        self.save_path = save_path
        self.page_url = page_url
        self.quality = quality
        self.connections = connections
        self.headers = headers or {}
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
        self.is_media = True

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def prepare(self):
        save_dir = os.path.dirname(self.save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)

        if not self.total_bytes or self.total_bytes == 0:
            try:
                info = probe_media(self.url, timeout_sec=8, headers=self.headers)
                if not info.get("is_playlist"):
                    self.total_bytes = info.get("total_bytes", 0)
            except Exception:
                pass

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self.status = "downloading"
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def pause(self):
        self._stop_event.set()
        self.status = "paused"
        if self.on_progress:
            self.on_progress(self)

    def resume(self):
        self.start()

    def cancel(self):
        self._stop_event.set()
        self.status = "cancelled"
        if self.on_progress:
            self.on_progress(self)

    def _progress_hook(self, d: Dict[str, Any]):
        if self._stop_event.is_set():
            raise KeyboardInterrupt("Download interrupted by user")

        status = d.get("status")
        if status == "downloading":
            self.status = "downloading"
            self.downloaded_bytes = d.get("downloaded_bytes", self.downloaded_bytes)
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total:
                self.total_bytes = total
            self.speed = d.get("speed") or 0.0

            if self.on_progress:
                self.on_progress(self)
        elif status == "finished":
            self.downloaded_bytes = self.total_bytes or self.downloaded_bytes
            if self.on_progress:
                self.on_progress(self)

    def _run(self):
        if not HAS_YTDLP:
            self.status = "error"
            self.error_message = "yt-dlp is not installed. Please install yt-dlp to download streaming media."
            if self.on_error:
                self.on_error(self, self.error_message)
            return

        is_audio = self.quality and "audio" in self.quality.lower()
        if is_audio:
            format_spec = "bestaudio/best"
        elif self.quality and self.quality != "best":
            h = re.sub(r"[^\d]", "", self.quality)
            if h:
                format_spec = f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={h}]+bestaudio/best[height<={h}]"
            else:
                format_spec = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best"
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
            "retries": 10,
            "fragment_retries": 10,
            "concurrent_fragment_downloads": 8,
            "http_chunk_size": 10485760,
            "noplaylist": True,
            "extractor_args": {"youtube": {"player_client": ["ios", "android", "web"]}},
        }

        if self.headers:
            ydl_opts["http_headers"] = self.headers

        try:
            from core.db import DownloadDB
            proxy_url = DownloadDB().get_proxy_url()
            if proxy_url:
                ydl_opts["proxy"] = proxy_url
        except Exception:
            pass

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
                if self.on_complete:
                    self.on_complete(self)
        except KeyboardInterrupt:
            self.status = "paused"
            if self.on_progress:
                self.on_progress(self)
        except Exception as e:
            err_msg = str(e)
            if "DRM" in err_msg or "Widevine" in err_msg or "PlayReady" in err_msg:
                self.error_message = "This media stream is protected by DRM (Widevine/PlayReady) and cannot be recorded."
            else:
                self.error_message = err_msg
            self.status = "error"
            if self.on_error:
                self.on_error(self, self.error_message)


# Backward compatibility aliases
YouTubeDownloadTask = UniversalMediaTask
