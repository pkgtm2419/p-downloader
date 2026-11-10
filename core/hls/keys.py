"""
HLS Key Manager and Decryptor (IM-01).
Handles AES-128-CBC decryption, explicit and sequence-derived IVs (RFC 8216 Section 5.2),
PKCS#7 unpadding, key caching, and DRM detection.
"""
from typing import Dict, Optional, Any
import requests

from core.errors import AppError, ErrorCode


class HLSKeyManager:
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self._key_cache: Dict[str, bytes] = {}

    def get_key(self, key_url: str, timeout: float = 12.0) -> bytes:
        if not key_url:
            raise AppError(ErrorCode.INTERNAL, "Missing key URI in encrypted HLS stream.")
        if key_url in self._key_cache:
            return self._key_cache[key_url]

        resp = self.session.get(key_url, timeout=timeout)
        resp.raise_for_status()
        key_bytes = resp.content
        if len(key_bytes) != 16:
            raise AppError(
                ErrorCode.INTERNAL,
                f"Invalid AES-128 key length ({len(key_bytes)} bytes; expected 16 bytes)."
            )
        self._key_cache[key_url] = key_bytes
        return key_bytes

    def decrypt_segment(self, data: bytes, key_info: Dict[str, Any], sequence_number: int) -> bytes:
        method = key_info.get("method", "NONE").upper()

        if method == "NONE" or not method:
            return data

        if method in ("SAMPLE-AES", "SAMPLE-AES-CTR") or "widevine" in str(key_info.get("url", "")).lower():
            raise AppError(
                ErrorCode.DRM_PROTECTED,
                f"HLS stream uses protected encryption ({method}). It cannot be saved."
            )

        if method != "AES-128":
            raise AppError(
                ErrorCode.INTERNAL,
                f"Unsupported HLS encryption method: {method}"
            )

        key_url = key_info.get("url", "")
        aes_key = self.get_key(key_url)

        # Derive IV: explicit IV or 16-byte big-endian sequence number
        iv_hex = key_info.get("iv")
        if iv_hex:
            iv_clean = iv_hex.replace("0x", "").replace("0X", "").zfill(32)
            iv_bytes = bytes.fromhex(iv_clean)
        else:
            iv_bytes = sequence_number.to_bytes(16, byteorder="big")

        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import padding

            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv_bytes), backend=default_backend())
            decryptor = cipher.decryptor()
            raw_decrypted = decryptor.update(data) + decryptor.finalize()

            # Apply PKCS#7 unpadding
            try:
                unpadder = padding.PKCS7(128).unpadder()
                return unpadder.update(raw_decrypted) + unpadder.finalize()
            except Exception:
                return raw_decrypted

        except ImportError:
            raise AppError(
                ErrorCode.INTERNAL,
                "The 'cryptography' package is required for AES-128 HLS decryption."
            )
