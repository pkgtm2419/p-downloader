"""
Real OS network adapter discovery, routing information, and route-bound HTTP sessions.
"""
import socket
from dataclasses import dataclass
from typing import List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.connection import create_connection

@dataclass
class NetworkRoute:
    id: str
    device: str
    source_ip: str
    address_family: str  # "ipv4" or "ipv6"
    gateway: Optional[str] = None
    metered: bool = False
    oper_state: str = "up"  # "up" or "down"

@dataclass
class RouteHealth:
    route_id: str
    reachable: bool
    latency_ms: float
    status: str

class SourceAddressAdapter(HTTPAdapter):
    """HTTPAdapter binding requests to a designated local IP address."""
    def __init__(self, source_ip: str, **kwargs):
        self.source_ip = source_ip
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["source_address"] = (self.source_ip, 0)
        return super().init_poolmanager(*args, **kwargs)


def list_routes() -> List[NetworkRoute]:
    """
    Enumerate active network adapters and outbound routes on the host.
    Filters out loopback (127.0.0.1 / ::1) and link-local addresses.
    """
    routes: List[NetworkRoute] = []

    try:
        import psutil
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for dev_name, nic_addrs in addrs.items():
            stat = stats.get(dev_name)
            oper_state = "up" if (stat and stat.isup) else "down"

            for a in nic_addrs:
                if a.family == socket.AF_INET:
                    ip = a.address
                    if ip.startswith("127.") or ip.startswith("169.254."):
                        continue
                    routes.append(NetworkRoute(
                        id=f"{dev_name}-ipv4",
                        device=dev_name,
                        source_ip=ip,
                        address_family="ipv4",
                        oper_state=oper_state
                    ))
                elif hasattr(socket, "AF_INET6") and a.family == socket.AF_INET6:
                    ip = a.address
                    if ip == "::1" or ip.startswith("fe80:"):
                        continue
                    routes.append(NetworkRoute(
                        id=f"{dev_name}-ipv6",
                        device=dev_name,
                        source_ip=ip,
                        address_family="ipv6",
                        oper_state=oper_state
                    ))
    except Exception:
        # Fallback to standard socket discovery
        try:
            hostname = socket.gethostname()
            for ip in socket.gethostbyname_ex(hostname)[2]:
                if not ip.startswith("127."):
                    routes.append(NetworkRoute(
                        id=f"default-{ip}",
                        device="default",
                        source_ip=ip,
                        address_family="ipv4",
                        oper_state="up"
                    ))
        except Exception:
            pass

    if not routes:
        # Default fallback
        routes.append(NetworkRoute(
            id="default-route",
            device="default",
            source_ip="0.0.0.0",
            address_family="ipv4",
            oper_state="up"
        ))

    return routes


def verify_route(route: NetworkRoute, target_host: str = "127.0.0.1", port: int = 80, timeout_s: float = 2.0) -> RouteHealth:
    """Check if designated local route can establish an outbound socket connection."""
    import time
    start = time.time()
    try:
        s = socket.socket(socket.AF_INET if route.address_family == "ipv4" else socket.AF_INET6, socket.SOCK_STREAM)
        s.settimeout(timeout_s)
        if route.source_ip not in ("0.0.0.0", "::"):
            s.bind((route.source_ip, 0))
        s.connect((target_host, port))
        s.close()
        elapsed = (time.time() - start) * 1000
        return RouteHealth(route_id=route.id, reachable=True, latency_ms=elapsed, status="healthy")
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return RouteHealth(route_id=route.id, reachable=False, latency_ms=elapsed, status=str(e))


def get_session_for_route(route: Optional[NetworkRoute]) -> requests.Session:
    """Return requests.Session bound to the specific network route."""
    session = requests.Session()
    if route and route.source_ip and route.source_ip not in ("0.0.0.0", "::"):
        adapter = SourceAddressAdapter(route.source_ip)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
    return session
