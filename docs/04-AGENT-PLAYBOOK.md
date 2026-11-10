# 04: Agent Playbook (how to execute this with sub-agents, MCP servers and plugins)

## 1. Ground rules for every agent

1. **Read first:** `00-INDEX.md`, `01-ARCHITECTURE-AND-CONTRACTS.md`, then only the items you own in `02`/`03`.
2. **Test first:** every bug fix starts with a failing test; every feature starts with a fixture-based test of its acceptance criteria. No network in unit tests (local fixture servers only).
3. **Small PRs:** one item (`NF-xx` / `IM-xx`) per branch/PR, ≤ ~600 changed lines where possible; a mechanical format/lint commit goes in its own PR.
4. **Contracts are frozen:** if you must change a contract (task interface, context, schema v2, DB), stop, write an ADR (`docs/adr/`), and get it merged before continuing. Do not fork the interface locally.
5. **Never weaken a check to go green** (no `xfail` without an issue link, no removing a security test, no broad `except`).
6. **Secrets:** never print, log, commit, or paste cookies, tokens, credentials; use the canary-secret tests.
7. **Licence hygiene:** MDM is GPL-3.0. Read it for behaviour, never copy code or assets. Third-party snippets need a licence note.
8. **Truthful UI:** if a feature is not implemented (FTP, torrents today), the UI must not offer it.
9. **Stop-and-ask list:** anything needing money or accounts (code-signing cert, Apple developer account, store registration), changes to the licence, anything that sends data off the machine, anything that disables a safety check.

## 2. Workstreams and ownership

| WS | Agent | Owns (paths) | First items |
|---|---|---|---|
| A | **engine-agent** | `core/tasks/`, `core/hls/`, `core/engine.py`, `core/segment.py`, `core/transfer_store.py` | IM-03 → IM-02 → IM-01 |
| B | **extractor-agent** | `core/router.py`, `core/tasks/extractor.py`, `core/extractors/` | NF-01, NF-05, IM-11 |
| C | **extension-agent** | `browser_extension/`, native host, `core/browser_handoff.py`, `core/context.py` | NF-02 (extension side), NF-03, IM-10, IM-15 |
| D | **qa-security-agent** | `tests/`, `.github/`, `core/logging_setup.py`, `core/errors.py`, SSRF | IM-04, IM-18, IM-09, IM-05 |
| E | **release-agent** | packaging specs, installer, `docs/`, update/signing | IM-19, NF-31, NF-32 |
| F | **gui-agent** | `gui/`, theming, i18n, accessibility | IM-08, IM-07, NF-28 |
| G | **automation-agent** | `core/automation/` (CLI, API, MCP, headless) | NF-21, NF-22, NF-25 |
| H | **network-agent** | `core/net/` (proxy, DNS, relay), FTP, torrent | NF-10, NF-11, NF-12 |

Parallel safety: files are partitioned by owner; cross-owner changes go through the contract owner (default: engine-agent for task/DB, extension-agent for message schema). Use one git worktree per agent (`git worktree add ../pd-<ws> -b ws/<name>`), rebase on `main` daily, and merge in the order given by the critical path in `00-INDEX.md`.

## 3. Tooling per role

| Need | Use |
|---|---|
| Issues/PRs, labels per item ID, milestones M0-M5 | **GitHub MCP server** (create one issue per `NF`/`IM`, link PRs, tick checklists) |
| Real browser tests, extension E2E, debugging site capture | **Playwright MCP** + Playwright test runner (Chromium with `--load-extension`; Firefox via `web-ext`) |
| Up-to-date docs (yt-dlp options, Chrome MV3, Firefox MV3, Qt, libtorrent, RFC 8216 HLS) | **fetch/web-search MCP** and a docs MCP (e.g., Context7) instead of memory |
| Run code, ffmpeg/ffprobe validation, fixtures | shell/filesystem tools: `ffprobe -v error -show_streams` must show both video and audio and the right duration |
| Fuzzing/property tests | `hypothesis` |
| GUI tests | `pytest-qt`, `QT_QPA_PLATFORM=offscreen` |
| Lint/types/audit | `ruff`, `mypy`, `pip-audit`, `web-ext lint`, `eslint` for the extension |
| Review | a **separate reviewer agent** per phase (see §5) |

Dependencies to add (only when their item starts): `ruff`, `mypy`, `hypothesis`, `pytest-qt`, `pytest-asyncio`, `pypac`, `PySocks`/`requests[socks]`, `aiohttp-socks`, `dnspython`, `pyftpdlib` (tests), `py7zr`, `rarfile`, `libtorrent` *(verify wheels)*, `mcp`, `paramiko` *(optional SFTP)*, `keyring` *(Linux vault)*.

## 4. Ready-to-paste agent prompts

Each prompt is self-contained. Replace `<…>`.

### Common preamble (prepend to every prompt)
> You are working in the repo `pkgtm2419/p-downloader` on branch `ws/<name>`. Read `docs/roadmap/00-INDEX.md` and `01-ARCHITECTURE-AND-CONTRACTS.md` first. Implement only the items listed below. Follow the ground rules in `04-AGENT-PLAYBOOK.md` §1. Work test-first. Run `pytest -q` (with `QT_QPA_PLATFORM=offscreen`) and `node --test tests/browser/*.test.mjs` before every commit. Commit messages: `<ID>: <summary>`. When an item's "Done when" is satisfied, update its checkbox in the issue and stop; do not start adjacent items. If a contract must change, stop and write an ADR.

### engine-agent
> Items: IM-03, IM-02, IM-01. 1) Add numbered SQL migrations with `PRAGMA user_version`, a DB backup before upgrade, and upgrade tests from fixture DBs of v1.0.0…v1.0.7. 2) Introduce the `Task` protocol, `TaskKind`, and the `kind` column; make `resume_download` rebuild tasks by kind. 3) Write `tests/test_hls_correctness.py` reproducing: AES-128 with `EXT-X-MEDIA-SEQUENCE:100` and implicit IV + PKCS#7 padding; pause mid-download then resume; separate audio group; fMP4 with `EXT-X-MAP`; key rotation; clear-then-encrypted; byte-range segments. Confirm they fail, then rewrite `core/hls_downloader.py` as `core/hls/` until they pass. Never write undecrypted bytes on failure; refuse SAMPLE-AES/DRM with `DRM_PROTECTED`. Acceptance: see "Done when" of IM-01/02/03.

### extractor-agent
> Items: NF-01, NF-05, IM-11. Build `core/router.py` exactly per contracts §4 with unit tests per row; replace every `is_youtube_url` gate; generalize `youtube_dialog.py` into a site-agnostic video dialog; add `core/tasks/extractor.py` and `core/extractors/ytdlp_manager.py` (verified install, side-by-side versions, atomic switch, rollback, never downgrade). Then apply IM-11 stage 1 (concurrent fragments, chunk size, limiter, proxy, cookies via temp `0600` Netscape file deleted in `finally`, configurable `extractor_args`). Use recorded fixtures for CI and a separate opt-in live test. Keep yt-dlp errors mapped to `AppError` codes.

### extension-agent
> Items: NF-02 (extension side), NF-03, NF-04, IM-10, IM-15. Implement schema v2 messages (contracts §5) with backward compatibility for v1; collect cookies per cookie-store (incognito/container aware); store per-tab media and context in `chrome.storage.session`; classify responses into hls/dash/file/maybe (ignore segment types and tiny sounds); report `blob:` videos by page URL; detect DRM (EME, ContentProtection, non-AES key methods); add the popup "Media on this page"; ship Firefox as MV3. Add `node --test` cases and a Playwright E2E site serving mp4, HLS (clear + AES), fMP4-HLS, DASH and a blob/MSE player with cookie + Referer checks. Do not request more permissions than needed; justify each in `docs/browser-extension.md`.

### qa-security-agent
> Items: IM-04, IM-18, IM-09, IM-05, IM-16. Add `core/logging_setup.py` with a redaction filter and a canary-secret test; fix CI (Node glob, version-drift script, hermetic SSRF test with an injectable resolver); implement SSRF per IM-09 with the listed test vectors; introduce `core/errors.py` and convert swallowed exceptions in batches of ≤ 15 per PR, each PR adding at least one test for a converted path; add ruff rules `BLE001` and `S110` after the count reaches zero.

### network-agent
> Items: NF-10, NF-11, NF-12 (and NF-15 later). Create `core/net/session.py` as the only factory for HTTP sessions. Make the existing Proxy tab functional (modes none/system/manual/PAC, SOCKS, auth in the vault, bypass list) and prove it with a local test proxy for every task kind; fail closed when "require proxy" is on. Add DoH + pinned-IP connections. Implement FTP/FTPS with `ftplib` (resume, multi-connection when allowed) tested with `pyftpdlib`; if you cannot finish FTP, remove `ftp://` acceptance from the UI and report.

### automation-agent
> Items: NF-21, NF-22, NF-25, IM-12. Implement `core/automation/ops.py` (contracts §10) and make the GUI, CLI, HTTP API and MCP server call it. CLI: `add/list/pause/resume/cancel/remove/limit/queue/tools/watch/settings`, `--json`, stable exit codes, `--headless`. API: loopback only, bearer token file `0600`, `Host`-header check, SSE for events, OpenAPI file. MCP: official SDK, destructive actions require a confirmation argument. Contract tests generated from the OpenAPI file.

### gui-agent
> Items: IM-08, IM-07, NF-28, then NF-27/NF-29. First replace hard-coded colours with tokens and add a lint test. Then split `main_window.py` into a model/view list and controllers that call `automation.ops`; keep behaviour identical (write characterization `pytest-qt` tests first). Then add dark/high-contrast themes with "follow system" using `QStyleHints.colorScheme()`. Only after the split: wrap strings for translation and add accessible names/tab order.

### release-agent
> Items: IM-19, NF-31, NF-32, NF-26 (store packaging). Archive old plans, publish this roadmap under `docs/roadmap/`, add ADRs. Implement update checking with Ed25519-verified `SHA256SUMS`; build Windows installer/portable and Linux artifacts from tags in CI; smoke-test the **built** artifacts; ensure PyInstaller collects yt-dlp extractors. List (do not attempt) the items that need paid accounts or certificates.

## 5. Review loop (after every milestone)

1. **Reviewer agent** (fresh context) gets: the milestone's items, the diff, and the "Done when" lists. Task: *try to break it.* Required probes: malformed/huge manifests and playlists, redirect to `127.0.0.1`/IPv6/metadata IP, cookie leakage across origins, secrets in logs/crash reports/DB, pause/resume/kill -9 races, path traversal in filenames and archives, non-ASCII/very long/Windows-reserved names, offline and flaky-network behaviour, proxy-down behaviour (must not fall back silently).
2. **Benchmark job** compares against the previous milestone's report (IM-13).
3. **Manual smoke** on Windows 11 with Chrome, Edge, Firefox (and one Linux distro): checklist in `docs/manual-test-log.md`, dated and signed off.
4. **Site matrix** refresh (`docs/site-matrix.md`) from the live job.
5. Release notes generated from `CHANGELOG [Unreleased]`; tag; CI builds, signs checksums, publishes.

## 6. Milestone schedule (rough, one focused developer or equivalent agent capacity)

| Milestone | Scope | Rough duration |
|---|---|---|
| M0 Stabilize | contracts, IM-03/02/01, NF-02, NF-10, IM-04/05/09/18 | 3-4 weeks |
| M1 Any website | NF-01/03/04/05/06, IM-11/10/15, NF-34 | 3-4 weeks |
| M2 Network | NF-11/12/13/15/17, IM-13/25 | 2-3 weeks |
| M3 Automation and trust | NF-21/22/25/23/31/30/26, IM-16/12 | 3 weeks |
| M4 Polish | IM-08/07/20/21/06, NF-28/27/29/33/18/09/32 | 5-7 weeks |
| M5 Heavy | NF-14/07/08/19/24/20, IM-14/22/17 | 6+ weeks |

These are estimates, not promises: M0 and M1 carry the most uncertainty (real-world sites), M4 depends on how much of `main_window.py` must be rewritten, and M5 items such as BitTorrent are each a project of their own.

## 7. Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| Sites change and break extractors | "Any site" silently degrades | NF-05 updater, weekly live job (IM-17), clear `EXTRACTOR_OUTDATED` message |
| DRM expectations | Users blame the app | NF-04 detection + docs; never produce corrupt output |
| Legal/ToS | Store rejection or takedowns | First-run notice, no DRM circumvention, privacy policy, store policy review (NF-26) |
| Python packaging of native deps (libtorrent, 7z, ffmpeg) | Broken installers | Verify wheels per OS/Python early; CI builds artifacts and smoke-tests them (NF-32) |
| Big GUI refactor regressions | User-visible bugs | Characterization tests before the split (IM-07) |
| yt-dlp as subprocess vs in-process | Size, speed, isolation trade-offs | Decide in an ADR before NF-05; keep an interface that allows both |
| Scope creep from M5 | Delays M0-M3 | M5 starts only after M3 ships |
| Accounts/certificates not available | Unsigned installers, no store listing | Track as external dependencies; ship unsigned with checksums and a clear note until resolved |
