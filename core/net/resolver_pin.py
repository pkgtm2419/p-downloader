"""
SSRF Validation and IP Pinning Resolver (IM-09 / NF-11).
Resolves hostnames across IPv4 and IPv6 (A and AAAA), checks for loopback,
link-local, cloud metadata, RFC 1918 private, and IPv4-mapped IPv6 addresses.
Supports injectable resolvers for hermetic testing.
"""
import socket
import ipaddress
from urllib.parse import urlparse
from typing import List, Optional, Callable

PROHIBITED_HOSTS = {
    "localhost", "127.0.0.1", "::1", "0.0.0.0", "::",
    "169.254.169.254", "metadata.google.internal", "instance-data"
}


def is_ip_prohibited(ip: ipaddress._BaseAddress) -> bool:
    """Checks if an IP address is private, loopback, link-local, multicast, or cloud metadata."""
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
        return True

    # Check for IPv4-mapped IPv6 addresses (e.g. ::ffff:10.0.0.1, ::ffff:127.0.0.1)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        mapped_v4 = ip.ipv4_mapped
        if mapped_v4.is_private or mapped_v4.is_loopback or mapped_v4.is_link_local or mapped_v4.is_reserved:
            return True

    # Cloud metadata (169.254.169.254)
    if str(ip) == "169.254.169.254":
        return True

    return False


def resolve_and_validate_host(
    hostname: str,
    custom_resolver: Optional[Callable[[str], List[str]]] = None
) -> List[str]:
    """
    Resolves hostname across IPv4 and IPv6, validates all IP addresses,
    and returns a list of pinned safe public IP addresses.
    Raises ValueError if any address is private or prohibited.
    """
    hostname_clean = hostname.strip("[]").lower()
    if hostname_clean in PROHIBITED_HOSTS:
        raise ValueError(f"Prohibited hostname: {hostname_clean}")

    # Check if hostname is an IP literal (including hex, octal, decimal integers)
    try:
        ip = ipaddress.ip_address(hostname_clean)
        if is_ip_prohibited(ip):
            raise ValueError(f"Prohibited IP address literal: {ip}")
        return [str(ip)]
    except ValueError as ve:
        # If it was an invalid literal, check if it was prohibited before resolving
        if "Prohibited" in str(ve):
            raise

    # Resolve hostname
    resolved_ips: List[str] = []
    if custom_resolver:
        resolved_ips = custom_resolver(hostname_clean)
    else:
        try:
            # Query getaddrinfo for both IPv4 and IPv6
            addr_info = socket.getaddrinfo(hostname_clean, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            resolved_ips = list({entry[4][0] for entry in addr_info})
        except Exception as e:
            raise ValueError(f"Failed to resolve hostname '{hostname_clean}': {e}")

    if not resolved_ips:
        raise ValueError(f"No IP addresses found for hostname '{hostname_clean}'")

    # Validate EVERY resolved IP address
    for ip_str in resolved_ips:
        try:
            ip = ipaddress.ip_address(ip_str)
            if is_ip_prohibited(ip):
                raise ValueError(f"Hostname '{hostname_clean}' resolved to prohibited IP: {ip_str}")
        except ValueError as ve:
            if "Hostname" in str(ve):
                raise
            raise ValueError(f"Invalid resolved IP format '{ip_str}'")

    return resolved_ips


def is_safe_url(
    url: str,
    custom_resolver: Optional[Callable[[str], List[str]]] = None
) -> bool:
    """
    Validates that a URL uses http/https and targets a safe public host.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False

        resolve_and_validate_host(hostname, custom_resolver=custom_resolver)
        return True
    except Exception:
        return False
