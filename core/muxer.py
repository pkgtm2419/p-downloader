"""
Audio/Video Stream Muxer using FFmpeg.
Combines separated video and audio tracks (e.g., DASH 1080p/4K streams or HLS tracks)
into standard playable containers (.mp4, .mkv) without quality loss (stream copy).
"""
import os
import sys
import shutil
import subprocess
import re
from typing import Optional, Tuple, Callable

# Windows flag to prevent flashing command prompt windows
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

class FFmpegMuxer:
    """
    Manages detection and execution of FFmpeg for audio/video stream muxing.
    """
    _cached_path: Optional[str] = None

    @classmethod
    def get_ffmpeg_path(cls) -> Optional[str]:
        """
        Locates the ffmpeg executable across system PATH and local project directories.
        """
        if cls._cached_path and os.path.isfile(cls._cached_path):
            return cls._cached_path

        # 1. Check system PATH
        which_path = shutil.which("ffmpeg")
        if which_path:
            cls._cached_path = which_path
            return which_path

        # 2. Check local application folders (tools, bin, vendor)
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        candidate_rel_paths = [
            os.path.join(base_dir, "tools", "ffmpeg.exe"),
            os.path.join(base_dir, "bin", "ffmpeg.exe"),
            os.path.join(base_dir, "vendor", "ffmpeg.exe"),
            os.path.join(base_dir, "ffmpeg.exe"),
            # Common Windows locations
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        ]

        for cand in candidate_rel_paths:
            if os.path.isfile(cand):
                cls._cached_path = cand
                return cand

        return None

    @classmethod
    def is_available(cls) -> bool:
        """Returns True if FFmpeg is installed and accessible."""
        return cls.get_ffmpeg_path() is not None

    @classmethod
    def mux_audio_video(
        cls,
        video_path: str,
        audio_path: str,
        output_path: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Tuple[bool, str]:
        """
        Muxes a separate video track and audio track into output_path using stream copy.
        Returns (success: bool, message: str).
        """
        ffmpeg_bin = cls.get_ffmpeg_path()
        if not ffmpeg_bin:
            return False, "FFmpeg executable not found. Please install FFmpeg or place ffmpeg.exe in the tools/ folder."

        if not os.path.isfile(video_path):
            return False, f"Video source file not found: {video_path}"
        if not os.path.isfile(audio_path):
            return False, f"Audio source file not found: {audio_path}"

        # Ensure destination directory exists
        out_dir = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(out_dir, exist_ok=True)

        cmd = [
            ffmpeg_bin,
            "-y",                     # Overwrite output
            "-i", video_path,         # Video input
            "-i", audio_path,         # Audio input
            "-c:v", "copy",           # Direct stream copy for video
            "-c:a", "aac",            # Copy or convert audio to aac if needed
            "-movflags", "+faststart",# Optimize MP4 for web streaming
            output_path
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                **({"creationflags": 0x08000000} if sys.platform == "win32" else {}),
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            stdout, stderr = process.communicate()
            if process.returncode == 0 and os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
                if progress_callback:
                    progress_callback(100.0)
                return True, "Muxing completed successfully."
            else:
                error_snippet = stderr[-400:] if stderr else "Unknown FFmpeg error"
                return False, f"FFmpeg failed with code {process.returncode}: {error_snippet}"

        except Exception as e:
            return False, f"Exception while running FFmpeg: {str(e)}"

    @classmethod
    def remux_to_mp4(
        cls,
        input_path: str,
        output_path: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Tuple[bool, str]:
        """
        Remuxes an existing media container (such as .ts, .mkv, .webm) into .mp4
        without re-encoding video/audio streams.
        """
        ffmpeg_bin = cls.get_ffmpeg_path()
        if not ffmpeg_bin:
            return False, "FFmpeg executable not found."

        if not os.path.isfile(input_path):
            return False, f"Input file not found: {input_path}"

        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", input_path,
            "-c", "copy",
            "-movflags", "+faststart",
            output_path
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                **({"creationflags": 0x08000000} if sys.platform == "win32" else {}),
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            stdout, stderr = process.communicate()
            if process.returncode == 0 and os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
                if progress_callback:
                    progress_callback(100.0)
                return True, "Remuxing completed."
            return False, f"Remux failed: {stderr[-300:] if stderr else ''}"
        except Exception as e:
            return False, f"Exception while running FFmpeg: {str(e)}"
