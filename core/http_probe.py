"""
Strict HTTP capability detection, range verification, and metadata extraction.
"""
import os
import re
import urllib.parse
from typing import Optional, Dict
import requests

from .download_models import DownloadRequest, HttpProbeResult, ProbeError
from .categories import sanitize_filename

MAX_REDIRECTS = 10
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def parse_content_disposition(cd_header: str) -> Optional[str]:
    """Parse Content-Disposition for RFC 5987 and standard filename values."""
    if not cd_header:
        return None

    # Check for RFC 5987 filename*=UTF-8''filename.ext
    rfc5987_match = re.search(r"filename\*\s*=\s*([^;]+)", cd_header, re.IGNORECASE)
    if rfc5987_match:
        val = rfc5987_match.group(1).strip().strip('"\'')
        if "''" in val:
            encoding, clean_val = val.split("''", 1)
            try:
                decoded = urllib.parse.unquote(clean_val, encoding=encoding or "utf-8")
                return sanitize_filename(decoded)
            except Exception:
                pass
        else:
            return sanitize_filename(urllib.parse.unquote(val))

    # Fallback to standard filename="name"
    standard_match = re.search(r'filename\s*=\s*(?:"([^"]+)"|([^;\s]+))', cd_header, re.IGNORECASE)
    if standard_match:
        fn = standard_match.group(1) or standard_match.group(2)
        if fn:
            return sanitize_filename(fn.strip('"\' '))

    return None

def extract_filename_from_url(url: str) -> str:
    """Extract and sanitize filename from URL path."""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    base = os.path.basename(urllib.parse.unquote(path))
    if base and base != "/" and base != ".":
        return sanitize_filename(base)
    return "download"

def probe_http(request: DownloadRequest, timeout_s: float = 8.0) -> HttpProbeResult:
    """
    Perform strict capability detection using a bounded GET Range request.
    Verifies actual byte range support rather than blindly trusting Accept-Ranges.
    """
    parsed = urllib.parse.urlparse(request.url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ProbeError("UNSUPPORTED_SCHEME", f"Unsupported URL scheme: {parsed.scheme}")

    req_headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "*/*",
        "Accept-Encoding": "identity",
        "Range": "bytes=0-0"
    }

    # Apply context headers if origin matches
    if request.context:
        if request.context.user_agent:
            req_headers["User-Agent"] = request.context.user_agent
        if request.context.referrer:
            req_headers["Referer"] = request.context.referrer
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin in request.context.per_origin_headers:
            req_headers.update(request.context.per_origin_headers[origin])

    session = requests.Session()
    session.max_redirects = MAX_REDIRECTS

    try:
        resp = session.get(request.url, headers=req_headers, stream=True, timeout=timeout_s, allow_redirects=True)
    except requests.exceptions.TooManyRedirects:
        raise ProbeError("REDIRECT_LOOP", "Too many redirects encountered while probing URL")
    except requests.exceptions.Timeout:
        raise ProbeError("TIMEOUT", f"Connection timed out after {timeout_s}s")
    except requests.exceptions.RequestException as e:
        raise ProbeError("NETWORK_ERROR", str(e))

    final_url = resp.url
    status = resp.status_code

    if status in (401, 403):
        resp.close()
        raise ProbeError("AUTH_REQUIRED", f"Authentication required (HTTP {status})")
    elif status == 404:
        resp.close()
        raise ProbeError("NOT_FOUND", f"Remote file not found (HTTP {status})")

    content_type = resp.headers.get("Content-Type")
    etag = resp.headers.get("ETag")
    last_modified = resp.headers.get("Last-Modified")
    content_disp = resp.headers.get("Content-Disposition", "")

    # Resolve filename
    extracted_filename = parse_content_disposition(content_disp)
    if not extracted_filename:
        if request.filename:
            extracted_filename = sanitize_filename(request.filename)
        else:
            extracted_filename = extract_filename_from_url(final_url)

    total_bytes: Optional[int] = None
    supports_ranges: bool = False

    if status == 416:
        # Range Not Satisfiable: Could be 0-byte file (Content-Range: bytes */0)
        cr = resp.headers.get("Content-Range", "")
        resp.close()
        if "*/0" in cr or "/0" in cr:
            return HttpProbeResult(
                final_url=final_url,
                total_bytes=0,
                supports_ranges=False,
                etag=etag,
                last_modified=last_modified,
                filename=extracted_filename,
                content_type=content_type
            )
        raise ProbeError("INVALID_RANGE", f"HTTP 416 Range Not Satisfiable: {cr}")

    elif status == 206:
        # Verified range response
        cr = resp.headers.get("Content-Range", "")
        # Expected format: bytes 0-0/TOTAL or bytes 0-0/*
        match = re.search(r"bytes\s+(\d+)-(\d+)/(\d+|\*)", cr, re.IGNORECASE)
        if match:
            start, end, total = int(match.group(1)), int(match.group(2)), match.group(3)
            # Only consider verified range if start is 0
            if start == 0 and end == 0:
                supports_ranges = True
                if total != "*":
                    total_bytes = int(total)
        else:
            # Server sent 206 but with non-compliant Content-Range
            supports_ranges = False

    elif status == 200:
        # Server ignored Range header! Must treat as non-splittable.
        supports_ranges = False
        content_len = resp.headers.get("Content-Length")
        if content_len and content_len.isdigit():
            total_bytes = int(content_len)
        else:
            total_bytes = None  # Unknown length stream

    else:
        resp.close()
        raise ProbeError(f"HTTP_{status}", f"Server returned unexpected HTTP status: {status}")

    # Consume small probe chunk and close stream cleanly
    try:
        resp.raw.read(1024)
    except Exception:
        pass
    resp.close()

    return HttpProbeResult(
        final_url=final_url,
        total_bytes=total_bytes,
        supports_ranges=supports_ranges,
        etag=etag,
        last_modified=last_modified,
        filename=extracted_filename,
        content_type=content_type
    )
