"""
Geo-IP and Server Country Resolution for P-Downloader.
Identifies host server geographic location, displays country flag emoji,
and measures TCP round-trip latency to remote servers.
"""
import time
import socket
import json
import urllib.request
import threading
from dataclasses import dataclass
from typing import Optional, Dict

COUNTRY_NAMES = {
    "US": "United States",
    "CA": "Canada",
    "GB": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "NL": "Netherlands",
    "JP": "Japan",
    "AU": "Australia",
    "IN": "India",
    "SG": "Singapore",
    "BR": "Brazil",
    "RU": "Russia",
    "CH": "Switzerland",
    "SE": "Sweden",
    "KR": "South Korea",
    "LOCAL": "Local Network"
}


def country_code_to_flag(code: str) -> str:
    """Converts 2-letter ISO country code into Unicode flag emoji."""
    if not code or len(code) != 2:
        return "🌐"
    code = code.upper()
    try:
        return "".join(chr(0x1F1E6 + ord(c) - 65) for c in code)
    except Exception:
        return "🌐"


@dataclass
class GeoIPInfo:
    ip: str
    country_code: str
    country_name: str
    flag: str
    ping_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "country_code": self.country_code,
            "country_name": self.country_name,
            "flag": self.flag,
            "ping_ms": round(self.ping_ms, 1)
        }


class GeoIPService:
    def __init__(self):
        self._cache: Dict[str, GeoIPInfo] = {}
        self._lock = threading.Lock()

    def measure_latency(self, ip_or_host: str, port: int = 443, timeout: float = 1.5) -> float:
        """
        Measures TCP handshake latency (in ms) to the target host/IP.
        """
        start = time.time()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((ip_or_host, port))
            s.close()
            return (time.time() - start) * 1000.0
        except Exception:
            # Try port 80 if 443 failed
            if port != 80:
                try:
                    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s2.settimeout(timeout)
                    s2.connect((ip_or_host, 80))
                    s2.close()
                    return (time.time() - start) * 1000.0
                except Exception:
                    pass
            return 0.0

    def resolve_ip(self, host: str) -> str:
        try:
            socket.inet_aton(host)
            return host
        except (socket.error, OSError):
            pass
        try:
            return socket.gethostbyname(host)
        except Exception:
            return host

    def lookup(self, host_or_ip: str, measure_ping: bool = True) -> GeoIPInfo:
        """
        Looks up country code and flag for the given host or IP.
        """
        ip = self.resolve_ip(host_or_ip)
        with self._lock:
            if ip in self._cache:
                info = self._cache[ip]
                if measure_ping and info.ping_ms <= 0:
                    info.ping_ms = self.measure_latency(ip)
                return info

        # Check local / private address spaces
        if ip.startswith("127.") or ip == "localhost" or ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.16."):
            info = GeoIPInfo(
                ip=ip,
                country_code="LOCAL",
                country_name="Local Network",
                flag="🏠",
                ping_ms=self.measure_latency(ip) if measure_ping else 0.0
            )
            with self._lock:
                self._cache[ip] = info
            return info

        # Check known well-known DNS / CDN ranges
        known_code = "US"
        if ip.startswith("1.1.1.") or ip.startswith("1.0.0."):
            known_code = "US"
        elif ip.startswith("8.8.8.") or ip.startswith("8.8.4."):
            known_code = "US"
        elif ip.startswith("9.9.9."):
            known_code = "CH"

        country_code = known_code
        country_name = COUNTRY_NAMES.get(country_code, country_code)

        # Attempt light online lookup with short timeout
        try:
            url = f"https://ipapi.co/{ip}/json/"
            req = urllib.request.Request(url, headers={"User-Agent": "P-Downloader/1.1"})
            with urllib.request.urlopen(req, timeout=1.2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                cc = data.get("country_code")
                cn = data.get("country_name")
                if cc:
                    country_code = cc
                    country_name = cn or COUNTRY_NAMES.get(country_code, country_code)
        except Exception:
            pass

        flag = country_code_to_flag(country_code)
        ping_ms = self.measure_latency(ip) if measure_ping else 0.0

        info = GeoIPInfo(
            ip=ip,
            country_code=country_code,
            country_name=country_name,
            flag=flag,
            ping_ms=ping_ms
        )
        with self._lock:
            self._cache[ip] = info
        return info


_default_geoip = GeoIPService()

def lookup_server_geoip(host_or_url: str, measure_ping: bool = True) -> GeoIPInfo:
    """
    Convenience function extracting host from URL or using raw hostname/IP.
    """
    from urllib.parse import urlparse
    if "://" in host_or_url:
        host = urlparse(host_or_url).hostname or host_or_url
    else:
        host = host_or_url.split(":")[0]
    return _default_geoip.lookup(host, measure_ping=measure_ping)
