"""
YouTube & Streaming Media Handler for P-Downloader.
Re-exports universal media extraction capabilities from core.extractor for backward compatibility.
"""
from .extractor import (
    is_youtube_url,
    is_media_url,
    is_youtube_playlist,
    extract_clean_youtube_url,
    extract_canonical_media_url,
    get_selectable_video_formats,
    probe_youtube,
    probe_media,
    YouTubeDownloadTask,
    UniversalMediaTask,
    HAS_YTDLP
)

__all__ = [
    "is_youtube_url",
    "is_media_url",
    "is_youtube_playlist",
    "extract_clean_youtube_url",
    "extract_canonical_media_url",
    "get_selectable_video_formats",
    "probe_youtube",
    "probe_media",
    "YouTubeDownloadTask",
    "UniversalMediaTask",
    "HAS_YTDLP"
]
