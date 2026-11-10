"""
Multi-Volume Archive Extraction Pipeline for P-Downloader.
Automatically unpacks .zip, .tar, .tar.gz, .tar.bz2, .tar.xz, .rar, and .7z archives,
including multi-part split volumes (.part01.rar, .7z.001) with path traversal defenses.
"""
import os
import re
import sys
import shutil
import zipfile
import tarfile
import subprocess
from typing import Optional, List, Tuple, Dict, Any

ARCHIVE_EXTENSIONS = {
    ".zip", ".tar", ".gz", ".tgz", ".bz2", ".tbz2", ".xz", ".txz",
    ".7z", ".rar"
}

SPLIT_VOLUME_PATTERNS = [
    re.compile(r"^(.*?)\.part0*1\.rar$", re.IGNORECASE),
    re.compile(r"^(.*?)\.part1\.rar$", re.IGNORECASE),
    re.compile(r"^(.*?)\.7z\.001$", re.IGNORECASE),
    re.compile(r"^(.*?)\.zip\.001$", re.IGNORECASE),
    re.compile(r"^(.*?)\.r00$", re.IGNORECASE),
]

PACKAGE_SPLIT_PATTERNS = [
    re.compile(r"^(.*?)\.part\d+\.rar$", re.IGNORECASE),
    re.compile(r"^(.*?)\.7z\.\d+$", re.IGNORECASE),
    re.compile(r"^(.*?)\.zip\.\d+$", re.IGNORECASE),
    re.compile(r"^(.*?)\.r\d+$", re.IGNORECASE),
]


def is_archive(filepath: str) -> bool:
    """Returns True if the file path represents a supported archive or first split volume."""
    if not filepath:
        return False
    lower = filepath.lower()
    for ext in ARCHIVE_EXTENSIONS:
        if lower.endswith(ext):
            return True
    for pat in SPLIT_VOLUME_PATTERNS:
        if pat.search(os.path.basename(filepath)):
            return True
    return False


def is_first_volume_or_single_archive(filepath: str) -> bool:
    """Returns True if the file is a standalone archive or the first volume of a split set."""
    if not is_archive(filepath):
        return False
    base = os.path.basename(filepath).lower()
    # If it's a split volume, must be part 1
    if ".part" in base and not re.search(r"\.part0*1\.rar$", base):
        return False
    if ".7z." in base and not base.endswith(".7z.001"):
        return False
    if ".zip." in base and not base.endswith(".zip.001"):
        return False
    return True


def get_7z_binary_path() -> Optional[str]:
    """Finds bundled or system-installed 7-Zip executable."""
    # 1. Bundled in resources
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    bundled_candidates = [
        os.path.join(base_dir, "resources", "bin", "7za.exe"),
        os.path.join(base_dir, "resources", "7za.exe"),
        os.path.join(base_dir, "resources", "bin", "7zz"),
        os.path.join(base_dir, "resources", "7zz")
    ]
    for b in bundled_candidates:
        if os.path.isfile(b) and os.access(b, os.X_OK if hasattr(os, "X_OK") else os.F_OK):
            return b

    # 2. System PATH
    for bin_name in ("7za", "7z", "7zz"):
        found = shutil.which(bin_name)
        if found:
            return found

    # 3. Standard Windows locations
    win_paths = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe"
    ]
    for wp in win_paths:
        if os.path.isfile(wp):
            return wp

    return None


def extract_archive(
    filepath: str,
    dest_dir: Optional[str] = None,
    password: Optional[str] = None
) -> Tuple[bool, str, List[str]]:
    """
    Safely unpacks an archive into dest_dir. Defends against directory traversal (Zip Slip).
    Returns (success: bool, message: str, extracted_files: List[str]).
    """
    if not os.path.isfile(filepath):
        return False, f"Archive file not found: {filepath}", []

    if not dest_dir:
        stem = os.path.splitext(os.path.basename(filepath))[0]
        for pat in SPLIT_VOLUME_PATTERNS:
            m = pat.search(os.path.basename(filepath))
            if m:
                stem = m.group(1)
                break
        dest_dir = os.path.join(os.path.dirname(os.path.abspath(filepath)), stem)

    os.makedirs(dest_dir, exist_ok=True)
    dest_dir_real = os.path.realpath(dest_dir)
    lower = filepath.lower()

    # 1. Standard ZIP files (pure Python)
    if lower.endswith(".zip") and not any(pat.search(os.path.basename(filepath)) for pat in SPLIT_VOLUME_PATTERNS):
        try:
            extracted = []
            with zipfile.ZipFile(filepath, "r") as zf:
                if password:
                    zf.setpassword(password.encode("utf-8"))
                for member in zf.namelist():
                    # Defend against Zip Slip
                    target = os.path.realpath(os.path.join(dest_dir_real, member))
                    if not target.startswith(dest_dir_real):
                        raise RuntimeError(f"Zip Slip path traversal attempt detected: {member}")
                    zf.extract(member, dest_dir_real)
                    extracted.append(target)
            return True, f"Successfully unpacked {len(extracted)} files.", extracted
        except Exception as e:
            return False, f"ZIP extraction error: {e}", []

    # 2. Standard TAR archives (pure Python)
    if any(lower.endswith(ext) for ext in (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
        try:
            extracted = []
            with tarfile.open(filepath, "r:*") as tf:
                # Path traversal check
                for member in tf.getmembers():
                    target = os.path.realpath(os.path.join(dest_dir_real, member.name))
                    if not target.startswith(dest_dir_real):
                        raise RuntimeError(f"Tar path traversal attempt detected: {member.name}")
                    extracted.append(target)
                if hasattr(tarfile, "data_filter"):
                    tf.extractall(dest_dir_real, filter="data")
                else:
                    tf.extractall(dest_dir_real)
            return True, f"Successfully unpacked {len(extracted)} files.", extracted
        except Exception as e:
            return False, f"TAR extraction error: {e}", []

    # 3. 7-Zip for RAR, 7z, and Split Volumes (.part01.rar, .7z.001)
    seven_z = get_7z_binary_path()
    if not seven_z:
        return False, "7-Zip binary (7za / 7z) not found. Please install 7-Zip to extract RAR/7z archives.", []

    cmd = [seven_z, "x", "-y", f"-o{dest_dir_real}"]
    if password:
        cmd.append(f"-p{password}")
    else:
        cmd.append("-p-")  # Do not prompt for password in terminal

    cmd.append(filepath)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode == 0:
            extracted = []
            for root, _, files in os.walk(dest_dir_real):
                for f in files:
                    extracted.append(os.path.join(root, f))
            return True, f"Successfully unpacked {len(extracted)} files with 7-Zip.", extracted
        return False, f"7-Zip error (code {proc.returncode}): {proc.stderr or proc.stdout}", []
    except Exception as e:
        return False, f"7-Zip execution error: {e}", []


def group_archive_volumes(filenames: List[str]) -> Dict[str, List[str]]:
    """
    Groups multi-volume filenames (e.g. movie.part1.rar, movie.part2.rar) under base package names.
    """
    packages: Dict[str, List[str]] = {}
    for fn in filenames:
        base = os.path.basename(fn)
        matched = False
        for pat in PACKAGE_SPLIT_PATTERNS:
            m = pat.search(base)
            if m:
                pkg_name = m.group(1)
                packages.setdefault(pkg_name, []).append(fn)
                matched = True
                break
        if not matched:
            packages.setdefault(os.path.splitext(base)[0], []).append(fn)

    # Sort volume sequences within each package
    for pkg in packages:
        packages[pkg].sort()

    return packages
