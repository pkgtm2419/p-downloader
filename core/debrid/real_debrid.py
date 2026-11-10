"""
Real-Debrid API Client for P-Downloader.
Provides OAuth device authorization, file-hoster link unrestriction, and cloud torrent resolution.
"""
from typing import Dict, Any, Optional, Tuple
import requests

RD_API_BASE = "https://api.real-debrid.com/rest/1.0"
RD_OAUTH_BASE = "https://api.real-debrid.com/oauth/v2"
RD_CLIENT_ID = "X245A4XAIBGVM"


class RealDebridClient:
    def __init__(self, api_token: Optional[str] = None, timeout_sec: int = 15):
        self.api_token = api_token
        self.timeout_sec = timeout_sec

    def _get_headers(self) -> Dict[str, str]:
        headers = {"User-Agent": "P-Downloader/1.1.0"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def get_device_code(self) -> Dict[str, Any]:
        """
        Initiates OAuth Device Code flow: returns device_code, user_code, verification_url.
        """
        url = f"{RD_OAUTH_BASE}/device/code?client_id={RD_CLIENT_ID}&new_credentials=yes"
        resp = requests.get(url, headers={"User-Agent": "P-Downloader/1.1.0"}, timeout=self.timeout_sec)
        resp.raise_for_status()
        return resp.json()

    def credentials_from_device(self, device_code: str) -> Dict[str, Any]:
        """
        Polls for user authorization on real-debrid.com/device.
        """
        url = f"{RD_OAUTH_BASE}/device/credentials?client_id={RD_CLIENT_ID}&code={device_code}"
        resp = requests.get(url, headers={"User-Agent": "P-Downloader/1.1.0"}, timeout=self.timeout_sec)
        resp.raise_for_status()
        return resp.json()

    def get_user_info(self) -> Dict[str, Any]:
        """Returns account details, premium expiration, and points."""
        url = f"{RD_API_BASE}/user"
        resp = requests.get(url, headers=self._get_headers(), timeout=self.timeout_sec)
        resp.raise_for_status()
        return resp.json()

    def unrestrict_link(self, link: str, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Unrestricts a file-hoster URL (Rapidgator, 1fichier, Turbobit, Mega, etc.)
        Returns dict containing: id, filename, download (direct link), filesize, mimeType.
        """
        url = f"{RD_API_BASE}/unrestrict/link"
        data = {"link": link}
        if password:
            data["password"] = password

        resp = requests.post(url, headers=self._get_headers(), data=data, timeout=self.timeout_sec)
        resp.raise_for_status()
        return resp.json()

    def add_magnet(self, magnet_uri: str) -> Dict[str, Any]:
        """
        Uploads a Magnet link to Real-Debrid cloud torrents.
        """
        url = f"{RD_API_BASE}/torrents/addMagnet"
        data = {"magnet": magnet_uri}
        resp = requests.post(url, headers=self._get_headers(), data=data, timeout=self.timeout_sec)
        resp.raise_for_status()
        return resp.json()

    def get_torrent_info(self, torrent_id: str) -> Dict[str, Any]:
        url = f"{RD_API_BASE}/torrents/info/{torrent_id}"
        resp = requests.get(url, headers=self._get_headers(), timeout=self.timeout_sec)
        resp.raise_for_status()
        return resp.json()
