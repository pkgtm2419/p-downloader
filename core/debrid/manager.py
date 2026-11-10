"""
Unified Debrid Manager for P-Downloader.
Detects supported premium file-hoster links and routes them through configured
debrid service providers (Real-Debrid, AllDebrid, Premiumize) for unthrottled downloads.
"""
from urllib.parse import urlparse
from typing import Optional, Tuple, Dict, Any
from .real_debrid import RealDebridClient
from .alldebrid import AllDebridClient
from .premiumize import PremiumizeClient

SUPPORTED_HOSTERS = {
    "rapidgator.net", "rg.to",
    "1fichier.com",
    "turbobit.net",
    "mega.nz",
    "nitroflare.com",
    "ddownload.com",
    "katfile.com",
    "fikper.com",
    "filefactory.com",
    "uptobox.com"
}


class DebridManager:
    def __init__(self, db=None):
        if db is None:
            from core.db import DownloadDB
            db = DownloadDB()
        self.db = db

    def is_debrid_host(self, url: str) -> bool:
        """Returns True if the URL domain matches a supported file-hoster."""
        if not url:
            return False
        try:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            for h in SUPPORTED_HOSTERS:
                if host == h or host.endswith("." + h):
                    return True
            return False
        except Exception:
            return False

    def get_active_client(self) -> Optional[Tuple[str, Any]]:
        """
        Returns the first configured and active Debrid client (provider_name, client_instance).
        """
        rd_token = self.db.get_setting("debrid_rd_token", "").strip()
        if rd_token:
            return "real_debrid", RealDebridClient(api_token=rd_token)

        ad_token = self.db.get_setting("debrid_ad_token", "").strip()
        if ad_token:
            return "alldebrid", AllDebridClient(api_token=ad_token)

        prem_token = self.db.get_setting("debrid_prem_token", "").strip()
        if prem_token:
            return "premiumize", PremiumizeClient(api_token=prem_token)

        return None

    def unrestrict_link(self, url: str, password: Optional[str] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Attempts to unrestrict a file-hoster link via the active debrid provider.
        Returns: (success: bool, final_url: str, metadata: dict).
        """
        if not self.is_debrid_host(url):
            return False, url, {}

        active = self.get_active_client()
        if not active:
            return False, url, {}

        provider, client = active
        try:
            if provider == "real_debrid":
                data = client.unrestrict_link(url, password=password)
                direct = data.get("download") or url
                return True, direct, data
            elif provider == "alldebrid":
                data = client.unrestrict_link(url, password=password)
                direct = data.get("link") or url
                return True, direct, data
            elif provider == "premiumize":
                data = client.unrestrict_link(url)
                direct = data.get("location") or url
                return True, direct, data
        except Exception as e:
            return False, url, {"error": str(e)}

        return False, url, {}
