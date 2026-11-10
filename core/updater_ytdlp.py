"""
Standalone Self-Updater for yt-dlp streaming extractors in P-Downloader.
Checks official GitHub releases for yt-dlp, detects newer versions,
and upgrades dependencies dynamically without requiring full app reinstallation.
"""
import sys
import subprocess
from typing import Dict, Any, Tuple, Optional
import requests

try:
    import yt_dlp
    CURRENT_VERSION = getattr(yt_dlp.version, "__version__", "unknown")
except Exception:
    CURRENT_VERSION = "not installed"

YTDLP_RELEASES_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"

def check_for_ytdlp_updates(timeout_sec: int = 10) -> Dict[str, Any]:
    """
    Checks GitHub releases for the latest available yt-dlp version.
    """
    current = CURRENT_VERSION
    try:
        from core.db import DownloadDB
        proxies = DownloadDB().get_proxy_config()
    except Exception:
        proxies = None

    headers = {
        "User-Agent": "P-Downloader/1.1.0 Extractor-Updater"
    }

    try:
        resp = requests.get(YTDLP_RELEASES_API, headers=headers, proxies=proxies, timeout=timeout_sec)
        resp.raise_for_status()
        data = resp.json()

        latest_tag = data.get("tag_name", "").lstrip("v")
        release_url = data.get("html_url", "https://github.com/yt-dlp/yt-dlp/releases")

        has_update = False
        if current != "not installed" and latest_tag:
            has_update = (latest_tag > current)

        return {
            "has_update": has_update,
            "current_version": current,
            "latest_version": latest_tag,
            "release_url": release_url
        }
    except Exception as e:
        return {
            "has_update": False,
            "current_version": current,
            "latest_version": current,
            "error": str(e)
        }

def update_ytdlp(pip_upgrade: bool = True) -> Tuple[bool, str]:
    """
    Upgrades yt-dlp to the latest release using pip subprocess.
    """
    try:
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return True, "Successfully upgraded yt-dlp to latest version."
        return False, f"Upgrade failed (code {result.returncode}): {result.stderr.strip()}"
    except Exception as e:
        return False, f"Upgrade execution error: {str(e)}"
