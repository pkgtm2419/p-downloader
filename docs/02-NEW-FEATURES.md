# 02: New Features (what is missing)

Each item: **Why** (evidence) · **Design** · **Steps** · **Done when**. "MDM" = Mister Download Manager, used as a behaviour reference only (GPL-3.0: no code copying). Contracts referenced (`BrowserRequestContext`, `Task`, router, schema v2) are in `01-ARCHITECTURE-AND-CONTRACTS.md`.

---

## A. Video from any website

### NF-01: Universal router, any page URL via yt-dlp  *(P0 · L · WS B)*
**Why:** only YouTube URLs reach yt-dlp today (`is_youtube_url` gates in `engine.py`, `segment.py`, `add_dialog.py`, `main_window.py`). Any other page URL downloads its HTML. MDM sends every page that is not a plain file to yt-dlp.
**Design:** implement `core/router.py` (table in contracts §4) and `core/tasks/extractor.py`. `extract_info(download=False)` runs in a worker with a timeout and returns the same `selectable_formats` shape the existing quality dialogs consume. Keep the YouTube-specific URL cleanup as a pre-step inside the extractor layer, not as a gate.
**Steps:**
1. Add the router with unit tests for each row of the decision table (fixtures, no network).
2. Replace every `is_youtube_url` gate with `router.classify`.
3. Generalize `youtube_dialog.py` → `video_dialog.py` (title, thumbnail, duration, format table, "audio only", subtitles).
4. After a probe says HTML, offer "Look for a video on this page?" instead of failing.
5. Map extractor errors to `AppError` codes (login, geo, DRM, outdated, no media).
**Done when:** a recorded-fixture suite covering ≥ 15 site shapes passes in CI; `docs/site-matrix.md` lists real sites tested with dates; pasting a non-YouTube video page downloads the video.

### NF-02: Request context reaches every task  *(P0 · M · WS C,A,B)*
**Why:** cookies/Referer/User-Agent captured by the extension are used for the probe only (`add_dialog.py` is the sole consumer); `create_download` has no headers parameter; `HLSDownloadTask` builds its downloader without headers. Login-gated or referer-checked media fails with 403. MDM forwards a full cookie jar (domain/path/flags), referrer and UA.
**Design:** contracts §3. Add `context` to `create_download(...)` and to all `Task.from_record`. Encrypted persistence so resume after restart keeps working.
**Steps:** (1) extension collects cookies (`cookies` permission) for the exact media URL's store (incognito/container aware); (2) schema v2 message; (3) `main.py`/`browser_handoff.py` parse and validate; (4) `net/session.py` applies origin-scoped cookies/headers; (5) yt-dlp gets a temp cookie file + `http_headers`; (6) one retry "as the app itself" when a browser UA is refused by a bot check (MDM does this; keep it opt-out); (7) redaction tests.
**Done when:** a local test server that requires a cookie and a Referer serves a direct file, an HLS stream and an extractor page; all three download; cookies never appear in logs or the DB in plaintext.

### NF-03: Extension stream sniffing v2  *(P0 · M · WS C)*
**Why:** DASH is refused in `background.js`; `blob:` (MSE) videos are dropped because only `http(s)` is accepted; manifests whose URL/type don't say so are missed. MDM reads response headers via `webRequest.onResponseStarted`, treats extension-less/untyped small text responses as "maybe a manifest" and reads them only on demand, and keeps a per-tab "Media on this page" list.
**Design:** classify each response (`hls`, `dash`, `file`, `maybe`); ignore tiny sounds (< ~ 20 KB) and segment types (`.ts`, `.m4s`, `.aac` fragments); store per-tab results in `chrome.storage.session` (survives worker sleep, see IM-10); for `blob:` videos send the **page URL** with `mediaKind:"blob"` and let the extractor/sniffer resolve it; for iframes, report the frame URL.
**Steps:** update `background.js`, `content.js`, `media-choices.js`; add popup tab "Media on this page" (type, size if known, quality, DRM badge, "Download" and "Copy URL"); add fixture-based `node --test` cases; add Playwright E2E (IM-17).
**Done when:** E2E site serves mp4, HLS (clear + AES), fMP4-HLS, DASH, and a `blob:` MSE player; each shows in the list and each downloads.

### NF-04: DRM detection and clear messaging  *(P1 · S · WS C,B)*
**Why:** encrypted-media streams cannot be saved; today they may end as a corrupt file marked completed. MDM flags protected media and never sends it.
**Design:** content script observes EME use (`navigator.requestMediaKeySystemAccess` hook, `<video>.mediaKeys`, `encrypted` events) and manifests with `EXT-X-KEY` methods other than `AES-128`/`NONE` or DASH `ContentProtection` (Widevine/PlayReady UUIDs); the HLS/extractor task also refuses `SAMPLE-AES` and DRM key URIs with `AppError(DRM_PROTECTED)`.
**Done when:** DRM fixtures show a "Protected video: it can't be saved" state in the pill/popup and produce no file; a regression test proves no DRM fixture ever reaches `completed`.

### NF-05: yt-dlp manager  *(P1 · M · WS B)*
**Why:** yt-dlp is a plain pip dependency with no updater; sites change weekly. MDM downloads a pinned release, verifies the signed checksum list and the binary, installs side-by-side, switches atomically, never downgrades, and keeps the previous version for rollback.
**Design:** `extractors/ytdlp_manager.py`; install under `~/.pdownloader/tools/yt-dlp/<version>/`; verify `SHA2-256SUMS` (+ signature where published) then the binary hash; status/update/rollback exposed via `automation.ops.tools_*`; run yt-dlp as a **subprocess** for isolation and crash-safety, or keep in-process behind a flag (document the trade-off: subprocess = safer, needs a binary per OS). GUI: Settings → Video → "Update extractors", version, channel (stable/nightly).
**Done when:** update works offline-safe (fails closed), rollback restores the previous version, and the manager refuses a tampered checksum (test).

### NF-06: Video options  *(P1 · M · WS B,F)*
**Why:** options exist for YouTube only; subtitle download not found in `core/`. MDM supports playlists, subtitles (embedded or beside), and sound-only.
**Design:** dialog fields: format/quality, container (mp4/mkv/webm), audio-only (mp3/m4a/opus), subtitles (languages, embed vs separate, auto-generated), chapters, thumbnail/metadata embed, playlist range, output template with safe-name preview. Missing subtitle languages must not fail the video (record a warning, like MDM's `sub_problems`).
**Done when:** each option has a fixture test; a playlist of N items creates N queued tasks with shared options.

### NF-34: Live stream recording  *(P2 · M · WS A)*
**Design:** HLS live: poll playlist at target-duration/2, append unseen segments by media-sequence, stop on `ENDLIST`/user stop/max duration; survive playlist gaps; optional "record from now".
**Done when:** a simulated live origin (sliding window, delayed segments, one gap) yields a gap-free or explicitly-gapped file with correct duration.

### NF-07: Image galleries  *(P3 · M · WS B)*
gallery-dl as a managed helper (same install/verify path as NF-05), progress via its JSON output, per-site options. Done when a fixture gallery produces the expected files and respects proxy/limiter.

### NF-08: Debrid services  *(P3 · M · WS B; experimental flag)*
Real-Debrid, AllDebrid, Premiumize via official APIs; tokens in the credential vault; the unrestricted link is held inside the task (never shown, never logged) and re-requested when it expires. Done when a mocked API test covers add/unrestrict/expire/retry.

### NF-09: Site hooks (plugin API)  *(P2 · M · WS B)*
**Why:** some share links are not the file (Google Drive shows a viewer/confirmation page, quota errors). MDM isolates each such site in its own module.
**Design:** `extractors/sites/<site>.py` implements `claims(url)`, `resolve(url, ctx) -> DirectTarget | Refusal`; `Refusal` carries the site's own message so the UI can say "Drive quota exceeded; try later". First hook: Google Drive (large-file confirm token flow, folder links out of scope).
**Done when:** hook registry has tests per site; adding a site is one file.

---

## B. Network and protocols

### NF-10: Proxy / SOCKS / PAC applied everywhere  *(P0 · M · WS H)*
**Why (verified):** Settings has a Proxy tab (`settings_dialog.py`) and stores `proxy_host`/`proxy_proto`, but **no code outside the dialog reads them**, so the proxy has no effect. MDM applies its proxy to downloads and to yt-dlp/gallery-dl.
**Design:** `net/session.py` is the only place that builds `requests`/`aiohttp` sessions. Modes: none · system (env + OS settings) · manual (HTTP/HTTPS/SOCKS4/5, auth) · PAC (`pypac`). `requests[socks]` (PySocks) for SOCKS; `aiohttp-socks` for aiohttp. Per-site bypass list. Pass the same proxy to yt-dlp (`proxy`), ffmpeg (`-http_proxy` or env), and any subprocess. Proxy credentials in the vault.
**Done when:** with a local test proxy, every task kind (direct, HLS, extractor, FTP-over-HTTP-proxy where relevant) shows traffic through it; a proxy failure is a clear `AppError`, not a silent direct connection (fail closed when "require proxy" is set).

### NF-11: Encrypted DNS, hosts overrides, IP pinning  *(P1 · M · WS H)*
**Design:** resolver abstraction (`system`, DoH Cloudflare/Google/custom via `dnspython`), results cached with TTL, optional hosts-file-style overrides, **pinned IPs fed to the connection** (custom adapter/aiohttp resolver) so the SSRF check and the connection use the same address (closes the rebinding window, IM-09). Happy-eyeballs across A/AAAA.
**Done when:** a test resolver proves private-range answers are rejected, pinned IP is what the socket connects to, and DoH failure falls back or fails per setting.

### NF-12: FTP / FTPS (optional SFTP)  *(P1 · M · WS H)*
**Why (verified):** `ftp://` is accepted by the Add dialog and batch dialog, but no FTP client exists in `core/`, so those jobs cannot work. MDM has an FTP engine.
**Design:** `tasks/ftp.py` with `ftplib` (`FTP_TLS` for explicit FTPS), `SIZE`, `REST` resume, passive mode, multiple control+data connections for segmented transfer when the server allows, binary mode, credentials from the vault, proxy support where possible. SFTP via `paramiko` as an optional extra.
**Done when:** tests against a local `pyftpdlib` server cover resume, multi-connection, login failure, and passive mode behind NAT-like config; if you decide **not** to ship FTP, remove `ftp://` from the accepted schemes and say so in docs (never leave a lie in the UI).

### NF-13: Checksum verification  *(P1 · S · WS A,F)*
**Why:** a SHA-256 verify routine exists in `transfer_store.py` but no UI sets it (*verify*). MDM verifies a user-given hash and server-announced digests (`Digest`, `Repr-Digest`, `Content-MD5`, `x-goog-hash`).
**Design:** Add-dialog field "Checksum (optional)" (algo auto-detected by length/prefix); auto-verify when the server announces one; state `VERIFYING`; on mismatch → `CHECKSUM_MISMATCH` with "Re-download" action; stream-hash while writing when possible to avoid a second full read.
**Done when:** mismatch fixture fails the task and keeps the bad file under a `.corrupt` name for inspection.

### NF-15: Network kill switch and helper relay  *(P2 · M · WS H)*
**Why:** p-downloader binds to adapters (`network_binder.py`) but a dropped adapter may fall back to another route; yt-dlp/ffmpeg are not bound at all. MDM runs a loopback relay (password-protected, 127.0.0.1 only) that opens helper connections through the chosen adapter, fails closed (502) when the adapter is down, and closes everything on route change.
**Design:** `net/relay.py` + policy "only through adapter X / VPN"; helpers get `--proxy http://mdm:<pw>@127.0.0.1:<port>`; on adapter loss, pause all tasks (state `PAUSED`, reason `ADAPTER_DOWN`) and resume when it returns.
**Done when:** simulated adapter loss produces zero packets on other interfaces (test with a second bound loopback alias) and tasks resume automatically.

### NF-17: Time-aware limiter  *(P3 · S · WS A)*
"Limit only while I'm at the computer" using OS idle time (Windows `GetLastInputInfo`, Linux/X11/Wayland via optional helper; if unavailable the option is hidden). Uses the existing speed limiter and scheduler.

### NF-14: Real BitTorrent engine  *(P2 · L · WS H)*
**Why (verified):** `core/torrent.py` only parses `.torrent` (bencode) and magnet URIs; there is no peer, tracker, DHT or piece code. The UI accepts magnets, so users will expect real downloads. MDM embeds librqbit (Rust).
**Design:** use `libtorrent` (python bindings, BSD) behind `tasks/torrent.py`; **verify wheel availability for your Python/OS matrix before committing**, fallback: manage `aria2c` over JSON-RPC (GPL-2 binary, separate process). Features in order: magnet metadata fetch → file selection → download → pause/resume (fast-resume data) → sequential mode → limits (down/up, ratio, seed time) → blocklist → port/UPnP → bind to adapter/proxy (NF-10/15).
**Security:** treat `.torrent` as untrusted (keep the bencode depth/size limits already present), sanitize file paths inside torrents, cap file count, no auto-execute.
**Done when:** a local tracker + seeder test downloads a multi-file torrent with selection and resumes after kill; if not shipped, hide magnet/torrent inputs.

### NF-20: Server country display  *(P3 · S · WS H)*
Offline IP→country table (choose a licence-compatible dataset; MaxMind needs an account/licence). Show a flag/code per download; useful with VPN-only mode. Optional, off by default.

---

## C. Managing downloads

### NF-18: Archive extraction and link-grabber packages  *(P2 · M · WS F,A)*
**Design:** the link grabber groups found links into **packages** (common name prefix like `name.part01.rar`, same host, same folder), each package becomes one queue group; on completion extract zip/tar (stdlib), 7z (`py7zr`), RAR (via `rarfile` + a system extractor or 7-Zip) with a password list; optional delete-archive-after (to Recycle Bin/Trash, never `rm`).
**Security:** zip-slip/path traversal, symlink, absolute path, decompression-bomb limits (total size, ratio, file count), nested archive depth limit.
**Done when:** malicious archive fixtures are rejected; multi-part archives extract; failures keep the archive.

### NF-19: RSS / auto-download rules  *(P3 · M · WS G)*
Feeds polled on a schedule, rules (must contain / exclude / episodes / quality), dedupe history; works with direct links and (after NF-14) torrents.

---

## D. Integration and automation

### NF-21: Real CLI  *(P1 · M · WS G)*
**Why:** only a minimal `--url` path exists and it drops `--output`/`--connections` when forwarded to a running instance (IM-12).
**Design:** `pdownloader <command>`: `add`, `list`, `pause`, `resume`, `cancel`, `remove`, `limit`, `queue`, `tools`, `watch`, `settings`. Talks to the running app over the existing authenticated IPC; if no app is running, `--headless` runs the engine in-process. JSON output (`--json`), stable exit codes, shell completion. Optional IDM-style switches (`/d url /p path /f name /n /q`) for people migrating.
**Done when:** every CLI command has a test; forwarding preserves all options (regression test for IM-12).

### NF-22: Local automation API  *(P1 · M · WS G)*
**Design:** loopback HTTP (aiohttp is already a dependency), bearer token (same `0600` token file pattern as IPC), CORS **off**, DNS-rebinding protection (check `Host` header), endpoints = contracts §10, Server-Sent Events for progress, OpenAPI schema in `docs/automation-api.schema.json`.
**Done when:** schema-driven contract tests pass; a request without the token or with a foreign `Host` is rejected.

### NF-25: MCP server  *(P2 · S · WS G)*
Official Python `mcp` SDK; tools: `list_downloads`, `add_download`, `pause`, `resume`, `remove` (confirmation required), `set_speed_limit`, `get_status`; talks to NF-22 with a dedicated, revocable token. Docs: setup for Claude/Cursor/VS Code. Safety: add-download URLs go through the same SSRF guard and router; no tool can read file contents or secrets.

### NF-23: Headless mode and Docker  *(P2 · M · WS G)*
`--headless` runs engine + API without Qt (split Qt imports out of `core/`); Dockerfile (non-root, volume for downloads/config, healthcheck on the API), compose example, docs for NAS/Unraid. Done when the container downloads a fixture file driven only through the API.

### NF-24: Phone remote control  *(P3 · L · WS G)*
Pairing code + HTTPS (self-signed pinned or user-provided cert), per-device tokens, revoke list, rate limiting, minimal web UI. Treat as high-risk: threat model first; keep off by default.

### NF-26: Extension release engineering  *(P1 · M · WS C,E)*
Options page (button on/off per site, ignore list, media-type filter, "ask before download"), "Test connection" that reports which hop is broken (extension → host → app → engine), store packages (Chrome Web Store and Edge Add-ons: small one-time developer fee; Firefox AMO: free), privacy policy page, reproducible zip, version sync with the app (IM-18). Add the first-run link from the app (NF-33).

---

## E. Polish and quality

### NF-28: Dark mode, themes, scaling  *(P1 · M · WS F)*
**Why:** `styles.py` defines a single `LIGHT_THEME_STYLESHEET`; 165 hard-coded hex colours sit outside it.
**Design:** token-based QSS generated from a palette dict (IM-08); Light, Dark, High-contrast; "follow system" using `QStyleHints.colorScheme()` and its change signal (Qt ≥ 6.5, matches the current `PyQt6>=6.5.0` requirement); interface scale 100-200% via font/metrics (not pixel hacks); user theme file (TOML/JSON) later.
**Done when:** screenshot tests (offscreen) of main window + 3 dialogs in each theme show no unreadable contrast (check WCAG AA ratios programmatically for the token pairs).

### NF-27: Internationalization  *(P2 · L · WS F)*
**Why:** 0 UI strings are wrapped for translation. MDM ships 86 languages with RTL mirroring.
**Design:** wrap strings with `self.tr()`/`QCoreApplication.translate`, `.ts` files via `pylupdate6`, compile with `lrelease`, language picker (restart-free if feasible), `Qt.LayoutDirection.RightToLeft` for Arabic/Hebrew/Persian/Urdu, locale-aware sizes/dates/speeds, extension `_locales`. Start with English + Hindi + 3-5 high-demand languages; mark machine translations clearly and let contributors fix them by PR. CI check: no untranslated new strings, no overflow (fit audit like MDM's `MDM_FIT_AUDIT`).
**Order:** do IM-07 (split `main_window.py`) first, or you will translate the same strings twice.

### NF-29: Accessibility  *(P2 · M · WS F)*
`setAccessibleName/Description` on every control (none today), logical tab order, visible focus, full keyboard operation (shortcut list in docs), no colour-only status, respect OS high-contrast and reduced-motion. Test with NVDA and Narrator on Windows, Orca on Linux (note MDM itself lists Orca as unsupported: set realistic expectations).

### NF-30: Crash and diagnostics reporter  *(P2 · S · WS D)*
`faulthandler.enable(file)`, `sys.excepthook`, `threading.excepthook`, Qt message handler → local report (version, OS, last 200 log lines redacted, task states without URLs unless the user opts in). "Help → Report a problem" opens a prefilled GitHub issue; nothing is sent automatically. Done when a forced crash in each of main thread, worker thread and Qt slot produces a report with no secrets (test with canary strings).

### NF-31: Signed auto-update  *(P1 · M · WS E)*
GitHub Releases API check (user-controlled frequency), download `SHA256SUMS` + detached **Ed25519 signature** (verify with `cryptography`, which is already a dependency; public key embedded), verify installer hash, then launch installer (Windows) or show package instructions (Linux). Never auto-install silently without consent. Done when a tampered list or installer is refused (test).

### NF-32: Packaging and platforms  *(P2 · L · WS E)*
Windows installer + portable (exist), add Linux `.deb`/`.rpm` (fpm or native tooling) with native-host manifests installed system-wide, AppImage, Docker (NF-23), macOS `.dmg` (needs Apple developer account for signing/notarization; ship as "experimental" until tested on real Macs). PyInstaller must collect yt-dlp's lazily imported extractors. CI builds from tag, runs smoke tests on the built artifact, publishes checksums and signatures. Windows SmartScreen: plan for a code-signing certificate.

### NF-33: First-run setup and integration check  *(P2 · S · WS F,C)*
Welcome dialog: language, download folder, browser integration status per browser (installed? host registered? extension connected?), "Test browser integration" button, clipboard-monitor and file-type capture opt-ins. Replaces silent setup.
