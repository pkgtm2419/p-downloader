"""
DNS-over-HTTPS (DoH) Resolver for P-Downloader.
Provides private encrypted DNS resolution via Cloudflare, Quad9, Google,
or custom DoH providers, preventing ISP tracking, DNS spoofing, and SNI inspection leaks.
"""
import time
import socket
import urllib.request
import urllib.parse
import json
import threading
from typing import List, Dict, Tuple, Optional

DOH_PROVIDERS = {
    "cloudflare": "https://cloudflare-dns.com/dns-query",
    "quad9": "https://dns.quad9.net/dns-query",
    "google": "https://dns.google/resolve",
    "system": "system"
}


class DOHResolver:
    """
    Thread-safe DNS-over-HTTPS resolver with TTL caching and fallback support.
    """
    def __init__(self, provider: str = "cloudflare", custom_url: Optional[str] = None, timeout: float = 3.0):
        self.provider = provider.lower()
        self.custom_url = custom_url
        self.timeout = timeout
        self._cache: Dict[Tuple[str, str], Tuple[List[str], float]] = {}
        self._lock = threading.Lock()

    def get_endpoint(self) -> str:
        if self.custom_url:
            return self.custom_url
        return DOH_PROVIDERS.get(self.provider, DOH_PROVIDERS["cloudflare"])

    def resolve(self, hostname: str, record_type: str = "A") -> List[str]:
        """
        Resolves hostname to IP addresses.
        Checks cache first; if expired, queries DoH provider.
        Falls back to system DNS if DoH fails.
        """
        # Do not resolve literal IP addresses
        try:
            socket.inet_aton(hostname)
            return [hostname]
        except (socket.error, OSError):
            pass

        key = (hostname.lower(), record_type.upper())
        now = time.time()

        with self._lock:
            if key in self._cache:
                ips, expire_at = self._cache[key]
                if now < expire_at:
                    return ips

        if self.provider == "system":
            return self._resolve_system(hostname)

        try:
            ips, ttl = self._query_doh(hostname, record_type)
            if ips:
                with self._lock:
                    self._cache[key] = (ips, now + max(60, ttl))
                return ips
        except Exception:
            pass

        # Fallback to system DNS
        return self._resolve_system(hostname)

    def _resolve_system(self, hostname: str) -> List[str]:
        try:
            results = socket.getaddrinfo(hostname, None, socket.AF_INET)
            ips = list({res[4][0] for res in results})
            return ips if ips else [hostname]
        except Exception:
            return []

    def _query_doh(self, hostname: str, record_type: str) -> Tuple[List[str], int]:
        endpoint = self.get_endpoint()
        params = urllib.parse.urlencode({
            "name": hostname,
            "type": record_type
        })
        url = f"{endpoint}?{params}"
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/dns-json",
                "User-Agent": "P-Downloader-DoH/1.1"
            }
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        answers = data.get("Answer", [])
        ips: List[str] = []
        min_ttl = 300

        for ans in answers:
            # type 1 is A (IPv4), type 28 is AAAA (IPv6)
            data_val = ans.get("data", "")
            ttl = ans.get("TTL", 300)
            if ttl < min_ttl:
                min_ttl = ttl
            if data_val:
                ips.append(data_val)

        return ips, min_ttl

    def clear_cache(self):
        with self._lock:
            self._cache.clear()


# Global default resolver
_default_resolver = DOHResolver(provider="system")

def get_resolver() -> DOHResolver:
    return _default_resolver

def set_resolver_provider(provider: str, custom_url: Optional[str] = None):
    global _default_resolver
    _default_resolver = DOHResolver(provider=provider, custom_url=custom_url)
