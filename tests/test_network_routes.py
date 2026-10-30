"""
Unit tests for OS network adapter and route discovery.
"""
import unittest
from core.network_routes import list_routes, get_session_for_route, NetworkRoute

class TestNetworkRoutes(unittest.TestCase):
    def test_list_routes_returns_valid_adapters(self):
        """list_routes discovers outbound routes and ignores loopback."""
        routes = list_routes()
        self.assertGreater(len(routes), 0)
        for r in routes:
            self.assertNotEqual(r.source_ip, "127.0.0.1")
            self.assertNotEqual(r.source_ip, "::1")
            self.assertIn(r.address_family, ("ipv4", "ipv6"))

    def test_get_session_for_route(self):
        """Bound session is successfully constructed for route."""
        route = NetworkRoute(
            id="test-route-1",
            device="eth0",
            source_ip="127.0.0.1",
            address_family="ipv4"
        )
        session = get_session_for_route(route)
        self.assertIsNotNone(session)
        self.assertIn("http://", session.adapters)
        self.assertIn("https://", session.adapters)


if __name__ == "__main__":
    unittest.main()
