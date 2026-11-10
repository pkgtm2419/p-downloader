"""
Premiumize.me API Client for P-Downloader.
"""
from typing import Dict, Any, Optional
import requests

PREM_API_BASE = "https://www.premiumize.me/api"


class PremiumizeClient:
    def __init__(self, api_token: Optional[str] = None, timeout_sec: int = 15):
        self.api_token = api_token
        self.timeout_sec = timeout_sec

    def _get_headers(self) -> Dict[str, str]:
        headers = {"User-Agent": "P-Downloader/1.1.0"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def unrestrict_link(self, link: str) -> Dict[str, Any]:
        """
        Creates a direct unthrottled link via Premiumize transfer service.
        """
        url = f"{PREM_API_BASE}/transfer/create"
        data = {"src": link}
        resp = requests.post(url, headers=self._get_headers(), data=data, timeout=self.timeout_sec)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "success":
            raise RuntimeError(f"Premiumize error: {data.get('message', 'Transfer creation failed')}")
        return data
