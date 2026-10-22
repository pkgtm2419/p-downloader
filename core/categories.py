"""
File category mapping and directory resolution.
"""
import os
from pathlib import Path

CATEGORY_EXTENSIONS = {
    "Compressed": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".tgz"],
    "Documents": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv", ".epub", ".rtf"],
    "Music": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus"],
    "Programs": [".exe", ".msi", ".bat", ".cmd", ".apk", ".jar", ".appx", ".msix", ".dmg"],
    "Video": [".mp4", ".mkv", ".avi", ".webm", ".mov", ".flv", ".wmv", ".m4v", ".ts"],
}

DEFAULT_DOWNLOADS_DIR = str(Path.home() / "Downloads" / "P-Downloader")

def get_category_for_filename(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    for category, extensions in CATEGORY_EXTENSIONS.items():
        if ext in extensions:
            return category
    return "General"

def get_default_save_path(filename: str, category: str = None) -> str:
    if not category:
        category = get_category_for_filename(filename)
    
    base_dir = os.path.join(DEFAULT_DOWNLOADS_DIR, category)
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, filename)
