"""
Backward-compatibility adapter for core.hls (IM-01).
All core HLS logic is modularized in core/hls/ (parser, keys, fetch, merge, task).
"""
from core.hls import (
    HLSParser,
    HLSKeyManager,
    HLSDownloader,
    HLSDownloadTask,
    merge_segments,
    mux_audio_video
)

__all__ = [
    "HLSParser",
    "HLSKeyManager",
    "HLSDownloader",
    "HLSDownloadTask",
    "merge_segments",
    "mux_audio_video"
]
