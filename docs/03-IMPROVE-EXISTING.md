# 03: Improve What Already Exists

Format: **Evidence** (what I measured or reproduced; *(verify)* = suspected from reading) · **Change** · **Done when**. `B-xx` refers to the bug list in `PLAN-universal-video-downloader.md`.

Measured baseline (v1.0.7): `core/` ≈ 5,000 lines, `gui/` ≈ 5,700 lines · `main_window.py` 1,376 lines · 79 broad `except` blocks (about 59 followed by `pass`) · **0** modules import `logging`, 14 `print()` calls · 92 of 205 `core/` functions have return annotations · 165 hard-coded hex colours outside `styles.py` · 0 translatable strings · no DB schema version · 36 settings read by string key · tests: 137 Python (136 pass here) + 16 JS.

---

## Engine and downloads

### IM-01: HLS rewrite  *(P0 · L · WS A)*
**Evidence (reproduced):** (a) AES-128 playlist with `#EXT-X-MEDIA-SEQUENCE:100` decrypts with the wrong IV, padding is not stripped, output is garbage but status is `completed` (B1); (b) `pause()` makes `download_segment` return `None` and the caller unpacks it → task goes to `error`, staging deleted (B2). *Read:* no `EXT-X-MAP` (fMP4), no separate audio renditions, no byte-ranges, key fetched once from the last `EXT-X-KEY`, segments before the first key crash on `key_info.get`, always picks `variants[0]` (B5-B7); `HLSDownloadTask` gets no headers; `set_speed_limit` is a no-op (B8).
**Change:** `core/hls/` package per Phase 1 of the earlier plan: full media-playlist model; IV = explicit or 16-byte big-endian `media_sequence + index`; PKCS#7 unpadding; per-segment key rotation; clear→encrypted transitions; init segment first; audio group download + mux; user-chosen variant; cooperative pause (sentinel, never `None` unpacking); fail loudly on key/decrypt errors (never write raw bytes); refuse `SAMPLE-AES`/DRM with `DRM_PROTECTED`.
**Done when:** `tests/test_hls_correctness.py` (the two reproductions + audio group, fMP4, key rotation, clear-then-encrypted, byte-range) passes; kill -9 mid-download resumes to a byte-identical file; 50 consecutive pause/resume cycles succeed.

### IM-02: One task interface, correct resume  *(P0 · M · WS A)*
**Evidence:** `resume_download` rebuilds every task as a plain `DownloadTask` for the stored URL; after an app restart an HLS download becomes a download of the `.m3u8` text file (B8). Pause deletes HLS temp dir, so HLS can never resume.
**Change:** `Task` protocol and `kind` column (contracts §2, §6); `engine.create_download` takes a `Route` + `BrowserRequestContext`; `from_record` per kind; staging dirs live under a stable per-task folder, not `tempfile.mkdtemp`.
**Done when:** a restart test resumes one task of each kind from the DB.

### IM-03: Database migrations  *(P0 · S · WS A)*
**Evidence:** no `user_version` or migration code found in `core/db.py`/`core/transfer_store.py`. Any column change will break existing users' databases.
**Change:** contracts §6: numbered SQL migrations, backup before upgrade, refuse newer DBs, upgrade tests from fixture DBs of every released version (v1.0.0 … v1.0.7).
**Done when:** CI upgrades every fixture DB and the app starts with all tasks intact.

### IM-11: Accelerated yt-dlp  *(P1 · M · WS B)*
**Evidence (read):** `YouTubeDownloadTask` options carry no `concurrent_fragment_downloads`, `http_chunk_size`, `ratelimit`, `proxy`, `source_address`, `cookiefile` or `http_headers`; `player_client` is hard-coded `["ios","android","web"]` and will go stale (B12). The app's "full bandwidth" machinery (limiter, bonding, resource controller) does not apply to these downloads.
**Change (stage 1, quick):** pass configurable `concurrent_fragment_downloads` (default 8), `http_chunk_size` (~10 MiB; also defeats per-connection throttling on some hosts), `retries`/`fragment_retries`, `ratelimit` from the limiter, proxy/binding via NF-10/15, cookies/headers via NF-02, `extractor_args` from settings; remove the hard-coded client list or make it a setting with a sensible default.
**Change (stage 2, true speed):** use yt-dlp only to **resolve** direct URLs + headers + fragment lists, then feed them to the app's own range/HLS engine so resume, bonding and limiter apply uniformly; fall back to yt-dlp's downloader for formats that need it (signature-ciphered, SABR, complex fragmenting).
**Done when:** on the throttled-origin benchmark (IM-13), stage 1 is ≥ 3× the default yt-dlp run; stage 2 is within ~10% of the range engine.

### IM-13: HTTP stack, disk, and honest benchmarks  *(P1 · M · WS A)*
**Evidence:** the existing benchmark number (~80 MB/s) is loopback; the HLS path uses blocking `requests` with a thread per segment and a double copy at merge (`combined.ts` + copy).
**Change:** keep-alive/HTTP/2 pooling for many small segments (aiohttp is already a dependency); stream-concatenate or `ffmpeg -c copy` straight from the segment list; verify sparse preallocation and write coalescing on NTFS and ext4; per-origin connection caps and `Retry-After`; benchmark harness adds a **rate-limited origin**, a **per-connection-throttled origin**, a **latency-injected origin** and an HLS 1080p-like origin; commit results under `docs/benchmarks/` with the machine described. MDM's lab server with fault injection is a good model for how to make the numbers meaningful.
**Done when:** benchmark report committed; regression guard in CI fails on a > 15% drop on the synthetic origins.

### IM-25: Limiter, resource budget and binding for every task kind  *(P1 · M · WS A)*
**Evidence:** `HLSDownloadTask.set_speed_limit` is a no-op; yt-dlp tasks ignore the limiter; helper processes ignore adapter binding (B8, B12).
**Change:** every task kind implements `set_speed_limit`; the global limiter is a token bucket shared by all kinds (in-process) and via the relay for subprocesses (NF-15); the resource controller budgets total connections and RAM across kinds.
**Done when:** a test sets a 1 MB/s global limit with one task of each kind running and measures ≤ 1.1 MB/s aggregate.

### IM-14: Probe, naming, resume validation audit  *(P2 · M · WS A, verify first)*
**Audit list (each needs a test before any change):** `Content-Disposition` with `filename*=UTF-8''…` and RFC 5987/6266 edge cases; servers that mishandle `HEAD`; `Accept-Ranges: none` and servers returning `200` to a range request (must fall back to single stream, not corrupt); `ETag`/`Last-Modified` + `If-Range` validation on resume (file changed on server → restart cleanly); redirect chains and cross-origin credential stripping; compressed content (`Content-Encoding`) vs. byte ranges; > 4 GB files and 32-bit counters; very long and non-ASCII names; Windows reserved names.
**Done when:** each audit line has a fixture-server test; failures become `IM-14.x` fixes.

### IM-22: File-exists policy  *(P2 · S · WS A, verify first)*
MDM's changelog shows a bug class worth testing here: a download saved under a numbered name (`name (1).mp4`) must display and open **that** name. Test: collision policy (ask / rename / overwrite / resume), numbered-name display, "Open file/folder" targets, categories + move/rename after completion.

---

## Reliability and code quality

### IM-04: Logging  *(P0 · S · WS D)*
**Evidence:** no module imports `logging`; 14 `print()` calls; with 59-ish swallowed exceptions, failures are invisible to users and to you.
**Change:** `core/logging_setup.py`: rotating file handler (e.g., 5 × 2 MB) in the app data dir, per-task log lines (route decision, retries, errors), a **redaction filter** (URLs' query tokens, cookies, `Authorization`, vault values), log level in Settings, "Help → Open log folder" and "Export diagnostics". Replace `print`.
**Done when:** canary-secret test passes: secrets injected into URLs/headers never appear in any log file.

### IM-05: Error handling  *(P1 · M · WS D)*
**Evidence:** 79 broad excepts, ~59 followed by `pass`.
**Change:** contracts §8. Triage each: (1) narrow to a specific exception, (2) log with context, (3) convert to `AppError` so the UI can show an actionable message and retry policy can decide. Lint rule (ruff `BLE001`, `S110`) blocks new blind excepts; allow-list only with a comment.
**Done when:** count of `except Exception: pass` is 0; every user-visible failure has a code and text.

### IM-06: Types, lint, static analysis  *(P2 · M · WS D)*
**Evidence:** 92/205 `core/` defs annotated; ~300 flake8 warnings (97 unused imports).
**Change:** `ruff` (lint + format), `mypy` (or pyright) strict on `core/` first, `pip-audit`, pre-commit config, one mechanical formatting commit up front so later diffs stay readable.
**Done when:** CI blocks on ruff + mypy for `core/`; unannotated public functions = 0.

### IM-07: Split `main_window.py`  *(P1 · L · WS F)*
**Evidence:** 1,376 lines, the largest module; it creates tasks directly (`create_download` has 5 call sites in the GUI).
**Change:** model/view for the download list (`QAbstractTableModel` + proxy for filter/sort; delegates for progress bars), controllers that call `automation.ops` (contracts §10), menus/toolbar/tray/clipboard watcher in separate modules, no business logic in widgets. Use signals/queued connections for worker → UI updates (9 `threading.Thread` starts exist; audit each for UI-thread safety).
**Done when:** `main_window.py` < 400 lines; `pytest-qt` tests drive add/pause/resume/cancel through controllers; a 10,000-row list stays responsive.

### IM-08: Design tokens, no hard-coded colours  *(P1 · M · WS F)*
**Evidence:** 165 hex colours outside `styles.py`; single light stylesheet.
**Change:** palette dict → QSS generator; replace inline colours with token lookups (`tokens.success`, `tokens.danger`, …); lint test that greps for raw hex in `gui/` outside `styles.py`.
**Done when:** the lint test passes and NF-28 themes can be switched at runtime.

### IM-20: Typed settings registry  *(P2 · M · WS F)*
**Evidence:** 36 string keys, and the proxy fields are saved but never read: the UI and the code drifted apart unnoticed.
**Change:** contracts §7; UI generated from the registry; a test fails if any registered setting is never read in code or any `get_setting("…")` key is not registered.
**Done when:** that consistency test is green and settings export/import works.

### IM-21: Download list UX  *(P2 · M · WS F, verify gaps first)*
**Check and add if missing:** search/filter (status, category, site, text), multi-select operations including **Move/Rename for several downloads at once** (MDM shipped this late; a good sign users ask), sort persistence, column chooser/persistence, "Find in list", keyboard shortcuts (Del, Space, Ctrl+A, Enter), per-download log tab with route decision and retries, progress detail view showing per-connection shares, drag-and-drop of links/files, clipboard monitor controls (exists; test it).

---

## Security

### IM-09: SSRF hardening  *(P1 · S · WS D)*
**Evidence:** `is_safe_external_url` resolves with `gethostbyname` (IPv4 only), is check-then-use (rebinding window), and fails closed on DNS errors so its test fails offline (B13).
**Change:** `getaddrinfo` over A and AAAA; reject if **any** result is private/loopback/link-local/reserved/multicast/unspecified/IPv4-mapped-private; re-validate each redirect hop; pin the validated IP into the connection (NF-11); injectable resolver for hermetic tests; also validate URLs found *inside* manifests (key URIs, segment URIs) and extractor outputs.
**Done when:** tests cover `127.0.0.1`, `::1`, `169.254.169.254`, `0.0.0.0`, `::ffff:10.0.0.1`, decimal/octal/hex IP forms, redirect-to-private, DNS-rebinding fixture.

### IM-16: Security hardening round  *(P1 · M · WS D)*
Checklist: IPC token file permissions (`0600`/ACL) and rotation; native host validates `allowed_origins`, message size and schema v2, rejects unknown keys; manifest/playlist/archive limits (contracts §11); subprocess hygiene (no `shell=True`, timeouts, secrets not on argv); Windows DPAPI/Linux keyring for the vault; dependency upper bounds + `pip-audit` + Dependabot; SBOM per release; `SECURITY.md` with a reporting address; threat model doc (`docs/security-model.md` exists, update it with this list).

### IM-17: Test strategy  *(P1 · L · WS D)*
Layers: unit + `hypothesis` fuzz for playlist/manifest/bencode/header parsers; fixture-server component tests (`tests/support/`); `pytest-qt` offscreen GUI tests; `node --test` for extension logic; **Playwright E2E** loading the unpacked extension in Chromium and web-ext for Firefox against a local site that serves mp4/HLS/fMP4/DASH/blob with cookie+Referer checks; weekly **live-site job** (a handful of public, legally-safe test videos) that opens an issue on failure; benchmark guard (IM-13). Rule: every bug gets a failing test first. Add a coverage floor and report it, but treat bug-class tests as the real metric.

### IM-18: CI/CD fixes  *(P1 · S · WS D)*
Use `node --test tests/browser/*.test.mjs` (the directory form fails on Node 22 and only works because CI pins Node 20); hermetic SSRF test (IM-09); version-drift check across README, `pyproject.toml`, `core/__init__.py`, `installer.iss`, both manifests (README still says 1.0.6 while code says 1.0.7); matrix Windows + Ubuntu + macOS (allowed to fail until NF-32); build artifacts from tags; sign checksums (NF-31); cache pip/npm.

---

## Extension

### IM-10: MV3 service-worker persistence  *(P1 · S · WS C)*
**Evidence (read):** `requestContext`, HLS-seen and YouTube maps live in worker memory; Chrome suspends idle workers (~30 s), so a later click sends no cookie/Referer context; `discoverHls` fetches with `credentials: 'omit'` so cookie-protected manifests are never found (B11).
**Change:** keep per-tab media and request context in `chrome.storage.session` (bounded, cleared on tab close/navigation); rebuild listeners at top level each wake; `credentials:'include'` for manifest discovery, or ask the app to fetch; alarms only if truly needed.
**Done when:** an E2E test sleeps the worker (or emulates restart) between detection and click and the download still carries cookies.

### IM-15: Firefox parity  *(P1 · M · WS C)*
**Evidence (read):** the Firefox manifest (MV2) has **no `content_scripts`** (no in-page button, no link capture); `background.js` calls `importScripts`, which does not exist in a Firefox MV2 background page, and the manifest lists only `background.js`, so `parseHlsMaster` and `youtubeMedia` are undefined (errors swallowed); `api.action` is MV3-only; `strict_min_version 109` predates `storage.session` (B10).
**Change:** ship Firefox as **MV3** with event-page background scripts (verify the minimum version you need against current Mozilla docs), add `content_scripts`, list all helper scripts in `background.scripts`, feature-detect `api.action || api.browserAction`, raise `strict_min_version` to what `storage.session` needs; Firefox container (cookie store) support.
**Done when:** the Playwright/web-ext E2E suite passes on Firefox; AMO validation (`web-ext lint`) is clean.

### IM-12: CLI forwarding  *(P2 · S · WS G)*
**Evidence (read):** `--url` forwarded to a running instance drops `--output` and `--connections` (B14).
**Change:** subsumed by NF-21: forward the full option set as one validated message; regression test.

---

## Documentation and process

### IM-19: Consolidate docs  *(P2 · S · WS E)*
**Evidence:** `UPGRADE_PLAN.md`, a 78 KB dated plan, and `.gsd/*` describe overlapping, mostly finished work; README says v1.0.6 in places.
**Change:** move old plans to `docs/archive/`; this folder becomes `docs/roadmap/`; add ADRs (`docs/adr/0001-router.md`, …) for decisions in the contracts; README gets a truthful "what works / what doesn't / tested sites / DRM and ToS notes" table; keep CHANGELOG with an `[Unreleased]` section that release notes are generated from (MDM's workflow is a good model); `CONTRIBUTING.md` with the agent workflow in `04-AGENT-PLAYBOOK.md`.
