"""
Unit and integration tests for Phase 5:
VPN Exclusive Fail-Closed Kill-Switch, DNS-over-HTTPS (DoH), and Geo-IP resolution.
"""
import unittest
from unittest.mock import patch, MagicMock

from core.network_binder import NetworkManager, NetworkInterface
from core.network_routes import NetworkRoute, get_session_for_route
from core.dns_doh import DOHResolver
from core.geoip import GeoIPService, country_code_to_flag, lookup_server_geoip, GeoIPInfo


class TestPrivacyVPNAndGeoIP(unittest.TestCase):
    def setUp(self):
        self.net_mgr = NetworkManager()
        self.net_mgr.set_vpn_exclusive(None, enabled=False, fail_closed=False)

    def tearDown(self):
        self.net_mgr.set_vpn_exclusive(None, enabled=False, fail_closed=False)

    def test_vpn_exclusive_fail_closed_killswitch(self):
        # 1. Enable fail-closed killswitch for a fake down VPN adapter IP
        fake_vpn_ip = "10.254.254.254"
        self.net_mgr.set_vpn_exclusive(fake_vpn_ip, enabled=True, fail_closed=True)

        # 2. Attempting to get a session must fail closed and raise ConnectionError
        with self.assertRaises(ConnectionError) as ctx:
            self.net_mgr.get_session_for_interface()
        self.assertIn("Fail-Closed Killswitch", str(ctx.exception))

        # 3. Disable killswitch: normal session is returned
        self.net_mgr.set_vpn_exclusive(None, enabled=False, fail_closed=False)
        session = self.net_mgr.get_session_for_interface()
        self.assertIsNotNone(session)

    def test_network_routes_fail_closed(self):
        down_route = NetworkRoute(
            id="vpn-down",
            device="tun0",
            source_ip="10.8.0.2",
            address_family="ipv4",
            oper_state="down"
        )
        with self.assertRaises(ConnectionError):
            get_session_for_route(down_route, fail_closed=True)

        up_route = NetworkRoute(
            id="eth0-up",
            device="eth0",
            source_ip="192.168.1.100",
            address_family="ipv4",
            oper_state="up"
        )
        session = get_session_for_route(up_route, fail_closed=True)
        self.assertIsNotNone(session)

    def test_doh_resolver_caching_and_literal_ip(self):
        resolver = DOHResolver(provider="cloudflare")
        # Literal IP should bypass DNS queries
        res = resolver.resolve("127.0.0.1")
        self.assertEqual(res, ["127.0.0.1"])

        # Mock DoH query
        mock_payload = (
            b'{"Status":0,"Answer":[{"name":"example.com","type":1,"TTL":300,"data":"93.184.216.34"}]}'
        )
        with patch("urllib.request.urlopen") as mock_url:
            mock_resp = MagicMock()
            mock_resp.read.return_value = mock_payload
            mock_resp.__enter__.return_value = mock_resp
            mock_url.return_value = mock_resp

            ips = resolver.resolve("example.com")
            self.assertEqual(ips, ["93.184.216.34"])

            # Second call should hit in-memory cache without calling urlopen again
            mock_url.reset_mock()
            ips_cached = resolver.resolve("example.com")
            self.assertEqual(ips_cached, ["93.184.216.34"])
            mock_url.assert_not_called()

    def test_geoip_flags_and_lookup(self):
        self.assertEqual(country_code_to_flag("US"), "🇺🇸")
        self.assertEqual(country_code_to_flag("DE"), "🇩🇪")
        self.assertEqual(country_code_to_flag("JP"), "🇯🇵")
        self.assertEqual(country_code_to_flag(""), "🌐")

        # Test localhost / local network lookup
        local_info = lookup_server_geoip("127.0.0.1", measure_ping=False)
        self.assertEqual(local_info.country_code, "LOCAL")
        self.assertEqual(local_info.flag, "🏠")

        # Test URL parsing
        url_info = lookup_server_geoip("http://127.0.0.1:8080/path/test.bin", measure_ping=False)
        self.assertEqual(url_info.country_code, "LOCAL")

        # Test dictionary export
        d = local_info.to_dict()
        self.assertEqual(d["country_code"], "LOCAL")
        self.assertEqual(d["flag"], "🏠")


if __name__ == "__main__":
    unittest.main()
