"""
Torrent and Magnet Link Processing Module for P-Downloader.
Provides Bencode/Bdecode parsing for .torrent files, Magnet URI resolution,
and metadata extraction (Plexo P2P capabilities) with recursion depth bounds (CWE-674).
"""
import os
import re
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import parse_qs, urlparse, unquote

MAX_BENCODE_DEPTH = 32
MAX_BENCODE_STRING_LEN = 50 * 1024 * 1024  # 50 MB

def bdecode(data: bytes, max_depth: int = MAX_BENCODE_DEPTH) -> Any:
    """
    Decodes standard bencoded data (BitTorrent specification).
    Enforces maximum nesting depth and byte string limits to prevent DoS.
    """
    def decode_func(x, f, depth=0):
        if depth > max_depth:
            raise ValueError(f"Exceeded maximum bencode nesting depth ({max_depth})")
        if f >= len(x):
            raise ValueError("Unexpected end of data")
        
        char = x[f:f+1]
        if char == b'i':
            # Integer: i<integer>e
            f += 1
            e = x.index(b'e', f)
            val = int(x[f:e])
            return val, e + 1
        elif char == b'l':
            # List: l<items>e
            f += 1
            r = []
            while x[f:f+1] != b'e':
                val, f = decode_func(x, f, depth + 1)
                r.append(val)
            return r, f + 1
        elif char == b'd':
            # Dict: d<key><value>e
            f += 1
            r = {}
            while x[f:f+1] != b'e':
                key, f = decode_func(x, f, depth + 1)
                val, f = decode_func(x, f, depth + 1)
                if isinstance(key, bytes):
                    key = key.decode("utf-8", errors="replace")
                r[key] = val
            return r, f + 1
        elif char.isdigit():
            # Byte string: <length>:<bytes>
            colon = x.index(b':', f)
            length = int(x[f:colon])
            if length < 0 or length > MAX_BENCODE_STRING_LEN:
                raise ValueError(f"Invalid or excessive byte string length: {length}")
            start = colon + 1
            val = x[start:start+length]
            return val, start + length
        else:
            raise ValueError(f"Unknown bencode type indicator: {char}")

    val, _ = decode_func(data, 0, 0)
    return val

def parse_magnet_uri(magnet_uri: str) -> Dict[str, Any]:
    """
    Parses a Magnet URI (urn:btih) into structured metadata:
    - info_hash (hex)
    - name (display name)
    - trackers (list of announce URLs)
    - exact_length (optional file size)
    """
    if not magnet_uri.lower().startswith("magnet:?"):
        raise ValueError("Invalid Magnet URI: missing magnet:? scheme")

    query = magnet_uri[len("magnet:?"):]
    params = parse_qs(query)

    info_hash = ""
    xt_list = params.get("xt", [])
    for xt in xt_list:
        if xt.lower().startswith("urn:btih:"):
            info_hash = xt[len("urn:btih:"):]
            break

    name = params.get("dn", [""])[0]
    trackers = params.get("tr", [])
    length_str = params.get("xl", ["0"])[0]
    try:
        length = int(length_str)
    except ValueError:
        length = 0

    return {
        "info_hash": info_hash,
        "name": name,
        "trackers": trackers,
        "length": length,
        "raw_uri": magnet_uri
    }

def is_torrent_or_magnet(uri_or_path: str) -> bool:
    """
    Determines if a target is a Magnet URI or a local .torrent file.
    """
    if not uri_or_path:
        return False
    lower = uri_or_path.strip().lower()
    if lower.startswith("magnet:?xt=urn:btih:"):
        return True
    if lower.endswith(".torrent"):
        return True
    return False

def inspect_torrent_file(file_path: str) -> Dict[str, Any]:
    """
    Reads a local .torrent file and returns file list, total size, and comment.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Torrent file not found: {file_path}")

    with open(file_path, "rb") as f:
        meta = bdecode(f.read())

    info = meta.get("info", {})
    name = info.get("name", "Unknown Torrent")
    if isinstance(name, bytes):
        name = name.decode("utf-8", errors="replace")

    files = []
    total_bytes = 0

    if "files" in info:
        # Multi-file torrent
        for item in info["files"]:
            length = item.get("length", 0)
            total_bytes += length
            path_parts = [p.decode("utf-8", errors="replace") if isinstance(p, bytes) else p for p in item.get("path", [])]
            files.append({
                "path": os.path.join(*path_parts),
                "length": length
            })
    else:
        # Single-file torrent
        total_bytes = info.get("length", 0)
        files.append({
            "path": name,
            "length": total_bytes
        })

    return {
        "name": name,
        "total_bytes": total_bytes,
        "files": files,
        "comment": meta.get("comment", "")
    }

# Compatibility alias
parse_torrent_file = inspect_torrent_file
