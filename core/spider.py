"""
IDM-Style Web Spider & Site Grabber Crawler Engine for P-Downloader.
Recursively crawls a target URL up to max_depth levels, extracts downloadable assets
(Video, Audio, Images, Documents, Archives), and feeds discovered links directly into Batch Add.
Includes SSRF and private IP address filtering with redirect protection (CWE-918 mitigation).
"""
import os
import re
import socket
import ipaddress
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

def is_safe_external_url(url: str) -> bool:
    """
    Prevents SSRF and internal port scanning by blocking private/loopback IP addresses.
    Validates scheme, hostname, IP literals, and resolved DNS addresses.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        hostname_clean = hostname.strip("[]").lower()
        if hostname_clean in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return False

        # 1. Check if hostname is an IP address literal
        try:
            ip = ipaddress.ip_address(hostname_clean)
        except ValueError:
            # 2. Resolve DNS for hostname
            try:
                resolved_ip = socket.gethostbyname(hostname_clean)
                ip = ipaddress.ip_address(resolved_ip)
            except Exception:
                return False

        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False

        return True
    except Exception:
        return False

class WebSpider:
    def __init__(
        self,
        start_url: str,
        max_depth: int = 1,
        target_categories: Optional[List[str]] = None,
        custom_extensions: Optional[Set[str]] = None,
        stay_on_domain: bool = True,
        max_threads: int = 4
    ):
        self.start_url = start_url.strip()
        self.max_depth = max(1, min(max_depth, 5))
        self.stay_on_domain = stay_on_domain
        self.max_threads = max(1, min(max_threads, 16))
        self.is_cancelled = False

        parsed = urlparse(self.start_url)
        self.start_domain = parsed.netloc.lower()

        # Build target extension filter
        self.target_extensions: Set[str] = set()
        if target_categories:
            for cat in target_categories:
                c_lower = cat.lower()
                if c_lower in DEFAULT_MEDIA_EXTENSIONS:
                    self.target_extensions.update(DEFAULT_MEDIA_EXTENSIONS[c_lower])

        if custom_extensions:
            self.target_extensions.update(ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in custom_extensions)

        if not self.target_extensions:
            # Default to all media
            for ext_set in DEFAULT_MEDIA_EXTENSIONS.values():
                self.target_extensions.update(ext_set)

        self.discovered_items: List[Dict[str, Any]] = []
        self.visited_pages: Set[str] = set()
        self._seen_urls: Set[str] = set()

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 P-Downloader-Spider/1.0"
        })

    def cancel(self):
        self.is_cancelled = True

    def crawl(self, progress_callback: Optional[Callable[[str, int], None]] = None) -> List[Dict[str, Any]]:
        """
        Executes breadth-first crawl starting from start_url up to max_depth.
        """
        if not is_safe_external_url(self.start_url):
            return []
            
        pages_to_crawl = [(self.start_url, 1)]  # (url, current_depth)

        while pages_to_crawl and not self.is_cancelled:
            current_batch = pages_to_crawl[:]
            pages_to_crawl.clear()

            # Filter unvisited pages
            unvisited = [item for item in current_batch if item[0] not in self.visited_pages and item[1] <= self.max_depth and is_safe_external_url(item[0])]
            if not unvisited:
                break

            next_level_links: List[str] = []

            with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                futures = {executor.submit(self._fetch_and_parse_page, url): url for url, depth in unvisited}

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

            next_depth = (current_batch[0][1] + 1) if current_batch else 2
            for link in next_level_links:
                if link not in self.visited_pages and (link, next_depth) not in pages_to_crawl and is_safe_external_url(link):
                    pages_to_crawl.append((link, next_depth))

        return self.discovered_items

    def _fetch_and_parse_page(self, page_url: str) -> List[str]:
        child_html_pages: List[str] = []
        if not is_safe_external_url(page_url):
            return []
        try:
            # Handle redirects manually to validate every redirect target hop against SSRF
            curr_url = page_url
            resp = None
            for _ in range(5):
                r = self.session.get(curr_url, timeout=12, allow_redirects=False)
                if r.is_redirect or r.status_code in (301, 302, 303, 307, 308):
                    loc = r.headers.get("Location")
                    if not loc:
                        break
                    next_url = urljoin(curr_url, loc)
                    if not is_safe_external_url(next_url):
                        # Block redirect to internal IP or private host
                        return []
                    curr_url = next_url
                else:
                    resp = r
                    break

            if not resp:
                return []

            content_type = resp.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return []

            html = resp.text
            # Extract links and sources
            raw_links = re.findall(r'(?:href|src)=["\']([^"\']+)["\']', html, re.IGNORECASE)

            for link in raw_links:
                if link.startswith("data:") or link.startswith("javascript:") or link.startswith("#"):
                    continue

                full_url = urljoin(curr_url, link)
                parsed = urlparse(full_url)
                if parsed.scheme not in ("http", "https"):
                    continue
                if not is_safe_external_url(full_url):
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
                            "source_page": curr_url
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
