"""
HLS (HTTP Live Streaming) Playlist Parser (IM-01).
Parses master and media playlists, stream variants, audio groups (#EXT-X-MEDIA),
fMP4 initialization maps (#EXT-X-MAP), per-segment key rotation (#EXT-X-KEY),
discontinuities, byte-ranges, and live vs VoD indicators per RFC 8216.
"""
import re
from urllib.parse import urljoin
from typing import List, Dict, Any, Optional


class MasterPlaylist(list):
    """List of stream variants with attached audio_groups and subtitles."""
    def __init__(self, variants: List[Dict[str, Any]], audio_groups: Dict[str, Any] = None, subtitles: List[Dict[str, Any]] = None):
        super().__init__(variants)
        self.variants = variants
        self.audio_groups = audio_groups or {}
        self.subtitles = subtitles or []

    def get(self, key: str, default: Any = None) -> Any:
        if key == "variants":
            return self.variants
        elif key == "audio_groups":
            return self.audio_groups
        elif key == "subtitles":
            return self.subtitles
        return default


class HLSParser:
    @staticmethod
    def is_master_playlist(content: str) -> bool:
        return "#EXT-X-STREAM-INF" in content or "#EXT-X-MEDIA:TYPE=" in content

    @staticmethod
    def parse_master_playlist(content: str, base_url: str) -> MasterPlaylist:
        """
        Parses master playlist into video variants and separate audio/subtitle renditions.
        Returns MasterPlaylist (list of variants with .audio_groups and .subtitles).
        """
        variants = []
        audio_groups: Dict[str, List[Dict[str, Any]]] = {}
        subtitles: List[Dict[str, Any]] = []

        lines = [line.strip() for line in content.splitlines() if line.strip()]

        for i, line in enumerate(lines):
            # Parse separate audio groups: #EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="English",DEFAULT=YES,URI="audio.m3u8"
            if line.startswith("#EXT-X-MEDIA:"):
                type_match = re.search(r'TYPE=([A-Z]+)', line)
                media_type = type_match.group(1) if type_match else ""

                group_match = re.search(r'GROUP-ID="([^"]+)"', line)
                name_match = re.search(r'NAME="([^"]+)"', line)
                uri_match = re.search(r'URI="([^"]+)"', line)
                default_match = re.search(r'DEFAULT=(YES|NO)', line)

                group_id = group_match.group(1) if group_match else "default"
                name = name_match.group(1) if name_match else "Audio"
                uri = urljoin(base_url, uri_match.group(1)) if uri_match else None
                is_default = (default_match.group(1) == "YES") if default_match else False

                if media_type == "AUDIO" and uri:
                    if group_id not in audio_groups:
                        audio_groups[group_id] = []
                    audio_groups[group_id].append({
                        "group_id": group_id,
                        "name": name,
                        "url": uri,
                        "is_default": is_default
                    })
                elif media_type == "SUBTITLES" and uri:
                    subtitles.append({
                        "name": name,
                        "url": uri
                    })

            # Parse video stream variants
            elif line.startswith("#EXT-X-STREAM-INF:"):
                info = line[len("#EXT-X-STREAM-INF:"):]
                bandwidth = 0
                resolution = "Unknown"
                codecs = ""
                audio_group_id = None

                bw_match = re.search(r'BANDWIDTH=(\d+)', info)
                if bw_match:
                    bandwidth = int(bw_match.group(1))

                res_match = re.search(r'RESOLUTION=(\d+x\d+)', info)
                if res_match:
                    resolution = res_match.group(1)

                codec_match = re.search(r'CODECS="([^"]+)"', info)
                if codec_match:
                    codecs = codec_match.group(1)

                audio_match = re.search(r'AUDIO="([^"]+)"', info)
                if audio_match:
                    audio_group_id = audio_match.group(1)

                # Next line is the URL
                if i + 1 < len(lines) and not lines[i + 1].startswith("#"):
                    stream_url = urljoin(base_url, lines[i + 1])
                    variants.append({
                        "resolution": resolution,
                        "bandwidth": bandwidth,
                        "codecs": codecs,
                        "audio_group_id": audio_group_id,
                        "url": stream_url
                    })

        # Sort variants by bandwidth descending
        variants.sort(key=lambda x: x["bandwidth"], reverse=True)
        return MasterPlaylist(variants, audio_groups, subtitles)

    @staticmethod
    def parse_media_playlist(content: str, base_url: str) -> Dict[str, Any]:
        """
        Parses media playlist segments, duration, sequence, init map (fMP4),
        per-segment key rotation, byte-ranges, and live status.
        """
        segments = []
        current_key_info = None
        init_map_url = None
        init_map_byterange = None
        total_duration = 0.0
        target_duration = 6.0
        media_sequence = 0
        is_live = True

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        current_duration = 0.0
        current_byterange = None

        for line in lines:
            if line.startswith("#EXT-X-TARGETDURATION:"):
                try:
                    target_duration = float(line.split(":")[1].strip())
                except Exception:
                    target_duration = 6.0

            elif line.startswith("#EXT-X-MEDIA-SEQUENCE:"):
                try:
                    media_sequence = int(line.split(":")[1].strip())
                except Exception:
                    media_sequence = 0

            elif line.startswith("#EXT-X-ENDLIST"):
                is_live = False

            # fMP4 CMAF init segment: #EXT-X-MAP:URI="init.mp4",BYTERANGE="123@0"
            elif line.startswith("#EXT-X-MAP:"):
                uri_match = re.search(r'URI="([^"]+)"', line)
                if uri_match:
                    init_map_url = urljoin(base_url, uri_match.group(1))
                br_match = re.search(r'BYTERANGE="([^"]+)"', line)
                if br_match:
                    init_map_byterange = br_match.group(1)

            # Per-segment key rotation: #EXT-X-KEY:METHOD=AES-128,URI="...",IV=0x...
            elif line.startswith("#EXT-X-KEY:"):
                method_match = re.search(r'METHOD=([^,\s]+)', line)
                uri_match = re.search(r'URI="([^"]+)"', line)
                iv_match = re.search(r'IV=([^,\s]+)', line)

                method = method_match.group(1) if method_match else "NONE"
                key_url = urljoin(base_url, uri_match.group(1)) if uri_match else ""
                iv_val = iv_match.group(1) if iv_match else None

                current_key_info = {
                    "method": method,
                    "url": key_url,
                    "iv": iv_val
                }

            elif line.startswith("#EXT-X-BYTERANGE:"):
                current_byterange = line[len("#EXT-X-BYTERANGE:"):].strip()

            elif line.startswith("#EXTINF:"):
                dur_match = re.search(r'#EXTINF:([\d.]+)', line)
                if dur_match:
                    current_duration = float(dur_match.group(1))

            elif not line.startswith("#"):
                seg_url = urljoin(base_url, line)
                seq_num = media_sequence + len(segments)
                segments.append({
                    "url": seg_url,
                    "duration": current_duration,
                    "key_info": current_key_info,
                    "sequence_number": seq_num,
                    "byterange": current_byterange
                })
                total_duration += current_duration
                current_duration = 0.0
                current_byterange = None

        return {
            "segments": segments,
            "total_duration": total_duration,
            "target_duration": target_duration,
            "segment_count": len(segments),
            "media_sequence": media_sequence,
            "init_map_url": init_map_url,
            "init_map_byterange": init_map_byterange,
            "is_live": is_live,
            "key_info": current_key_info
        }
