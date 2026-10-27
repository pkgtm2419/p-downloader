#!/usr/bin/env python3
"""
Automated Version Management & Release Bumper for P-Downloader.

Usage:
    python scripts/bump_version.py patch       # 1.0.1 -> 1.0.2
    python scripts/bump_version.py minor       # 1.0.1 -> 1.1.0
    python scripts/bump_version.py major       # 1.0.1 -> 2.0.0
    python scripts/bump_version.py 1.2.0       # Explicit target version
    python scripts/bump_version.py --current   # Prints current version

Options:
    --commit    Automatically git commit changes
    --tag       Create annotated git tag v<version>
    --push      Push commit and tag to origin
"""
import sys
import re
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def get_current_version() -> str:
    init_path = ROOT / "core" / "__init__.py"
    content = init_path.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if not match:
        raise ValueError("Could not find __version__ in core/__init__.py")
    return match.group(1).strip()


def calculate_next_version(current: str, bump_type: str) -> str:
    parts = current.split(".")
    while len(parts) < 3:
        parts.append("0")

    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        raise ValueError(f"Current version '{current}' is not valid semver (X.Y.Z)")

    if bump_type == "patch":
        patch += 1
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif re.match(r"^\d+\.\d+(\.\d+)?", bump_type):
        return bump_type.lstrip("v")
    else:
        raise ValueError(f"Invalid bump type: '{bump_type}'. Choose patch, minor, major, or explicit X.Y.Z")

    return f"{major}.{minor}.{patch}"


def update_file(path: Path, pattern: str, replacement: str):
    if not path.exists():
        print(f"Skipping {path} (not found)")
        return
    content = path.read_text(encoding="utf-8")
    new_content, count = re.subn(pattern, replacement, content)
    if count > 0:
        path.write_text(new_content, encoding="utf-8")
        print(f"Updated {path.relative_to(ROOT)} ({count} replacements)")
    else:
        print(f"No changes in {path.relative_to(ROOT)}")


def bump_all_files(old_ver: str, new_ver: str):
    print(f"\n--- Bumping P-Downloader version: {old_ver} -> {new_ver} ---")

    # 1. core/__init__.py
    update_file(
        ROOT / "core" / "__init__.py",
        r'__version__\s*=\s*["\'][^"\']+["\']',
        f'__version__ = "{new_ver}"'
    )

    # 2. pyproject.toml
    update_file(
        ROOT / "pyproject.toml",
        r'version\s*=\s*["\'][^"\']+["\']',
        f'version = "{new_ver}"'
    )

    # 3. installer.iss
    update_file(
        ROOT / "installer.iss",
        r'#define\s+MyAppVersion\s+["\'][^"\']+["\']',
        f'#define MyAppVersion "{new_ver}"'
    )

    # 4. browser_extension/manifest.json
    update_file(
        ROOT / "browser_extension" / "manifest.json",
        r'"version":\s*["\'][^"\']+["\']',
        f'"version": "{new_ver}"'
    )

    # 5. README.md (update asset references)
    readme_path = ROOT / "README.md"
    if readme_path.exists():
        content = readme_path.read_text(encoding="utf-8")
        # Replace occurrences like v1.0.0 or 1.0.0 in download links and file names
        content = re.sub(
            r'P-Downloader-Setup-v[\d\.]+\.exe',
            f'P-Downloader-Setup-v{new_ver}.exe',
            content
        )
        content = re.sub(
            r'P-Downloader-v[\d\.]+-Portable\.exe',
            f'P-Downloader-v{new_ver}-Portable.exe',
            content
        )
        content = re.sub(
            r'P-Downloader-v[\d\.]+-Windows-x64-Portable\.zip',
            f'P-Downloader-v{new_ver}-Windows-x64-Portable.zip',
            content
        )
        content = re.sub(
            r'P-Downloader-v[\d\.]+-Linux-x64\.tar\.gz',
            f'P-Downloader-v{new_ver}-Linux-x64.tar.gz',
            content
        )
        content = re.sub(
            r'pdownloader-browser-extension-v[\d\.]+\.zip',
            f'pdownloader-browser-extension-v{new_ver}.zip',
            content
        )
        readme_path.write_text(content, encoding="utf-8")
        print(f"Updated {readme_path.relative_to(ROOT)} asset tables")


def main():
    parser = argparse.ArgumentParser(description="P-Downloader Version Bumper")
    parser.add_argument("bump", nargs="?", default="patch", help="patch | minor | major | explicit X.Y.Z")
    parser.add_argument("--current", action="store_true", help="Print current version and exit")
    parser.add_argument("--commit", action="store_true", help="git commit the updated files")
    parser.add_argument("--tag", action="store_true", help="git tag the new release")
    parser.add_argument("--push", action="store_true", help="git push master and tags to origin")

    args = parser.parse_args()

    curr_ver = get_current_version()
    if args.current:
        print(f"Current version: {curr_ver}")
        return

    new_ver = calculate_next_version(curr_ver, args.bump)
    bump_all_files(curr_ver, new_ver)

    if args.commit:
        print("\nCommitting changes...")
        subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-m", f"chore(release): bump version to {new_ver}"], cwd=ROOT, check=True)

    if args.tag:
        tag_name = f"v{new_ver}"
        print(f"\nCreating tag {tag_name}...")
        subprocess.run(["git", "tag", "-fa", tag_name, "-m", f"Release {tag_name}"], cwd=ROOT, check=True)

    if args.push:
        tag_name = f"v{new_ver}"
        print("\nPushing to origin...")
        subprocess.run(["git", "push", "origin", "master"], cwd=ROOT, check=True)
        if args.tag:
            subprocess.run(["git", "push", "origin", tag_name, "--force"], cwd=ROOT, check=True)

    print(f"\n✅ Successfully bumped version to {new_ver}!")
    print(f"   Release Tag: v{new_ver}")


if __name__ == "__main__":
    main()
