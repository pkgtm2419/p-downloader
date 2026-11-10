"""
AllDebrid API Client for P-Downloader.
"""
from typing import Dict, Any, Optional
import requests

AD_API_BASE = "https://api.alldebrid.com/v4"
AD_AGENT = "pdownloader"


class AllDebridClient:
    def __init__(self, api_token: Optional[str] = None, timeout_sec: int = 15):
        self.api_token = api_token
        self.timeout_sec = timeout_sec

    def _get_headers(self) -> Dict[str, str]:
        headers = {"User-Agent": "P-Downloader/1.1.0"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def unrestrict_link(self, link: str, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Unlocks file-hoster link via AllDebrid.
        """
        url = f"{AD_API_BASE}/link/unlock?agent={AD_AGENT}"
        params = {"link": link}
        if password:
            params["password"] = password

        resp = requests.get(url, headers=self._get_headers(), params=params, timeout=self.timeout_sec)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "success":
            raise RuntimeError(f"AllDebrid error: {data.get('error', {}).get('message', 'Unlock failed')}")
        return data.get("data", {})

    def add_magnet(self, magnet_uri: str) -> Dict[str, Any]:
        url = f"{AD_API_BASE}/magnet/upload?agent={AD_AGENT}"
        data = {"magnets[]": magnet_uri}
        resp = requests.post(url, headers=self._get_headers(), data=data, timeout=self.timeout_sec)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "success":
            raise RuntimeError(f"AllDebrid error: {data.get('error', {}).get('message', 'Magnet upload failed')}")
        return data.get("data", {})
