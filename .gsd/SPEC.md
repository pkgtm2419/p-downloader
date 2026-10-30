# SPEC.md — P-Downloader Security Hardening & Penetration Defense

Status: FINALIZED
Version: 1.0.6
Target: P-Downloader v1.0.6 Ultra Security Hardening

## 1. Vision & Objectives
Harden P-Downloader against client-side and remote penetration attacks identified in the application security assessment:
1. Prevent Path Traversal and Arbitrary File Overwrites in HTTP Content-Disposition headers and destination resolution.
2. Secure the Local IPC TCP server against unauthorized localhost exploitation via cryptographic authentication token gating and user confirmation.
3. Encrypt Site Credentials and API Bearer tokens at rest using platform-native cryptography (DPAPI on Windows, encrypted vault fallback).
4. Guard Bencode parsing against stack recursion denial-of-service and memory exhaustion.
5. Filter SSRF / internal loopback and RFC1918 addresses in WebSpider and URL probe requests.
6. Eliminate process argument injection and format string risks in desktop shell executions.
7. Maintain 100% test pass rate across Windows and Linux, bump version to v1.0.6, and verify via CI.

## 2. Requirements & Must-Haves
- [x] **REQ-SEC-01**: Sanitize all `Content-Disposition` filenames with `sanitize_filename` enforcing strict basename extraction, character whitelisting, and directory containment.
- [x] **REQ-SEC-02**: Implement secret token authentication for `core/ipc.py` stored in user-isolated `~/.pdownloader/.ipc_token` (`0600` permissions) and disallow unprompted silent auto-downloading from untrusted IPC calls.
- [x] **REQ-SEC-03**: Secure `core/credentials_manager.py` with DPAPI encryption (`CryptProtectData` / `CryptUnprotectData` on Windows) and Base64-encrypted secret keying on POSIX so plaintext passwords never land in SQLite.
- [x] **REQ-SEC-04**: Implement `max_depth` (depth limit 32) and maximum byte string length limits in `core/torrent.py` `bdecode`.
- [x] **REQ-SEC-05**: Implement RFC1918 and loopback IP blocking in `core/spider.py` (`is_safe_external_url`) to prevent SSRF and internal port scanning.
- [x] **REQ-SEC-06**: Clean process command execution in `gui/main_window.py` to use discrete argument lists for `explorer.exe`.
- [x] **REQ-SEC-07**: Update and add unit tests covering each security fix.
- [x] **REQ-SEC-08**: Version bump to v1.0.6 and full test suite verification.
