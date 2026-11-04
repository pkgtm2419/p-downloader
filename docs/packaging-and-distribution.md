# Packaging & Distribution Guide

This document describes how to compile, package, and release **P-Downloader** across supported platforms.

---

## 1. Distribution Artifacts Overview

| Target Artifact | Platform | Build Tool | Configuration |
| :--- | :--- | :--- | :--- |
| **`P-Downloader-Setup.exe`** | Windows x64 | Inno Setup 6 + PyInstaller | [`installer.iss`](file:///installer.iss) |
| **`P-Downloader-Portable.exe`** | Windows x64 | PyInstaller (Onefile) | [`P-Downloader-Portable.spec`](file:///P-Downloader-Portable.spec) |
| **`P-Downloader-Windows-x64-Portable.zip`** | Windows x64 | PyInstaller (Onedir) + ZIP | [`pdownloader.spec`](file:///pdownloader.spec) |
| **`P-Downloader-Linux-x64.tar.gz`** | Linux x64 | PyInstaller + tar | [`pdownloader.spec`](file:///pdownloader.spec) |
| **`pdownloader-browser-extension.zip`** | All Browsers | ZIP archiver | [`browser_extension/`](file:///browser_extension/) |

---

## 2. Automated Windows Build Pipeline

The easiest way to build the complete Windows release suite is via the bundled batch script:

```bat
build_installer.bat
```

### What `build_installer.bat` executes:
1. Validates the active Python virtual environment.
2. Invokes **PyInstaller** on `pdownloader.spec` to produce `dist\P-Downloader\`.
3. Invokes **PyInstaller** on `P-Downloader-Portable.spec` to produce `dist\P-Downloader-Portable.exe`.
4. Compiles the Inno Setup installer script via `ISCC.exe installer.iss` to produce `dist\P-Downloader-Setup.exe`.
5. Packages the standalone directory into `dist\P-Downloader-Windows-x64-Portable.zip`.
6. Compresses the browser extension into `dist\pdownloader-browser-extension.zip`.
7. Computes SHA256 hashes and writes `dist\SHA256SUMS.txt`.

---

## 3. Manual PyInstaller Compilation

### Building the Standalone Directory
```powershell
pyinstaller --clean pdownloader.spec
```
Outputs binaries and dependencies into `dist/P-Downloader/`.

### Building the Single-File Portable Executable
```powershell
pyinstaller --clean P-Downloader-Portable.spec
```
Outputs standalone single executable `dist/P-Downloader-Portable.exe`.

---

## 4. Building the Inno Setup Installer (`installer.iss`)

[Inno Setup 6](https://jrsoftware.org/isdl.php) creates the production Windows wizard installer:

```powershell
# Compile installer from command line (ensure ISCC.exe is in PATH)
ISCC.exe installer.iss
```

### Key Installer Capabilities configured in `installer.iss`:
- **Seamless Upgrade Detection**: Detects previous installations and preserves settings/download history.
- **Native Host Registry Keys**: Registers native messaging manifest entries for Chrome, Edge, Brave, and Firefox.
- **Start Menu & Desktop Shortcuts**: Configures high-DPI application icons and uninstaller entries.
- **Visual C++ Runtime Check**: Verifies required runtimes are present.

---

## 5. Linux Standalone Packaging

To build a portable Linux package on Ubuntu, Debian, or Fedora:

```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Compile via PyInstaller
pyinstaller --clean pdownloader.spec

# 3. Copy launcher scripts and desktop file
cp run_pdownloader.sh dist/P-Downloader/
cp pdownloader.desktop dist/P-Downloader/
chmod +x dist/P-Downloader/P-Downloader dist/P-Downloader/run_pdownloader.sh

# 4. Package tarball
tar -czvf dist/P-Downloader-Linux-x64.tar.gz -C dist/ P-Downloader/
```

---

## 6. Version Bumping (`scripts/bump_version.py`)

P-Downloader provides an automated version bumping utility to keep all configuration files synchronized:

```powershell
# Bump patch version (e.g., 1.0.6 -> 1.0.7)
python scripts/bump_version.py patch

# Bump minor version (e.g., 1.0.7 -> 1.1.0)
python scripts/bump_version.py minor

# Set explicit version
python scripts/bump_version.py 2.0.0
```

### Files updated automatically by `bump_version.py`:
- `pyproject.toml` (`version = "..."`)
- `installer.iss` (`#define MyAppVersion "..."`)
- `browser_extension/manifest.json` (`"version": "..."`)
- `browser_extension/manifest.firefox.json` (`"version": "..."`)
- `main.py` (`__version__ = "..."`)
- `core/__init__.py` (`__version__ = "..."`)

---

## 7. Generating Cryptographic Checksums

Before releasing binaries, generate verifiable SHA256 checksums:

```powershell
# Windows PowerShell
Get-FileHash -Algorithm SHA256 dist\P-Downloader* | ForEach-Object { "$($_.Hash)  $($_.Path | Split-Path -Leaf)" } | Out-File -Encoding utf8 dist\SHA256SUMS.txt

# Linux / macOS
cd dist && sha256sum P-Downloader* > SHA256SUMS.txt
```

