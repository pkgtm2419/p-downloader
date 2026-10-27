"""
Antivirus Post-Download Security Scanner for P-Downloader (IDM Feature).
Integrates with Microsoft Defender (MpCmdRun.exe) or custom AV engines
to scan downloaded files immediately upon completion before user execution.
"""
import os
import sys
import glob
import subprocess
from typing import Optional, Tuple

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

class AntivirusScanner:
    _cached_defender_path: Optional[str] = None

    @classmethod
    def get_defender_path(cls) -> Optional[str]:
        if cls._cached_defender_path and os.path.isfile(cls._cached_defender_path):
            return cls._cached_defender_path

        if sys.platform != "win32":
            return None

        # Check standard Windows Defender paths
        standard_path = r"C:\Program Files\Windows Defender\MpCmdRun.exe"
        if os.path.isfile(standard_path):
            cls._cached_defender_path = standard_path
            return standard_path

        # Check Platform-specific Windows Defender paths (Windows 10/11 updates)
        platform_pattern = r"C:\ProgramData\Microsoft\Windows Defender\Platform\*\MpCmdRun.exe"
        matches = glob.glob(platform_pattern)
        if matches:
            # Sort to pick highest version
            matches.sort(reverse=True)
            cls._cached_defender_path = matches[0]
            return matches[0]

        return None

    @classmethod
    def is_available(cls) -> bool:
        return cls.get_defender_path() is not None

    @classmethod
    def scan_file(cls, file_path: str, custom_av_path: str = "") -> Tuple[bool, str]:
        """
        Scans target file using Microsoft Defender or custom AV.
        Returns (is_clean: bool, message: str).
        """
        if not os.path.isfile(file_path):
            return False, f"File not found: {file_path}"

        av_bin = custom_av_path if (custom_av_path and os.path.isfile(custom_av_path)) else cls.get_defender_path()
        if not av_bin:
            return True, "No antivirus scanner detected (Skipped)"

        try:
            # Run MpCmdRun.exe: ScanType 3 = File/Directory scan
            cmd = [av_bin, "-Scan", "-ScanType", "3", "-File", file_path, "-DisableRemediation"]
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=CREATE_NO_WINDOW,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            stdout, stderr = proc.communicate(timeout=60)

            # Return code 0 = No threats detected
            # Return code 2 = Threat detected
            if proc.returncode == 0:
                return True, "File verified clean by Windows Defender."
            elif proc.returncode == 2:
                return False, "THREAT DETECTED: Windows Defender identified potential malware in this file."
            else:
                return True, f"Scan completed with code {proc.returncode}"

        except subprocess.TimeoutExpired:
            return True, "Scan timed out (File allowed)"
        except Exception as e:
            return True, f"Scan skipped due to error: {str(e)}"
