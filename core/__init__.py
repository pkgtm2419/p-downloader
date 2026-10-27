"""
P-Downloader Core Engine Package
"""
__version__ = "1.0.2"

from .engine import DownloadEngine
from .segment import DownloadTask, probe_url
from .db import DownloadDB
from .categories import get_category_for_filename, get_default_save_path

__all__ = [
    "DownloadEngine",
    "DownloadTask",
    "probe_url",
    "DownloadDB",
    "get_category_for_filename",
    "get_default_save_path"
]
