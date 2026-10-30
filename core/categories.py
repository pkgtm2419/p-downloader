"""
File category mapping and directory resolution with path traversal sanitization.
"""
import os
import re
from pathlib import Path

CATEGORY_EXTENSIONS = {
    "Compressed": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".tgz"],
    "Documents": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv", ".epub", ".rtf"],
    "Music": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus"],
    "Programs": [".exe", ".msi", ".bat", ".cmd", ".apk", ".jar", ".appx", ".msix", ".dmg"],
    "Video": [".mp4", ".mkv", ".avi", ".webm", ".mov", ".flv", ".wmv", ".m4v", ".ts"],
}

DEFAULT_DOWNLOADS_DIR = str(Path.home() / "Downloads" / "P-Downloader")

def sanitize_filename(filename: str, default: str = "download.bin") -> str:
    """
    Sanitizes untrusted filenames from URLs and Content-Disposition headers.
    Strips directory traversal sequences, illegal OS characters, and control codes.
    """
    if not filename:
        return default
    
    # 1. Normalize path separators and extract basename only
    clean = os.path.basename(filename.replace("\\", "/"))
    # 2. Strip null bytes and whitespace/dots
    clean = clean.replace("\x00", "").strip(". ")
    # 3. Remove illegal Windows & Unix filename characters: < > : " / \ | ? *
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', clean)
    
    # 4. Check if filename was reduced to empty or dangerous dot names
    if not clean or clean in (".", ".."):
        return default
    
    return clean

def get_category_for_filename(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    for category, extensions in CATEGORY_EXTENSIONS.items():
        if ext in extensions:
            return category
    return "General"

def get_default_save_path(filename: str, category: str = None) -> str:
    """
    Calculates safe destination path inside DEFAULT_DOWNLOADS_DIR.
    Guarantees canonical target path cannot escape the category directory.
    """
    safe_fn = sanitize_filename(filename)
    if not category:
        category = get_category_for_filename(safe_fn)
    
    base_dir = (Path(DEFAULT_DOWNLOADS_DIR) / category).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    
    target_path = (base_dir / safe_fn).resolve()
    # Path traversal assertion: target must strictly be inside base_dir
    try:
        target_path.relative_to(base_dir)
    except ValueError:
        target_path = base_dir / "download.bin"
        
    return str(target_path)
