# 01: Architecture and Contracts

Freeze these **before** parallel work starts. Every workstream codes against them. Names of existing tables/modules below are illustrative: adapt to what is in `core/db.py`, `core/transfer_store.py` and `core/engine.py` and record deviations here.

## 1. Target module layout

```
core/
  router.py                 # classify(url, context) -> Route          (NF-01)
  context.py                # BrowserRequestContext + store             (NF-02)  (extends browser_context.py)
  tasks/
    base.py                 # Task protocol, TaskKind, TaskState, Progress
    direct.py               # existing DownloadTask (range engine)
    hls.py                  # new HLS task on the block engine          (IM-01)
    extractor.py            # yt-dlp task                               (NF-01, IM-11)
    ftp.py                  # FTP/FTPS task                             (NF-12)
    torrent.py              # libtorrent task                           (NF-14)
  hls/                      # parser.py, keys.py, fetch.py, merge.py    (IM-01)
  extractors/
    ytdlp_manager.py        # install/update/rollback                   (NF-05)
    sites/                  # site hooks: gdrive.py, ...                (NF-09)
  net/
    session.py              # one place that builds sessions: proxy, DNS, binding, limiter
    proxy.py  dns.py  relay.py  resolver_pin.py
  settings.py               # typed registry                            (IM-20)
  errors.py                 # error taxonomy                            (IM-05)
  logging_setup.py          # rotating, redacting logs                  (IM-04)
  db_migrations/            # 0001_init.sql, 0002_task_kind.sql ...     (IM-03)
  automation/
    ops.py                  # the operations list (section 10)
    api_server.py  cli.py  mcp_server.py
gui/                        # split per IM-07: models/, views/, controllers/, dialogs/
browser_extension/          # see section 5 for the message schema
```

Rule: **GUI never talks to a task class directly**; it calls `automation.ops` (the same operations the CLI, HTTP API and MCP use). One code path means one set of bugs.

## 2. Task interface

```python
class TaskKind(str, Enum):
    DIRECT = "direct"; HLS = "hls"; DASH = "dash"; EXTRACTOR = "extractor"
    FTP = "ftp"; TORRENT = "torrent"

class TaskState(str, Enum):
    QUEUED = "queued"; PROBING = "probing"; RUNNING = "running"; PAUSED = "paused"
    MERGING = "merging"; VERIFYING = "verifying"; COMPLETED = "completed"
    FAILED = "failed"; CANCELLED = "cancelled"

@dataclass
class Progress:
    state: TaskState
    downloaded: int; total: int | None
    speed_bps: float; eta_s: float | None
    connections: int
    message: str = ""              # human text, already translated
    error: AppError | None = None  # typed, see section 8

class Task(Protocol):
    id: str; kind: TaskKind
    def start(self) -> None: ...
    def pause(self) -> None: ...          # keeps staging; idempotent
    def resume(self) -> None: ...
    def cancel(self, delete_files: bool) -> None: ...
    def set_speed_limit(self, bps: int | None) -> None: ...   # MUST work for every kind
    def progress(self) -> Progress: ...
    def to_record(self) -> dict: ...      # everything needed to rebuild after restart
    @classmethod
    def from_record(cls, rec: dict, deps: Deps) -> "Task": ...
```

Invariants: `pause()` never raises and never deletes staging; `cancel()` is the only place staging is deleted; a task is rebuilt by `kind` from the DB, never by sniffing its URL; progress events are rate-limited to ≤ 5/s per task.

## 3. BrowserRequestContext

Builds on the existing `core/browser_context.py` (keep its origin scoping and cross-origin stripping).

```python
@dataclass(frozen=True)
class BrowserRequestContext:
    page_url: str                       # the page that played the media
    referrer: str | None
    user_agent: str | None
    headers: dict[str, str]             # allow-listed only (Accept*, Origin, Range-agnostic)
    cookies: list[Cookie]               # name, value, domain, host_only, path, secure, expires
    incognito: bool = False
    store_id: str | None = None
```

- **Persisted encrypted** with the task (reuse the credential vault / DPAPI code; on Linux use the OS keyring when present, otherwise an app-key file with `0600`). Never in the DB in plaintext, never in logs (extend the redaction tests).
- **Origin-scoped:** cookies and auth headers are sent only to hosts matching cookie domain/path rules; redirects to other origins drop them (already implemented for the direct task; apply to every task kind).
- **Expiry:** tokens in stream URLs expire. A 403/410 mid-download raises `AppError(STREAM_URL_EXPIRED)`; the app asks the extension for a fresh URL (existing refresh dialog) or re-runs the extractor if the task has a `page_url`.
- **Passing to yt-dlp:** write a temporary Netscape cookie file (mode `0600`, deleted in `finally`) and pass `http_headers`; never put cookies on a command line.

## 4. Router decision table (`core/router.py`)

Input: `url`, optional `BrowserRequestContext`, optional hints from the extension (`mediaKind`, `mime`). Output: `Route(kind, reason, extractor_hint)`.

| Order | Condition | Route |
|---|---|---|
| 1 | scheme `magnet:` or path `.torrent` | TORRENT |
| 2 | scheme `ftp`/`ftps` | FTP |
| 3 | extension hint says `hls` or URL path `.m3u8` or `Content-Type` mpegurl | HLS |
| 4 | hint `dash` or `.mpd` or `dash+xml` | DASH (extractor first, native later) |
| 5 | site hook claims URL (e.g. Google Drive) | DIRECT via hook |
| 6 | HEAD/GET-range probe says file (`Content-Disposition`, binary/video/audio `Content-Type`, or known file extension) | DIRECT |
| 7 | probe says HTML | EXTRACTOR: `extract_info(download=False)`; formats found → EXTRACTOR, none → fail with `NO_MEDIA_FOUND` and say why |
| 8 | probe fails | DIRECT with the probe error surfaced (never silent) |

Rules: classification is by **evidence, not hostname**; the router never downloads the body; it runs off the UI thread with a timeout; its decision and reason are written to the task log.

## 5. Native message schema v2 (extension → host → app)

```jsonc
{
  "v": 2,
  "id": "uuid",                           // idempotency key for the transactional handoff
  "action": "download" | "video" | "batch" | "ping",
  "url": "https://...",                    // stream or file URL
  "pageUrl": "https://...",                // page that played it (router/extractor input)
  "mediaKind": "file" | "hls" | "dash" | "page" | "blob",
  "mime": "video/mp4",
  "title": "…",
  "referrer": "https://…",
  "userAgent": "…",
  "cookies": [{ "name":"", "value":"", "domain":"", "hostOnly":false, "path":"/", "secure":true, "exp": 0 }],
  "headers": { "Origin": "…" },            // allow-listed
  "selection": { "variantUrl": "", "audioUrl": "", "formatId": "", "outputFormat": "mp4" | "mp3" | "m4a" },
  "drm": false,
  "incognito": false, "storeId": null,
  "size": 0, "filename": "…"
}
```

- `v` missing ⇒ treat as v1 (today's messages) and fill defaults, so old extensions keep working during rollout.
- The **desktop side must read** `audioUrl`, `outputFormat`, `cookies`, `headers`, `userAgent` (today no Python code reads `audioUrl` or `outputFormat`).
- Limits: URL ≤ 8 KB, cookies ≤ 200 entries / 64 KB, reject unknown top-level keys (log them).
- Response: `{ "ok": true, "taskId": "…" }` or `{ "ok": false, "code": "APP_NOT_RUNNING" | "DRM" | "REFUSED" | ..., "message": "…" }`. On `ok:false` the extension hands the download back to the browser (existing behaviour; keep it).

## 6. Database migrations (`IM-03`)

Today there is no schema version. Add `PRAGMA user_version` and numbered migration files applied in a transaction, with a backup copy of the DB before the first migration.

```sql
-- 0002_task_kind.sql  (illustrative; adapt table/column names)
ALTER TABLE downloads ADD COLUMN kind TEXT NOT NULL DEFAULT 'direct';
ALTER TABLE downloads ADD COLUMN page_url TEXT;
ALTER TABLE downloads ADD COLUMN context_blob BLOB;      -- encrypted BrowserRequestContext
ALTER TABLE downloads ADD COLUMN route_reason TEXT;
ALTER TABLE downloads ADD COLUMN expected_checksum TEXT; -- "sha256:abcd…"
UPDATE downloads SET kind='hls' WHERE lower(url) LIKE '%.m3u8%';
UPDATE downloads SET kind='extractor' WHERE kind='direct' AND (url LIKE '%youtube.com%' OR url LIKE '%youtu.be%');
PRAGMA user_version = 2;
```

Rules: migrations are forward-only; each has a test that upgrades a fixture DB from every previous version; downgrade is not supported (the app refuses to open a newer DB and says so).

## 7. Settings registry (`IM-20`)

One typed registry replaces the ~36 scattered `get_setting("...")` string keys.

```python
Setting("proxy.mode", enum=["none","system","manual","pac"], default="system")
Setting("net.dns", enum=["system","doh-cloudflare","doh-google","doh-custom"], default="system")
Setting("video.concurrent_fragments", int, default=8, min=1, max=32)
...
```

Each setting has: key, type, default, validation, "requires restart" flag, section/label for the UI, and a migration alias for the old key. Import/export as JSON (secrets excluded). The UI is generated from the registry, so a setting can no longer exist in the UI without being read (the proxy bug: the UI saved `proxy_host` and nothing read it).

## 8. Error taxonomy (`core/errors.py`)

`AppError(code, message_key, details, retryable, user_action)`

| Code | Retryable | User-facing meaning |
|---|---|---|
| `NETWORK_TIMEOUT`, `NETWORK_RESET` | yes | transient; auto-retry with backoff |
| `HTTP_4XX_AUTH` (401/403) | no | login or cookies needed / bot check |
| `STREAM_URL_EXPIRED` (403/410 on a token URL) | via refresh | asking the browser for a fresh link |
| `HTTP_429_503` | yes (honor Retry-After) | server asked us to slow down |
| `DRM_PROTECTED` | no | protected video; cannot be saved |
| `NO_MEDIA_FOUND` | no | no video found on this page |
| `EXTRACTOR_OUTDATED` | no | site changed; update extractors |
| `GEO_BLOCKED`, `LOGIN_REQUIRED` | no | say which |
| `DISK_FULL`, `PATH_DENIED`, `NAME_TOO_LONG` | no | say which path |
| `CHECKSUM_MISMATCH` | no | file corrupt; offer re-download |
| `UNSAFE_URL` (SSRF block) | no | blocked for safety, say why |
| `MUX_FAILED` | no | ffmpeg output attached to log |
| `INTERNAL` | no | bug; offers "Copy diagnostics" |

Rule: no `except Exception: pass` (about 59 today). Either handle a specific error, or convert to `AppError`/log with context and re-raise.

## 9. Progress and event schema

Tasks emit `Progress` snapshots through one thread-safe bus; the GUI, CLI (`--watch`), HTTP API (Server-Sent Events) and MCP all subscribe to the same bus. Event types: `task_added`, `task_state`, `task_progress`, `task_log`, `task_done`, `task_failed`. Every event carries `task_id`, `ts`, and is JSON-serializable.

## 10. Automation operations (shared by CLI, API, MCP, GUI)

`add(url|path, options) → task_id` · `list(filter)` · `get(task_id)` · `pause(ids)` · `resume(ids)` · `cancel(ids, delete_files)` · `remove(ids)` · `set_limit(task_id|global, bps)` · `queue_*` · `scheduler_*` · `settings_get/set` · `tools_status/update` (yt-dlp, ffmpeg) · `events(since)`.

Destructive ops (`cancel(delete_files=True)`, `remove`) require an explicit flag; the MCP server asks for confirmation text for these.

## 11. Security invariants (checked in review and CI)

1. Secrets (cookies, tokens, credentials) are encrypted at rest and redacted in logs, crash reports, and diagnostics exports (tests prove it).
2. The IPC/API token file is created `0600` (Linux/macOS) or ACL-restricted (Windows); API binds `127.0.0.1` only unless remote control is on, and then uses TLS + pairing.
3. Every outbound request for user-supplied URLs goes through the SSRF guard (IPv4+IPv6, redirect re-check, IP pinning).
4. Manifests, playlists and archives are untrusted: size, count, depth and path-traversal limits (zip-slip, `..`, absolute paths, symlinks).
5. Subprocesses (yt-dlp, ffmpeg, gallery-dl, 7z) are started with argument lists (never `shell=True`), with timeouts, and with secrets passed by file/env, not argv.
6. Downloaded filenames are sanitized (Windows reserved names, trailing dots/spaces, length, `..`).
7. No telemetry. Anything that leaves the machine is opt-in and user-visible.
