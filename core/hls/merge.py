"""
HLS Stream Segment Merger and Muxer (IM-01).
Handles MPEG-TS concatenation, fMP4 init segment stitching, and FFmpeg audio/video muxing.
"""
import os
import shutil
from typing import List, Optional

from core.muxer import FFmpegMuxer
from core.errors import AppError, ErrorCode


def merge_segments(
    segment_files: List[str],
    output_path: str,
    init_map_path: Optional[str] = None,
    is_fmp4: bool = False
) -> str:
    """
    Concatenates downloaded segments into final playable media file.
    For fMP4 CMAF streams, places the initialization map (ftyp/moov) at the head.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    temp_merged = output_path + ".temp_merged"

    try:
        with open(temp_merged, "wb") as outfile:
            # 1. If fMP4, write init map first
            if init_map_path and os.path.isfile(init_map_path):
                with open(init_map_path, "rb") as init_f:
                    shutil.copyfileobj(init_f, outfile, 64 * 1024)

            # 2. Append all segment chunks
            for seg in segment_files:
                if seg and os.path.isfile(seg):
                    with open(seg, "rb") as infile:
                        shutil.copyfileobj(infile, outfile, 64 * 1024)

        # 3. If target is .mp4, remux for maximum compatibility
        if output_path.lower().endswith(".mp4") and FFmpegMuxer.is_available():
            ok, msg = FFmpegMuxer.remux_to_mp4(temp_merged, output_path)
            if not ok:
                shutil.move(temp_merged, output_path)
            else:
                try:
                    os.remove(temp_merged)
                except Exception:
                    pass
        else:
            shutil.move(temp_merged, output_path)

        return output_path
    finally:
        if os.path.exists(temp_merged):
            try:
                os.remove(temp_merged)
            except Exception:
                pass


def mux_audio_video(video_path: str, audio_path: str, output_path: str) -> bool:
    """
    Muxes separate video and audio streams together using FFmpeg with stream copy (-c copy).
    """
    if not FFmpegMuxer.is_available():
        raise AppError(ErrorCode.MUX_FAILED, "FFmpeg is required to mux separate HLS audio and video tracks.")

    ok, msg = FFmpegMuxer.mux_streams(video_path, audio_path, output_path)
    if not ok:
        raise AppError(ErrorCode.MUX_FAILED, f"Failed to mux audio and video tracks: {msg}")
    return True
