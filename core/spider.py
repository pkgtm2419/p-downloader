"""
Web Spider / Site Grabber Engine for P-Downloader.
Recursively crawls web pages up to depth N to find downloadable media, documents,
images, and archives for batch downloading.
"""
import os
import re
import threading
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Set, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

DEFAULT_MEDIA_EXTENSIONS = {
    "video": {".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv", ".ts", ".m4v", ".m3u8"},
    "audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".opus"},
    "archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".iso", ".exe", ".msi"},
    "documents": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"},
    "images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
}

class WebSpider:
    def __init__(
        self,
        start_url: str,
        max_depth: int = 1,
        target_categories: Optional[List[str]] = None,
        custom_extensions: Optional[Set[str]] = None,
        stay_on_domain: bool = True,
        max_workers: int = 4
    ):
        self.start_url = start_url.strip()
        self.max_depth = max(1, min(max_depth, 5))
        self.stay_on_domain = stay_on_domain
        self.max_workers = max_workers

        parsed = urlparse(self.start_url)
        self.start_domain = parsed.netloc.lower()

        # Build set of target extensions
        self.target_extensions: Set[str] = set()
        cats = target_categories or ["video", "audio", "archives", "documents"]
        for cat in cats:
            if cat in DEFAULT_MEDIA_EXTENSIONS:
                self.target_extensions.update(DEFAULT_MEDIA_EXTENSIONS[cat])
        if custom_extensions:
            self.target_extensions.update(ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in custom_extensions)

        self.visited_pages: Set[str] = set()
        self.discovered_items: List[Dict[str, Any]] = []
        self._seen_urls: Set[str] = set()
        self.is_cancelled = False

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def crawl(
        self,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes multi-level crawling. Returns list of discovered downloadable items.
        """
        pages_to_crawl = [(self.start_url, 1)]

        for depth in range(1, self.max_depth + 1):
            if self.is_cancelled:
                break

            current_level_pages = [url for url, d in pages_to_crawl if d == depth and url not in self.visited_pages]
            if not current_level_pages:
                break

            next_level_links: List[str] = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(self._fetch_and_parse_page, page_url): page_url for page_url in current_level_pages}
                for future in as_completed(futures):
                    if self.is_cancelled:
                        break
                    p_url = futures[future]
                    self.visited_pages.add(p_url)
                    try:
                        child_links = future.result()
                        next_level_links.extend(child_links)
                        if progress_callback:
                            progress_callback(p_url, len(self.discovered_items))
                    except Exception:
                        pass

            for link in next_level_links:
                if link not in self.visited_pages and (link, depth + 1) not in pages_to_crawl:
                    pages_to_crawl.append((link, depth + 1))

        return self.discovered_items

    def _fetch_and_parse_page(self, page_url: str) -> List[str]:
        child_html_pages: List[str] = []
        try:
            resp = self.session.get(page_url, timeout=12)
            content_type = resp.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return []

            html = resp.text
            # Extract links and sources
            raw_links = re.findall(r'(?:href|src)=["\']([^"\']+)["\']', html, re.IGNORECASE)

            for link in raw_links:
                if link.startswith("data:") or link.startswith("javascript:") or link.startswith("#"):
                    continue

                full_url = urljoin(page_url, link)
                parsed = urlparse(full_url)
                if parsed.scheme not in ("http", "https"):
                    continue

                path = parsed.path
                ext = os.path.splitext(path)[1].lower()

                # Check if it matches media/file extensions
                if ext in self.target_extensions:
                    if full_url not in self._seen_urls:
                        self._seen_urls.add(full_url)
                        fn = os.path.basename(path) or f"download{ext}"
                        self.discovered_items.append({
                            "filename": fn,
                            "url": full_url,
                            "type": ext.lstrip(".").upper(),
                            "source_page": page_url
                        })
                elif not ext or ext in (".html", ".htm", ".php", ".asp", ".aspx"):
                    # Potential next page link
                    if self.stay_on_domain:
                        if parsed.netloc.lower() == self.start_domain:
                            child_html_pages.append(full_url)
                    else:
                        child_html_pages.append(full_url)

        except Exception:
            pass

        return child_html_pages

    def cancel(self):
        self.is_cancelled = True
