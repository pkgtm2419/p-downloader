"""
Torrent and Magnet Link Processing Module for P-Downloader.
Provides Bencode/Bdecode parsing for .torrent files, Magnet URI resolution,
and metadata extraction (Plexo P2P capabilities).
"""
import os
import re
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import parse_qs, urlparse, unquote

def bdecode(data: bytes) -> Any:
    """
    Decodes standard bencoded data (BitTorrent specification).
    """
    def decode_func(x, f):
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
                val, f = decode_func(x, f)
                r.append(val)
            return r, f + 1
        elif char == b'd':
            # Dict: d<key><value>e
            f += 1
            r = {}
            while x[f:f+1] != b'e':
                key, f = decode_func(x, f)
                val, f = decode_func(x, f)
                if isinstance(key, bytes):
                    key = key.decode("utf-8", errors="replace")
                r[key] = val
            return r, f + 1
        elif char.isdigit():
            # Byte string: <length>:<bytes>
            colon = x.index(b':', f)
            length = int(x[f:colon])
            start = colon + 1
            val = x[start:start+length]
            return val, start + length
        else:
            raise ValueError(f"Unknown bencode type indicator: {char}")

    val, _ = decode_func(data, 0)
    return val

def parse_magnet_uri(uri: str) -> Dict[str, Any]:
    """
    Parses Magnet URI and extracts metadata.
    Example: magnet:?xt=urn:btih:XXXX&dn=Ubuntu.iso&tr=http...
    """
    parsed = urlparse(uri)
    query_params = parse_qs(parsed.query)

    xt_list = query_params.get("xt", [])
    info_hash = ""
    for xt in xt_list:
        if "urn:btih:" in xt.lower():
            info_hash = xt.split("urn:btih:")[-1].strip()

    name = unquote(query_params.get("dn", ["Unknown Torrent"])[0])
    trackers = [unquote(tr) for tr in query_params.get("tr", [])]
    exact_length = query_params.get("xl", [0])[0]
    try:
        total_bytes = int(exact_length)
    except Exception:
        total_bytes = 0

    return {
        "is_magnet": True,
        "info_hash": info_hash,
        "name": name,
        "trackers": trackers,
        "total_bytes": total_bytes
    }

def parse_torrent_file(file_path: str) -> Dict[str, Any]:
    """
    Parses a local .torrent file and extracts metadata and file list.
    """
    with open(file_path, "rb") as f:
        data = f.read()

    decoded = bdecode(data)
    info = decoded.get("info", {})

    raw_name = info.get("name", b"Unknown")
    name = raw_name.decode("utf-8", errors="replace") if isinstance(raw_name, bytes) else str(raw_name)

    files = []
    total_bytes = 0

    if "files" in info:
        # Multi-file torrent
        for f in info["files"]:
            length = f.get("length", 0)
            total_bytes += length
            raw_path_parts = f.get("path", [])
            path_parts = [p.decode("utf-8", errors="replace") if isinstance(p, bytes) else str(p) for p in raw_path_parts]
            files.append({
                "path": os.path.join(*path_parts),
                "length": length
            })
    elif "length" in info:
        # Single-file torrent
        length = info.get("length", 0)
        total_bytes = length
        files.append({
            "path": name,
            "length": length
        })

    piece_length = info.get("piece length", 0)

    # Announce list
    trackers = []
    if "announce" in decoded:
        raw_tr = decoded["announce"]
        trackers.append(raw_tr.decode("utf-8", errors="replace") if isinstance(raw_tr, bytes) else str(raw_tr))
    if "announce-list" in decoded:
        for tr_group in decoded["announce-list"]:
            for tr in tr_group:
                trackers.append(tr.decode("utf-8", errors="replace") if isinstance(tr, bytes) else str(tr))

    return {
        "is_magnet": False,
        "name": name,
        "total_bytes": total_bytes,
        "piece_length": piece_length,
        "files": files,
        "trackers": list(dict.fromkeys(trackers))
    }

def is_torrent_or_magnet(url: str) -> bool:
    if not url:
        return False
    u = url.strip().lower()
    return u.startswith("magnet:?") or u.endswith(".torrent")
