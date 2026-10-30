"""
Origin-scoped authentication and secret-safe request context manager.
Prevents leaking cookies, bearer tokens, or session credentials across redirects.
"""
from urllib.parse import urlparse
from typing import Optional, Dict
from .download_models import BrowserRequestContext

DISALLOWED_HEADERS = {"host", "content-length", "transfer-encoding", "connection"}

def get_effective_origin(url: str) -> str:
    """Extract scheme://netloc for effective origin matching."""
    parsed = urlparse(url)
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"

def sanitize_header_value(val: str) -> str:
    """Strip dangerous control characters and newlines to prevent header injection."""
    if not val:
        return ""
    # Disallow CRLF
    return val.replace("\r", "").replace("\n", "").strip()

def headers_for_target(
    context: Optional[BrowserRequestContext],
    target_url: str,
    redirect_from: Optional[str] = None
) -> Dict[str, str]:
    """
    Generate HTTP request headers strictly scoped to target origin.
    Drops sensitive auth tokens and cookies if redirected to a different origin.
    """
    headers: Dict[str, str] = {
        "Accept": "*/*",
        "Accept-Encoding": "identity"
    }

    if not context:
        return headers

    if context.user_agent:
        headers["User-Agent"] = sanitize_header_value(context.user_agent)

    target_origin = get_effective_origin(target_url)
    is_cross_origin = False

    if redirect_from:
        initial_origin = get_effective_origin(redirect_from)
        if initial_origin != target_origin:
            is_cross_origin = True

    # Same-origin or initial origin headers
    if target_origin in context.per_origin_headers and not is_cross_origin:
        origin_hdrs = context.per_origin_headers[target_origin]
        for k, v in origin_hdrs.items():
            k_clean = k.strip()
            if k_clean.lower() in DISALLOWED_HEADERS:
                continue
            headers[k_clean] = sanitize_header_value(v)

    # Scoped referer
    if context.referrer:
        ref_origin = get_effective_origin(context.referrer)
        if ref_origin == target_origin:
            headers["Referer"] = sanitize_header_value(context.referrer)

    return headers
