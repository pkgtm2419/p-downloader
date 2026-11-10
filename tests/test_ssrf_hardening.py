"""
Comprehensive SSRF hardening tests (IM-09).
Validates IPv4 and IPv6 resolution, cloud metadata blocking,
IPv4-mapped IPv6 address filtering, and hermetic mock resolvers.
"""
import unittest

from core.net.resolver_pin import is_safe_url, resolve_and_validate_host, is_ip_prohibited
from core.spider import is_safe_external_url
import ipaddress


class TestSSRFHardening(unittest.TestCase):
    def test_prohibited_ip_literals(self):
        blocked_ips = [
            "127.0.0.1",
            "::1",
            "169.254.169.254",
            "0.0.0.0",
            "::",
            "10.0.0.1",
            "192.168.1.1",
            "172.16.5.10",
            "::ffff:10.0.0.1",
            "::ffff:127.0.0.1",
            "::ffff:169.254.169.254",
            "224.0.0.1",  # Multicast
            "240.0.0.1"   # Reserved
        ]

        for ip_str in blocked_ips:
            ip = ipaddress.ip_address(ip_str)
            self.assertTrue(is_ip_prohibited(ip), f"Failed to prohibit: {ip_str}")
            url = f"http://[{ip_str}]/test" if ":" in ip_str else f"http://{ip_str}/test"
            self.assertFalse(is_safe_url(url), f"Failed to block URL: {url}")
            self.assertFalse(is_safe_external_url(url), f"Spider failed to block URL: {url}")

    def test_safe_public_ip_literals(self):
        safe_ips = [
            "93.184.216.34",
            "1.1.1.1",
            "8.8.8.8",
            "2606:4700:4700::1111"
        ]

        for ip_str in safe_ips:
            ip = ipaddress.ip_address(ip_str)
            self.assertFalse(is_ip_prohibited(ip), f"Falsely prohibited: {ip_str}")
            url = f"https://[{ip_str}]/video.mp4" if ":" in ip_str else f"https://{ip_str}/video.mp4"
            self.assertTrue(is_safe_url(url), f"Failed to allow safe URL: {url}")

    def test_hermetic_custom_resolver_hostname(self):
        # 1. Custom resolver returning public IP
        def mock_resolver_public(hostname: str):
            return ["93.184.216.34"]

        self.assertTrue(is_safe_url("https://example.com/file.zip", custom_resolver=mock_resolver_public))
        pinned = resolve_and_validate_host("example.com", custom_resolver=mock_resolver_public)
        self.assertEqual(pinned, ["93.184.216.34"])

        # 2. Custom resolver attempting DNS rebinding to internal IP
        def mock_resolver_rebinding(hostname: str):
            return ["192.168.1.50"]

        self.assertFalse(is_safe_url("https://attacker-rebinding.com/steal", custom_resolver=mock_resolver_rebinding))
        with self.assertRaises(ValueError) as ctx:
            resolve_and_validate_host("attacker-rebinding.com", custom_resolver=mock_resolver_rebinding)
        self.assertIn("prohibited IP", str(ctx.exception))

    def test_cloud_metadata_hostnames_blocked(self):
        self.assertFalse(is_safe_url("http://metadata.google.internal/computeMetadata/v1/"))
        self.assertFalse(is_safe_url("http://instance-data/latest/meta-data/"))


if __name__ == "__main__":
    unittest.main()
