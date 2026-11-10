# P-Downloader: Plan to Fix and Complete the "Download Any Video, Any Site, Full Speed" Goal

> Repo: `github.com/pkgtm2419/p-downloader` (v1.0.7, Python 3.10+ / PyQt6 desktop app + MV3/MV2 browser extension + native-messaging host)
> Goal: download video from **any website**, captured by a **proper browser extension**, at **full bandwidth**.
> This plan is written to be executed by an AI coding agent (or several in parallel). Section 7 splits it into workstreams.

---

## 0. How this analysis was done (and its limits)

- Cloned the repo and read `core/`, `gui/`, `main.py`, and all of `browser_extension/`, plus the existing docs (`README.md`, `UPGRADE_PLAN.md`, `.gsd/*`).
- Ran the test suite headless: **136 passed, 1 failed** (`tests/test_security.py::test_spider_ssrf_filtering`). Extension tests: **16/16 pass** when run as `node --test tests/browser/*.test.mjs`.
- **Reproduced two HLS bugs** against a local test server (section 2, B1 and B2).
- Everything marked **[read]** below comes from reading the code and was not executed. Treat those as "very likely", and let the first task of each phase be a failing test that proves it.
- Not verified: the GUI on a real desktop, Windows-specific code (DPAPI, installer, network adapters), real-world sites, and real browsers. The sandbox had no general internet, so no live site was tested.

**Overall picture:** the repo is much further along than a typical early project. It has a segmented range engine, SQLite journaling, adaptive concurrency, network bonding, a transactional extension handoff protocol, and a good test suite. The `.gsd/STATE.md` says all 15 planned tasks are done. The gaps are not in the "classic file download" path. They are in the **video path**, which is the thing you actually want: most "any website" video is not a plain file URL.

---

## 1. Findings summary (ranked)

| # | Severity | Area | Finding | Evidence |
|---|---|---|---|---|
| B1 | **Critical** | HLS | AES-128 streams whose playlist does not start at sequence 0 decrypt with the **wrong IV** and PKCS#7 padding is **never stripped**. Output is garbage but status is `completed`. | **Reproduced.** Output differed from plaintext; 24,672 bytes written vs 24,576 expected. |
| B2 | **Critical** | HLS | **Pause crashes the task.** `download_segment` returns `None` when paused, then `idx, path = future.result()` raises. Task goes to `error`, temp dir is deleted, so HLS can never resume. | **Reproduced:** `cannot unpack non-iterable NoneType object`. |
| B3 | **Critical** | Universal sites | **yt-dlp is only used for YouTube.** Pasting a Vimeo / X / Instagram / Facebook / Reddit / news-site *page* URL falls to the plain HTTP probe and downloads the HTML page as `download.bin`. yt-dlp supports well over a thousand sites; the app uses it for one. | **[read]** `core/engine.py`, `core/segment.py::probe_url`, `gui/add_dialog.py` all gate on `is_youtube_url`. |
| B4 | **Critical** | Auth / cookies | Browser cookies, Referer and User-Agent captured by the extension are used for the **probe only**. The real `DownloadTask`, `HLSDownloadTask` and yt-dlp task never receive them (`create_download` has no headers parameter). Any login-gated or referer-checked video returns 403. | **[read]** `gui/add_dialog.py:284` is the only consumer; `core/engine.py::create_download` has no `headers`; `HLSDownloadTask` builds `HLSDownloader(url, save_path, max_workers)` with no headers. |
| B5 | High | HLS | Separate audio renditions (`#EXT-X-MEDIA:TYPE=AUDIO`) are ignored, so many streams come out **silent**. The extension parses them and sends `audioUrl`, but **no Python code reads `audioUrl` or `outputFormat`**. | **[read]** grep of `core/ gui/ main.py` finds neither. |
| B6 | High | HLS | fMP4/CMAF streams (`#EXT-X-MAP` init segment, `.m4s`) are not supported; segments are saved as `.ts` and concatenated without the init segment. Byte-range segments and per-segment key rotation are also unhandled (only the last key seen is fetched and applied to all segments; segments before the first `#EXT-X-KEY` crash on `key_info.get`). | **[read]** `core/hls_downloader.py`. |
| B7 | High | HLS | Always picks the highest-bandwidth variant (`variants[0]`); the quality the user chose in the extension/dialog is ignored. | **[read]** |
| B8 | High | HLS | HLS bypasses the "v2" engine: no resume, no speed limit (`set_speed_limit` is a no-op), no shared resource budget, no network binding, no retry classification. After an app restart, `resume_download` rebuilds it as a plain `DownloadTask` for the `.m3u8` URL (downloads the playlist text as the file). | **[read]** `core/engine.py::resume_download`, `core/hls_downloader.py::HLSDownloadTask`. |
| B9 | High | Extension | **DASH (`.mpd`) is explicitly refused** (`throw new Error('DASH streams are unsupported.')`). MSE `blob:` videos are dropped because only `http(s)` URLs are accepted. These cover a large share of modern sites. | **[read]** `background.js`, `content.js`. |
| B10 | High | Firefox | The Firefox manifest (MV2) has **no `content_scripts`**, so no in-page download pill and no link capture. `background.js` uses `importScripts`, which does not exist in a Firefox MV2 background page, and the manifest lists only `background.js`, so `parseHlsMaster` and `youtubeMedia` are undefined and HLS discovery fails silently. `api.action.setBadgeText` is MV3-only (MV2 uses `browserAction`). `strict_min_version 109` predates `storage.session` (Firefox 115). | **[read]** `manifest.firefox.json`, `background.js`. |
| B11 | Medium | Extension | MV3 service worker state is in memory (`requestContext`, `hlsSeen`, YouTube maps). After ~30 s idle the worker is killed and the cookie/Referer context is lost, so a later click sends no credentials. `discoverHls` fetches the playlist with `credentials: 'omit'`, so cookie-protected manifests are never discovered. | **[read]** |
| B12 | Medium | Speed | yt-dlp downloads run with defaults: no `concurrent_fragment_downloads`, no `http_chunk_size`, no rate limit, no proxy/source-address, no cookies. YouTube/DASH downloads therefore do **not** use the app's "full bandwidth" machinery. `player_client` is hard-coded to `["ios","android","web"]`, which will rot. | **[read]** `core/youtube_downloader.py:412-428`. |
| B13 | Medium | Security | `is_safe_external_url` resolves DNS with `gethostbyname` (IPv4 only, no IPv6/AAAA check) and is check-then-use (DNS-rebinding window). The test fails offline because the function fails closed on DNS errors. | Test failure; **[read]** `core/spider.py`. |
| B14 | Low | CLI | `--url` forwarded to a running instance drops `--output` and `--connections`. | **[read]** `main.py`. |
| B15 | Low | Hygiene | README still says v1.0.6 in install/build sections (code is 1.0.7). ~300 flake8 warnings, 97 of them unused imports. CI runs `node --test tests/browser`, which fails on Node 22 (directory arg), only passes because CI pins Node 20. Three overlapping plan docs (`UPGRADE_PLAN.md`, the 78 KB dated plan, `.gsd/*`) describe work that is mostly done. | flake8 run; `node --test tests/browser` on v22 returns 1 failure. |

---

## 2. Reproductions (turn these into permanent regression tests first)

Both were confirmed with a throwaway local HTTP server. Recreate as `tests/test_hls_correctness.py`.

1. **B1:** serve an AES-128 playlist with `#EXT-X-MEDIA-SEQUENCE:100`, implicit IV, PKCS#7-padded segments. Expected: output equals the concatenated plaintext. Actual: mismatch, status `completed`.
2. **B2:** slow segments, call `pause()` mid-download. Expected: status `paused`, state kept, `resume()` finishes with a byte-identical file. Actual: status `error`.

Add siblings for B5/B6: master playlist with separate audio group; fMP4 with `#EXT-X-MAP`; key rotation mid-playlist; clear segments before the first key; byte-range segments.

---

## 3. Target architecture

One routing decision, made once, in one place:

```
URL (+ page URL + captured headers/cookies)
        │
        ▼
  core/router.py  ── classify ──►  DIRECT_FILE      → existing DownloadTask (range engine, bonding, limiter)
                                   HLS              → new HlsEngineTask (uses the v2 block engine)
                                   DASH             → ExtractorTask (yt-dlp) or DashTask
                                   PAGE (any site)  → ExtractorTask (yt-dlp, accelerated)
                                   TORRENT/MAGNET   → existing torrent path
```

Rules:
- **Classification is by evidence, not by hostname.** Order: `magnet:`/`.torrent` → HLS/DASH by URL or `Content-Type` → direct file by `Content-Type`/`Content-Disposition`/extension → otherwise try yt-dlp `extract_info(download=False)`; if it yields formats, it is a PAGE; if it fails, fall back to a direct download and tell the user why.
- **One header context object** (`BrowserRequestContext`, which already exists) travels with every task type and is origin-scoped (already implemented in `core/browser_context.py`; keep that protection).
- Every task type implements the same interface (`start/pause/resume/cancel/set_speed_limit/progress`) and registers with `ResourceController` and `SpeedLimiter`.

---

## 4. Phased plan

Each task lists files, work, and a testable acceptance criterion. Do the phases in order; tasks inside a phase can run in parallel (see section 7).

### Phase 0: Safety net (1 day)

- [ ] **0.1** Add `tests/test_hls_correctness.py` with the reproductions from section 2; confirm they fail on `master`.
- [ ] **0.2** Fix CI: use `node --test tests/browser/*.test.mjs`; add `pytest` as the runner (the suite already passes under it); make the SSRF test hermetic by injecting a resolver (see 5.1).
- [ ] **0.3** Reconcile docs: one authoritative `ROADMAP.md`; archive the three old plans under `docs/archive/`; fix README version strings; add a `scripts/bump_version.py` check to CI so README, `pyproject.toml`, `core/__init__.py`, `installer.iss` and both manifests cannot drift.
- [ ] **0.4** Remove unused imports and apply a formatter (ruff or black) in a single mechanical commit so later diffs stay readable.

**Done when:** CI green on Windows and Linux, new failing tests are committed (marked `xfail(strict=True)` until fixed).

### Phase 1: Make HLS correct (2-3 days) [B1, B2, B5, B6, B7, B8]

Rewrite `core/hls_downloader.py` as `core/hls/` (parser, key manager, segment fetcher, task).

- [ ] **1.1 Parser.** Full media-playlist model: `MEDIA-SEQUENCE`, `DISCONTINUITY`, `MAP` (init segment), `BYTERANGE`, `KEY` per segment (rotation, `IV` explicit or `sequence number` derived as 16-byte big-endian of `media_sequence + index`), `ENDLIST`/live detection, `EXT-X-MEDIA` audio/subtitle groups, `EXT-X-I-FRAME-STREAM-INF` ignored. Use a small, well-tested parser (consider the `m3u8` package vs. a hardened in-house parser; prefer in-house plus tests because input is untrusted).
- [ ] **1.2 Decryption.** AES-128-CBC with **PKCS#7 unpadding**; fail loudly (never write raw bytes) if the key fetch or decrypt fails; `SAMPLE-AES` and DRM (Widevine/PlayReady/FairPlay) are detected and reported as "protected, not supported", not silently corrupted.
- [ ] **1.3 Variant selection.** Honor the user's chosen variant (by bandwidth/resolution/URL); default to best. Surface variant list through the existing `gui/video_quality_dialog.py`.
- [ ] **1.4 Audio/video merge.** When a variant references an audio group, download both and mux with `core/muxer.py` (`-c copy`). Honor the extension's `audioUrl` and `outputFormat` (mp4/mp3); add the missing Python-side handling in `core/browser_handoff.py` and `main.py`.
- [ ] **1.5 fMP4.** Write the init segment first, then `.m4s` segments, to a temp `.mp4`; remux with ffmpeg only if needed.
- [ ] **1.6 Move onto the v2 engine.** Run segment fetches through the shared block queue / `ResourceController` / `SpeedLimiter` / `network_binder`, with per-segment retry via `retry_policy.py` and token-expiry handling via the existing refresh dialog (403/410 on a segment → ask the extension for a fresh playlist URL).
- [ ] **1.7 Durable resume.** Persist per-segment completion in `transfer_store` (segment files kept in a stable staging dir, not `tempfile.mkdtemp`). `resume_download` must rebuild the correct task type from the DB (add a `kind` column: `direct|hls|dash|extractor|torrent`; migrate old rows by sniffing the URL).
- [ ] **1.8 Pause/cancel semantics.** Cooperative: workers check a flag, finish or abandon the current segment, return a sentinel (never `None` unpacking). Pause keeps staging; cancel deletes it.
- [ ] **1.9 Live streams.** Poll the playlist, append new segments until `ENDLIST` or user stop. (Can ship after 1.1-1.8.)

**Done when:** all section 2 tests pass; a 2 GB-equivalent synthetic stream survives kill -9 mid-download and resumes to a byte-identical output; pause/resume works 50 times in a row in a stress test.

### Phase 2: Universal site support via an extractor layer (3-4 days) [B3, B12]

- [ ] **2.1 `core/router.py`** implementing the classification in section 3. Replace every `is_youtube_url` gate in `engine.py`, `segment.py`, `add_dialog.py`, `main_window.py` with the router. Keep YouTube-specific URL cleanup as a plugin of the extractor layer.
- [ ] **2.2 `core/extractor.py`** wrapping yt-dlp (`extract_info(download=False)`, format list, playlists, thumbnails, subtitles). Run in a worker thread with a timeout; never block the UI. Return the same `selectable_formats` shape the dialogs already consume.
- [ ] **2.3 Accelerated yt-dlp downloads.** Two options; implement A first, B as the stretch goal:
  - **A (fast to ship):** pass `concurrent_fragment_downloads` (user-configurable, default 8-16), `http_chunk_size` (about 10 MiB, which also defeats per-connection throttling on some hosts), `ratelimit` from `SpeedLimiter`, `proxy`/`source_address` from the network binder, `http_headers` and a cookie jar from the captured context, and `retries`/`fragment_retries`.
  - **B (true full bandwidth, IDM-like):** use yt-dlp only to **resolve** the direct media URLs and headers (`url`, `http_headers`, fragments), then feed those URLs into the app's own range/HLS engine so resume, bonding and the global limiter apply uniformly. Only fall back to yt-dlp's internal downloader for formats that need it (fragmented DASH, SABR, signature-ciphered URLs).
- [ ] **2.4 Configurable `extractor_args`** and a one-click **"Update extractors"** (`pip install -U yt-dlp` in a managed location, or bundle a yt-dlp binary updated by CI). Remove the hard-coded `player_client` list or make it a setting with a sane default. Sites change weekly, so this is the main maintenance cost of "any website."
- [ ] **2.5 DASH.** With yt-dlp present, DASH is handled by 2.3. Optionally add a small native `.mpd` parser (`SegmentTemplate`/`SegmentList`/`SegmentBase`) so the extension can pass `.mpd` URLs without yt-dlp.
- [ ] **2.6 Cookies for login-gated sites.** Accept a Netscape cookie file or the cookie header from the extension (see 3.2); also expose yt-dlp's `cookiesfrombrowser` as an opt-in setting. Store nothing in plaintext (reuse `credentials_manager`).
- [ ] **2.7 Clear failure messages.** Map extractor errors to actionable text: "DRM-protected", "login required", "geo-blocked", "site changed, update extractors", "no video found on this page."

**Done when:** a table of at least 15 representative sites (direct mp4, HLS, DASH, YouTube, Vimeo, X, Reddit, Instagram public post, a news site with embedded HLS, a site with `blob:` MSE playback, etc.) is recorded in `docs/site-matrix.md` with pass/fail and date; CI runs a **recorded-fixture** version (no live network) and a weekly **live** job that opens an issue when a site breaks.

### Phase 3: Extension that actually captures everything (3-4 days) [B4, B9, B10, B11]

- [ ] **3.1 Header/cookie propagation end to end.** Add `headers: dict` (or a `BrowserRequestContext`) to `DownloadEngine.create_download`, `HLSDownloadTask`, `YouTubeDownloadTask`/extractor task, and `DownloadTask`. Persist it **encrypted** with the task so resume works after restart (the DB must never hold plaintext cookies; reuse the DPAPI/vault code). Keep the existing cross-origin stripping.
- [ ] **3.2 Credential capture that survives worker sleep.** Move `requestContext` to `chrome.storage.session` (bounded size, per tab, cleared on tab close). Add `cookies` permission only if needed; prefer reading the real `Cookie` header from `onBeforeSendHeaders` for the exact media request. In `discoverHls`, fetch with `credentials: 'include'`, and fall back to asking the desktop app to fetch (so cookie-protected manifests are found).
- [ ] **3.3 Detect more media.** Add: DASH `.mpd` (stop throwing; pass to the router), `Content-Type: video/*|audio/*|application/x-mpegURL|application/dash+xml`, `<video>` with `blob:` source (report the **page URL** and let the extractor/sniffer resolve it), `<source>`, `<track>`, `og:video` meta, JSON-LD `VideoObject`, and `PerformanceObserver` resource timing for media requests the `webRequest` listener misses (service-worker-served media). Handle `iframe` players via `all_frames` (already set) and show the pill on the correct frame.
- [ ] **3.4 Pill/popup UX.** Per-site "ignore" list, quality picker that shows size and "video + audio / video only / audio only" (the data is already computed in `media-choices.js`), batch "download all detected", and an unobtrusive state when nothing is found ("play the video for a second").
- [ ] **3.5 Firefox parity.** Either (a) ship Firefox as **MV3** (Firefox supports MV3 with event-page background scripts and `content_scripts`; verify the minimum version you need against current docs) and drop MV2, or (b) fix MV2: add `content_scripts`, list `hls.js`, `youtube-media.js`, `media-choices.js` etc. in `background.scripts`, use `browserAction`, raise `strict_min_version` to 115. Prefer (a). Add a feature-detect shim (`api.action || api.browserAction`).
- [ ] **3.6 Real-browser E2E.** Playwright with `--load-extension` (Chromium) and web-ext (Firefox) against a local test site that serves mp4, HLS (clear and AES), fMP4 HLS and DASH, with cookie and Referer checks. Native host is stubbed with a local socket. This replaces most manual testing and proves B4/B10/B11 stay fixed.
- [ ] **3.7 Extension hardening review.** Keep `host_permissions` broad (needed), but verify: message validation on every `runtime.onMessage`, no sensitive data in logs, size caps (already present), CSP, and a documented privacy statement. Needed anyway for Chrome Web Store / AMO submission.
- [ ] **3.8 Distribution.** Publish to Chrome Web Store, Edge Add-ons and AMO so users do not need Developer Mode; keep the zip for sideloading. The native host installer already exists; add a "Test connection" button in the extension popup that reports exactly which part of the chain is broken (extension to host, host to app, app to engine).

**Done when:** the Playwright E2E suite passes in CI on Linux for Chromium and Firefox, and a manual smoke test on Windows 11 with Chrome, Edge and Firefox is checked in under `docs/manual-test-log.md`.

### Phase 4: "Full bandwidth" (2-3 days) [B12, plus tuning]

- [ ] **4.1 Benchmark first, tune second.** Extend `tests/benchmarks/benchmark_downloads.py` with: (1) HLS 1080p-like stream, (2) throttled-per-connection origin, (3) high-latency origin. Record `docs/benchmarks/` before/after. The existing 80 MB/s local result is a loopback number; add a rate-limited and a latency-injected origin so the numbers mean something.
- [ ] **4.2 HLS/DASH concurrency.** Segment-level parallelism through the AIMD controller (already exists for ranges); cap per-origin streams to avoid bans; honor `429/503 Retry-After`.
- [ ] **4.3 HTTP stack.** Prefer HTTP/2 or keep-alive pooling for many small segments (aiohttp is already a dependency; the HLS path currently uses blocking `requests` and one thread per segment). Reuse connections; avoid per-segment TLS handshakes.
- [ ] **4.4 Disk path.** Confirm sparse preallocation and write coalescing on Windows (NTFS) and Linux; make sure the merge step for HLS is a streamed concatenation or `ffmpeg -c copy` straight from the segment list (no double copy of multi-GB files, which the current `combined.ts` plus `shutil.copyfile` does).
- [ ] **4.5 Bandwidth policy UI.** "Use full bandwidth" vs. "leave N Mbps free"; per-site and per-queue limits; schedule-based limits (infrastructure exists in `scheduler_service.py` and `speed_limiter.py`).

**Done when:** benchmark report shows HLS and extractor downloads within ~10% of the range engine on the same link, and the report is committed.

### Phase 5: Security and robustness (1-2 days) [B13]

- [ ] **5.1 SSRF.** Resolve with `getaddrinfo` (A **and** AAAA), reject if **any** address is private/loopback/link-local/reserved/multicast, and **pin** the validated IP for the connection (custom `requests` adapter or aiohttp resolver) to remove the rebinding window; re-validate on every redirect hop. Accept an injectable resolver so the test is hermetic.
- [ ] **5.2 Untrusted-manifest limits.** Max playlist size, max segment count, max redirect depth, max total size; reject `file:`/`ftp:` URIs and `#EXT-X-KEY` URIs pointing at private networks.
- [ ] **5.3 Filename and path safety** for extractor-provided titles (already sanitized for HTTP; apply the same to yt-dlp `outtmpl`, including Windows reserved names and length limits).
- [ ] **5.4 Dependency policy.** Pin upper bounds, add `pip-audit` and Dependabot, sign release artifacts (the repo already publishes `SHA256SUMS.txt`).
- [ ] **5.5 Secret redaction regression test** for the new header plumbing (extend `tests/test_secret_redaction.py`).

### Phase 6: Packaging and release (1-2 days)

- [ ] **6.1** Bundle `ffmpeg` (via `imageio-ffmpeg`, already a dependency) and verify PyInstaller picks up yt-dlp's lazily imported extractors (`--collect-submodules yt_dlp`), a common cause of "works from source, breaks in the exe."
- [ ] **6.2** CI builds Windows installer + portable + Linux tarball from a tag, runs the E2E suite against the **built** artifact, and attaches checksums.
- [ ] **6.3** Auto-update check (GitHub Releases API) and the extractor-update button from 2.4.
- [ ] **6.4** macOS: either support it (build, notarize, native-messaging paths) or remove it from the README badges until it is real.
- [ ] **6.5** Update README/docs to match reality (tested sites matrix, DRM statement, browser support matrix, known limitations).

---

## 5. Explicit non-goals and honest limits

- **DRM** (Widevine, PlayReady, FairPlay: Netflix, Disney+, Prime, most paid services) cannot be downloaded by this design, and the app should say so clearly instead of producing a corrupt file. Do not add DRM circumvention.
- **"Any website" is a moving target.** Sites change their players constantly. The realistic promise is "works on every site yt-dlp supports, plus generic HLS/DASH/mp4 sniffing", kept alive by extractor updates (2.4) and a weekly live test (Phase 2 done-criteria).
- **Terms of service and copyright** differ by site and country. Add a short notice in the first-run dialog that the user is responsible for downloading only content they have the right to save.
- **YouTube SABR** streaming (already noted in `background.js` as unsupported) depends on yt-dlp keeping pace; do not hand-roll it.

---

## 6. Test strategy

| Layer | Tooling | What it proves |
|---|---|---|
| Unit | pytest, `hypothesis` for the playlist parser (fuzz untrusted input) | parser/crypto correctness, no crashes on malformed manifests |
| Component | local `http.server`/aiohttp fixtures in `tests/support/` (already exists) | HLS, fMP4, DASH, cookies, Referer, 403 refresh, 429 backoff, kill/resume |
| GUI | `pytest-qt` with `QT_QPA_PLATFORM=offscreen` (already used) | routing from dialog to task, quality dialog, resume after restart |
| Extension unit | `node --test` (already exists) | capture policy, handoff state machine |
| Extension E2E | Playwright (Chromium) + web-ext (Firefox) | sniffing, pill, header capture, native handoff against the fixture site |
| Live matrix | weekly GitHub Action, opens an issue on failure | real sites still work |
| Benchmarks | `tests/benchmarks/` | speed claims are measured, not asserted |

Regression rule: every bug in section 1 gets a test that fails before the fix.

---

## 7. Running this with plugins, MCP servers and sub-agents

Suggested parallel workstreams (each in its own git worktree/branch, merged after Phase 0 lands):

| Agent | Scope | Phases/Tasks |
|---|---|---|
| **A: HLS/engine** | `core/hls/`, `core/engine.py`, `transfer_store`, DB migration | Phase 1, 4.2-4.4 |
| **B: Extractor/router** | `core/router.py`, `core/extractor.py`, yt-dlp integration, GUI dialogs | Phase 2 |
| **C: Extension** | `browser_extension/`, native host, handoff, header plumbing (3.1 touches A and B: agree the `BrowserRequestContext` interface first) | Phase 3 |
| **D: QA/CI/security** | tests, CI, SSRF, fuzzing, benchmarks, E2E harness | Phase 0, 3.6, 4.1, Phase 5 |
| **E: Packaging/docs** | PyInstaller, installer, README/docs, store listings | Phase 6, 0.3 |

Interface contracts to freeze **before** parallel work starts (put them in `docs/contracts.md`):
1. `BrowserRequestContext` shape and how it is persisted encrypted.
2. The task interface (`start/pause/resume/cancel/set_speed_limit`, progress dict, `kind`).
3. The native-message schema, including `audioUrl`, `outputFormat`, `pageUrl`, `requestHeaders`, `mediaKind`.

Useful tooling:
- **GitHub MCP server**: create one issue per finding (B1-B15) with the evidence above, link PRs, and keep the checklist here in sync.
- **Playwright MCP / Playwright test runner**: drive real Chromium with the unpacked extension for 3.6 and for debugging site-specific capture.
- **Fetch / web search MCP**: look up current yt-dlp options, Chrome MV3 and Firefox MV3 behavior, and HLS RFC 8216 details instead of relying on memory.
- **Filesystem + shell**: ffmpeg/ffprobe to validate outputs (`ffprobe -v error -show_streams` must show both video and audio, correct duration).
- **Python libraries worth adding**: `hypothesis`, `pytest-qt`, `pytest-asyncio`, `pip-audit`, `ruff`; optionally `m3u8` (parser) and `pycryptodomex`/`cryptography` (already present) for AES.
- **Review agent**: after each phase, a separate agent reads the diff against section 1 and tries to break it (malformed manifests, huge playlists, redirect to `127.0.0.1`, cookie leakage across origins).

---

## 8. Definition of done (whole project)

1. All findings B1-B15 closed, each with a regression test.
2. `docs/site-matrix.md` shows the tested sites with dates; weekly live job is green or has an open issue.
3. Chrome, Edge and Firefox extensions pass the Playwright E2E suite; store listings submitted.
4. A cookie-protected, referer-checked HLS stream downloads correctly with audio, survives a hard kill, and resumes.
5. Benchmarks show HLS/extractor downloads at the same throughput class as the range engine on the same link.
6. Windows installer, portable exe and Linux tarball build from a tag in CI and pass a smoke test.
7. README and docs describe what actually works, including DRM and ToS limits.

---

## 9. Suggested order if time is short

1. Phase 0 (safety net)
2. B1 + B2 fixes (data corruption and crash; a few hours once tests exist)
3. 3.1 + 3.2 (cookies/headers reach the real download; this alone unblocks many sites)
4. 2.1-2.3A (route any page URL through yt-dlp with concurrent fragments)
5. 1.4-1.7 (audio, resume) then 3.3 and 3.5 (DASH/blob capture, Firefox)
6. Everything else
