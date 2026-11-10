"""
Intelligent Download Task Router for P-Downloader.
Classifies incoming URLs, MIME types, and filenames into appropriate download engines
(Direct Accelerated HTTP, HLS, DASH, Universal Streaming Media, FTP, BitTorrent).
"""
import re
from urllib.parse import urlparse
from typing import Optional, Dict, Any
from .download_models import DownloadKind

KNOWN_STREAMING_DOMAINS = {
    "youtube.com", "youtu.be", "googlevideo.com",
    "vimeo.com", "dailymotion.com",
    "twitter.com", "x.com", "t.co",
    "tiktok.com", "instagram.com", "facebook.com", "fb.watch",
    "reddit.com", "v.redd.it",
    "twitch.tv", "kick.com",
    "soundcloud.com", "bandcamp.com", "mixcloud.com",
    "bilibili.com", "nicovideo.jp",
    "rumble.com", "odysee.com", "bitchute.com",
    "crunchyroll.com", "funimation.com",
    "bbc.co.uk", "cnn.com", "foxnews.com", "msnbc.com"
}

KNOWN_BINARY_EXTENSIONS = {
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".img",
    ".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".apk",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".bin", ".dat", ".raw"
}

def is_streaming_site(url: str) -> bool:
    """Returns True if the URL domain matches a known streaming site."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        for domain in KNOWN_STREAMING_DOMAINS:
            if host == domain or host.endswith("." + domain):
                return True
        return False
    except Exception:
        return False

def classify_target(
    url: str,
    content_type: Optional[str] = None,
    filename: Optional[str] = None
) -> DownloadKind:
    """
    Classifies a download request into the optimal engine:
    - TORRENT: magnet:? or .torrent
    - FTP: ftp:// or ftps://
    - HLS: .m3u8 or application/x-mpegURL
    - DASH: .mpd or application/dash+xml
    - MEDIA: known streaming site or HTML page containing extractable media
    - HTTP: direct binary file / accelerated HTTP range worker
    """
    u_lower = (url or "").strip().lower()
    fn_lower = (filename or "").strip().lower()
    ct_lower = (content_type or "").strip().lower()

    # 1. BitTorrent check
    if u_lower.startswith("magnet:?") or fn_lower.endswith(".torrent") or u_lower.endswith(".torrent"):
        return DownloadKind.TORRENT
    if ct_lower in ("application/x-bittorrent",):
        return DownloadKind.TORRENT

    # 2. FTP check
    if u_lower.startswith(("ftp://", "ftps://")):
        return DownloadKind.FTP

    # 3. HLS check
    if ".m3u8" in u_lower or fn_lower.endswith(".m3u8") or ".m3u8" in fn_lower:
        return DownloadKind.HLS
    if any(ct in ct_lower for ct in ("application/x-mpegurl", "application/vnd.apple.mpegurl", "audio/x-mpegurl")):
        return DownloadKind.HLS

    # 4. DASH check
    if ".mpd" in u_lower or fn_lower.endswith(".mpd"):
        return DownloadKind.DASH
    if "application/dash+xml" in ct_lower:
        return DownloadKind.DASH

    # 5. Known streaming domain check
    if is_streaming_site(url):
        return DownloadKind.MEDIA

    # 6. Binary file extension check
    for ext in KNOWN_BINARY_EXTENSIONS:
        if fn_lower.endswith(ext) or u_lower.split("?")[0].endswith(ext):
            return DownloadKind.HTTP

    # 7. Content-Type inspection
    if ct_lower:
        if any(prefix in ct_lower for prefix in ("video/", "audio/", "application/octet-stream", "application/zip", "application/x-")):
            return DownloadKind.HTTP
        if "text/html" in ct_lower:
            # HTML page that might contain embedded media
            return DownloadKind.MEDIA

    return DownloadKind.HTTP
