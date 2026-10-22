"""
Multi-Network Bandwidth Aggregation Engine.
Discovers active network interfaces (Wi-Fi, Ethernet, Mobile Hotspots/Tethering),
manages interface pooling, and binds HTTP segmented connections to specific physical adapters
for aggregate multi-path throughput (Plexo-grade bandwidth bonding).
"""
import os
import time
import socket
import subprocess
import json
import threading
from typing import List, Dict, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

class SourceAddressAdapter(HTTPAdapter):
    """
    HTTPAdapter that binds outgoing TCP connections to a specific local IP address,
    forcing packets over a chosen network interface.
    """
    def __init__(self, source_address: str, **kwargs):
        self.source_address = (source_address, 0)
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['source_address'] = self.source_address
        return super().init_poolmanager(*args, **kwargs)

class NetworkInterface:
    def __init__(
        self,
        alias: str,
        ip: str,
        interface_index: int = 0,
        is_default: bool = False,
        enabled: bool = True,
        is_metered: bool = False
    ):
        self.alias = alias
        self.ip = ip
        self.interface_index = interface_index
        self.is_default = is_default
        self.enabled = enabled
        self.is_metered = is_metered
        self.bytes_downloaded: int = 0
        self.speed: float = 0.0
        self._last_bytes: int = 0
        self._last_time: float = time.time()

    def record_bytes(self, byte_count: int):
        self.bytes_downloaded += byte_count

    def update_speed(self):
        now = time.time()
        elapsed = now - self._last_time
        if elapsed >= 0.5:
            delta = self.bytes_downloaded - self._last_bytes
            self.speed = delta / elapsed
            self._last_time = now
            self._last_bytes = self.bytes_downloaded

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alias": self.alias,
            "ip": self.ip,
            "interface_index": self.interface_index,
            "is_default": self.is_default,
            "enabled": self.enabled,
            "is_metered": self.is_metered,
            "bytes_downloaded": self.bytes_downloaded,
            "speed": self.speed
        }

class NetworkManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(NetworkManager, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self.interfaces: Dict[str, NetworkInterface] = {}
        self.bonding_enabled: bool = True
        self.refresh_interfaces()

    def refresh_interfaces(self) -> List[NetworkInterface]:
        """
        Discovers all active IPv4 interfaces using pure standard library networking.
        Fast, lightweight, and triggers zero security/process-spawning alerts.
        """
        discovered: Dict[str, NetworkInterface] = {}
        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
                ip = info[4][0]
                if not ip.startswith("127.") and not ip.startswith("169.254.") and ip not in discovered:
                    existing = self.interfaces.get(ip)
                    enabled = existing.enabled if existing else True
                    metered = existing.is_metered if existing else False
                    discovered[ip] = NetworkInterface(
                        alias=f"Network Adapter ({ip})",
                        ip=ip,
                        is_default=(len(discovered) == 0),
                        enabled=enabled,
                        is_metered=metered
                    )
        except Exception:
            pass

        if not discovered:
            discovered["0.0.0.0"] = NetworkInterface(
                alias="Default Route",
                ip="0.0.0.0",
                is_default=True,
                enabled=True
            )

        self.interfaces = discovered
        return list(self.interfaces.values())

    def get_active_interfaces(self) -> List[NetworkInterface]:
        """
        Returns list of user-enabled network interfaces.
        """
        if not self.interfaces:
            self.refresh_interfaces()
        active = [ni for ni in self.interfaces.values() if ni.enabled]
        return active if active else list(self.interfaces.values())

    def get_session_for_interface(self, ip: Optional[str] = None) -> requests.Session:
        """
        Creates a requests.Session bound to a specific network interface's IP.
        If IP is None or not available, returns a standard unbound Session.
        """
        session = requests.Session()
        if self.bonding_enabled and ip and ip in self.interfaces:
            try:
                adapter = SourceAddressAdapter(ip)
                session.mount("http://", adapter)
                session.mount("https://", adapter)
            except Exception:
                pass
        return session

    def get_interface_for_segment(self, segment_index: int) -> Optional[NetworkInterface]:
        """
        Assigns active interfaces round-robin to download segments.
        """
        active = self.get_active_interfaces()
        if not active or not self.bonding_enabled:
            return None
        return active[segment_index % len(active)]
