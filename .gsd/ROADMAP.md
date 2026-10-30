# ROADMAP.md — Security Hardening Roadmap

### Phase 1: Input Sanitization & Path Traversal Defense
- **Goal**: Protect filesystem boundaries against `Content-Disposition` path traversal and directory escape.
- **Tasks**:
  1. Add `sanitize_filename()` in `core/categories.py` and `core/segment.py`.
  2. Implement canonical path resolution check in `get_default_save_path()`.
  3. Add unit tests for path traversal attack strings (`../../`, absolute paths, Windows drive specifiers).
- **Status**: Ready

### Phase 2: IPC Hardening & Token Authentication
- **Goal**: Prevent local socket hijacking and unauthorized remote download triggering.
- **Tasks**:
  1. Implement secure random token generation and authentication in `core/ipc.py`.
  2. Update `browser_extension/pdownloader_native_host.py` to supply token.
  3. Require explicit user confirmation in `gui/main_window.py` for IPC downloads.
- **Status**: Ready

### Phase 3: Cryptographic Storage & Protocol Hardening
- **Goal**: Encrypt credentials at rest, restrict bencode recursion, and block SSRF.
- **Tasks**:
  1. Add DPAPI encryption / decryption in `core/credentials_manager.py`.
  2. Add `max_depth` recursion guard and byte limit in `core/torrent.py`.
  3. Add SSRF / private IP address filtering in `core/spider.py`.
  4. Fix argument list formatting in `gui/main_window.py`.
- **Status**: Ready

### Phase 4: Verification, Version Bump & CI Publication
- **Goal**: Verify all 31+ unit tests plus new security regression tests, bump version to v1.0.6, and verify GitHub Actions release.
- **Tasks**:
  1. Run complete unit test suite across all modules.
  2. Bump version to 1.0.6.
  3. Commit and tag release.
- **Status**: Ready
