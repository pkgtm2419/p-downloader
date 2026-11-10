# P-Downloader: Master Roadmap (new features + improvements)

> Repo: `github.com/pkgtm2419/p-downloader` · baseline v1.0.7 · Python 3.10+ / PyQt6 + browser extension + native host
> This folder is the single source of truth for what to build next. It supersedes the scattered plans in the repo root (`UPGRADE_PLAN.md`, the dated plan, `.gsd/*`).

## Files in this folder

| File | What it holds |
|---|---|
| `00-INDEX.md` | This page: the master table, milestones, how to read IDs |
| `01-ARCHITECTURE-AND-CONTRACTS.md` | Interfaces every workstream must agree on **before** coding (router, task interface, request context, message schema, DB migrations, settings, errors) |
| `02-NEW-FEATURES.md` | Specs for every missing feature (`NF-xx`) |
| `03-IMPROVE-EXISTING.md` | Specs for improving what already exists (`IM-xx`) |
| `04-AGENT-PLAYBOOK.md` | How to run this with sub-agents, MCP servers and plugins; ready-to-paste agent prompts |
| `PLAN-universal-video-downloader.md` | The earlier bug-level plan (findings B1-B15, reproductions, phases). `IM-xx` items refer back to its `B`-numbers |

## How the evidence was gathered

- p-downloader: cloned, read, tests run (136/137 pass; the one failure is the SSRF test, probably no DNS in the sandbox), two HLS bugs reproduced against a local server.
- Mister Download Manager (MDM, `anefzaoui/misterdownloadmanager`, Rust, GPL-3.0): README, docs, crate layout and key source headers read; **not** run. Its speed claims are the author's own.
- Items marked *(verify)* are suspected from reading and must start with a failing test or a quick check.
- **Licence note:** MDM is GPL-3.0, p-downloader is MIT. Use MDM for *ideas and behaviour*; do not copy its code.

## Reading the IDs

- `NF-xx` = new feature, `IM-xx` = improvement of an existing feature, `B-xx` = bug from the earlier plan.
- **Priority:** P0 = fixes broken/lying behaviour or blocks the main goal · P1 = core to "any site, full speed" or to trust · P2 = strong value · P3 = nice to have.
- **Effort** (ideal engineer-days): S ≤ 1 · M 2-4 · L 5-10.
- **WS** = workstream: A engine/HLS · B extractor/router · C extension · D QA/CI/security · E packaging/docs · F GUI/UX · G automation (CLI/API/MCP) · H network/protocols.

## Master table

### Milestone M0: Stabilize (target v1.1.0)

| ID | Title | Pri | Eff | WS | Depends |
|---|---|---|---|---|---|
| IM-01 | HLS rewrite: IV/padding, pause, audio, fMP4, key rotation, quality choice | P0 | L | A | contracts |
| IM-02 | One task interface; `kind` column; correct resume after restart | P0 | M | A | IM-03 |
| IM-03 | DB schema versioning + migrations | P0 | S | A | none |
| NF-02 | Request context (cookies/Referer/UA) reaches every task | P0 | M | C,A,B | contracts |
| NF-10 | Proxy / SOCKS / PAC actually applied (UI already exists, nothing reads it) | P0 | M | H | contracts |
| IM-04 | Logging framework (currently none) + log export | P0 | S | D | none |
| IM-05 | Replace swallowed exceptions with typed errors | P1 | M | D | IM-04 |
| IM-09 | SSRF hardening: IPv6, pinning, redirects | P1 | S | D | none |
| IM-18 | CI fixes, version-drift check, hermetic tests | P1 | S | D | none |
| IM-19 | Consolidate docs; kill stale plans | P2 | S | E | none |

### Milestone M1: Any website (target v1.2.0)

| ID | Title | Pri | Eff | WS | Depends |
|---|---|---|---|---|---|
| NF-01 | Universal router: any page URL via yt-dlp | P0 | L | B | NF-02 |
| NF-03 | Extension stream sniffing v2 (DASH, blob, "maybe" manifests, media list) | P0 | M | C | NF-02 |
| NF-04 | DRM detection and clear messages | P1 | S | C,B | NF-03 |
| NF-05 | yt-dlp manager: verified install, update, rollback | P1 | M | B | NF-01 |
| NF-06 | Video options: playlists, subtitles, audio-only, chapters, thumbnails | P1 | M | B,F | NF-01 |
| IM-11 | Accelerated yt-dlp (fragments, chunking, limiter, proxy, cookies) | P1 | M | B | NF-01, NF-10 |
| IM-10 | MV3 service-worker persistence | P1 | S | C | none |
| IM-15 | Firefox parity (MV3) | P1 | M | C | none |
| NF-34 | Live stream recording | P2 | M | A | IM-01 |

### Milestone M2: Network and protocols (target v1.3.0)

| ID | Title | Pri | Eff | WS | Depends |
|---|---|---|---|---|---|
| NF-11 | Encrypted DNS, hosts overrides, IP pinning | P1 | M | H | NF-10 |
| NF-12 | FTP/FTPS (optional SFTP), segmented + resume | P1 | M | H | contracts |
| NF-13 | Checksum verification UI + server digests | P1 | S | A,F | none |
| NF-15 | Network kill switch, adapter policy, helper relay | P2 | M | H | NF-10 |
| NF-17 | Time-aware speed limit ("only while I'm at the computer") | P3 | S | A | none |
| IM-13 | HTTP stack/disk performance + honest benchmarks | P1 | M | A | IM-01 |
| IM-25 | Limiter, resource budget and binding apply to every task kind | P1 | M | A | IM-02 |

### Milestone M3: Automation and trust (target v1.4.0)

| ID | Title | Pri | Eff | WS | Depends |
|---|---|---|---|---|---|
| NF-21 | Real CLI | P1 | M | G | contracts |
| NF-22 | Local automation API (loopback, token, OpenAPI) | P1 | M | G | NF-21 |
| NF-25 | MCP server for AI assistants | P2 | S | G | NF-22 |
| NF-23 | Headless mode + Docker | P2 | M | G | NF-22 |
| NF-31 | Signed auto-update | P1 | M | E | none |
| NF-30 | Crash and diagnostics reporter (local, opt-in sharing) | P2 | S | D | IM-04 |
| NF-26 | Extension: store release, options page, "Test connection" | P1 | M | C,E | IM-15 |
| IM-16 | Security hardening round (secrets, IPC, native host, deps) | P1 | M | D | none |
| IM-12 | CLI forwarding bug (drops `--output`/`--connections`) | P2 | S | G | NF-21 |

### Milestone M4: Polish (target v1.5.0)

| ID | Title | Pri | Eff | WS | Depends |
|---|---|---|---|---|---|
| NF-28 | Dark mode, themes, interface scaling | P1 | M | F | IM-08 |
| IM-08 | Remove 165 hard-coded colours; design tokens | P1 | M | F | none |
| IM-07 | Split `main_window.py` (1,376 lines); list model/view | P1 | L | F | none |
| NF-27 | i18n framework + first languages + RTL | P2 | L | F | IM-07 |
| NF-29 | Accessibility (keyboard, screen readers, high contrast) | P2 | M | F | IM-07 |
| NF-33 | First-run setup and "Test browser integration" | P2 | S | F,C | NF-26 |
| NF-18 | Archive extraction + link-grabber packages | P2 | M | F,A | none |
| NF-09 | Site hooks (Google Drive etc.) as a plugin API | P2 | M | B | NF-01 |
| NF-32 | Packaging: .deb, .rpm, AppImage, macOS | P2 | L | E | NF-31 |
| IM-20 | Typed settings registry | P2 | M | F | IM-03 |
| IM-21 | Download list UX (find, filters, bulk ops) *(verify gaps)* | P2 | M | F | IM-07 |
| IM-06 | Type hints (92 of 205 defs) + ruff + mypy in CI | P2 | M | D | none |

### Milestone M5: Heavy features (v2.x)

| ID | Title | Pri | Eff | WS | Depends |
|---|---|---|---|---|---|
| NF-14 | Real BitTorrent engine (libtorrent) | P2 | L | H | IM-02 |
| NF-07 | Image galleries (gallery-dl) | P3 | M | B | NF-05 |
| NF-08 | Debrid services | P3 | M | B | NF-09 |
| NF-19 | RSS / auto-download rules | P3 | M | G | NF-14 |
| NF-24 | Phone remote control (pairing + HTTPS) | P3 | L | G | NF-22 |
| NF-20 | Server country display (offline IP table) | P3 | S | H | none |
| IM-14 | Probe/naming/resume-validation audit | P2 | M | A | none |
| IM-22 | File-exists policy and numbered names audit | P2 | S | A | none |
| IM-17 | Test strategy: E2E, fuzzing, live-site matrix | P1 | L | D | ongoing |

## Dependency picture (critical path)

```
IM-03 (migrations) → IM-02 (task kinds) → IM-01 (HLS) ─┐
contracts → NF-02 (context) → NF-01 (router) → NF-05/06/IM-11 → M1 done
                    └→ NF-03 (sniffing v2) → NF-04 (DRM)
NF-10 (proxy) → NF-11 (DNS) → NF-15 (kill switch/relay)
NF-21 (CLI) → NF-22 (API) → NF-25 (MCP) / NF-23 (Docker) / NF-24 (remote)
```

Do **IM-03, IM-04, contracts** first: everything else leans on them.

## Honest scope notes

- **DRM video** (Netflix etc.) is out of scope; the app must say so (NF-04), never produce a corrupt file.
- **"Any website"** really means *every site yt-dlp supports + generic HLS/DASH/mp4 sniffing*. It stays true only with regular extractor updates (NF-05) and a weekly live-site test (IM-17).
- **BitTorrent, debrid, remote control and macOS** are large and are scheduled last on purpose. Do not let them delay M0-M2.
- Windows code signing, Apple notarization and store accounts need accounts/certificates only you can obtain; plan time for those (NF-26, NF-31, NF-32).
