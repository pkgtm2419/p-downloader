"""Networking and socket security package."""
from .resolver_pin import is_safe_url, resolve_and_validate_host, is_ip_prohibited

__all__ = ["is_safe_url", "resolve_and_validate_host", "is_ip_prohibited"]
