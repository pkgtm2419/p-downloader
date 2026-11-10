"""
Debrid Service Integration for P-Downloader (Real-Debrid, AllDebrid, Premiumize).
"""
from .real_debrid import RealDebridClient
from .alldebrid import AllDebridClient
from .premiumize import PremiumizeClient
from .manager import DebridManager

__all__ = [
    "RealDebridClient",
    "AllDebridClient",
    "PremiumizeClient",
    "DebridManager"
]
