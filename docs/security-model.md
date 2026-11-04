# Security Architecture & Threat Model

This document outlines the security architecture, threat model, cryptographic safeguards, and data protection practices of **P-Downloader**.

---

## 1. Threat Model & Boundaries

P-Downloader interacts with external untrusted networks, accepts links from browser extensions, and stores user authentication credentials. 

```
┌─────────────────────────────────────────────────────────────┐
│                       Untrusted Web                         │
│  - Malicious CDNs / Servers (Forged headers, 200 vs 206)    │
│  - Cross-Origin Redirects (Credential stealing)             │
│  - Internal Networks (SSRF via Spider)                      │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / HTTPS
┌──────────────────────────────▼──────────────────────────────┐
│                    Network Ingestion Layer                  │
│  - Strict Range Capability Probing (http_probe.py)          │
│  - Origin-Scoped Auth Enforcement (download_models.py)      │
│  - SSRF Filter (spider.py)                                  │
└──────────────────────────────┬──────────────────────────────┘
                               │ Sanitized Ingestion
┌──────────────────────────────▼──────────────────────────────┐
│               Local Host Boundaries & Storage               │
│  - Authenticated IPC Token (0o600 file permissions)         │
│  - Encrypted Credentials Vault (Fernet / DPAPI)             │
│  - Redacted Logging (http_errors.py)                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Credentials Storage & Vault Encryption

Implemented in [`core/credentials_manager.py`](file:///core/credentials_manager.py):
- **Cryptographic Encryption**: Site passwords, Bearer tokens, and HTTP authorization headers are encrypted at rest using **Fernet symmetric encryption** (AES-128 in CBC mode with PKCS7 padding and HMAC-SHA256 authentication).
- **Key Generation & Storage**: The encryption key is derived and stored locally in the user profile directory (`~/.pdownloader/vault.key`) with restricted file permissions (`0o600`), inaccessible to other non-privileged local users.
- **Plaintext Ban**: Passwords and bearer tokens are never written to SQLite database columns in plaintext.

---

## 3. Origin-Scoped Authentication & Redirect Security

A critical vulnerability in legacy downloaders occurs when an authenticated download (`https://secure.example.com/file`) issues an HTTP 302 redirect to an untrusted third-party CDN or mirror (`https://untrusted-mirror.net/file`). Passing the original `Authorization` or `Cookie` headers to the redirect target allows malicious mirrors to steal user sessions.

### Protection Rules:
1. **Origin Matching**: Saved credentials are tied strictly to an exact hostname/domain.
2. **Strip Headers on Cross-Origin Redirects**: If a redirect targets a different domain, scheme, or port, sensitive headers (`Authorization`, `Cookie`, `Proxy-Authorization`) are stripped before executing the redirect request.

---

## 4. SSRF Defense in Web Spider (`core/spider.py`)

When the Web Spider or Site Grabber crawls links from a webpage, malicious pages could embed links targeting internal corporate networks or cloud metadata APIs.

The `is_safe_external_url()` filter enforces:
- **Loopback Blocking**: Rejects `127.0.0.1`, `localhost`, `::1`.
- **Private RFC 1918 Ranges**: Rejects `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`.
- **Link-Local & Cloud Metadata**: Rejects `169.254.169.254` (AWS, GCP, Azure metadata endpoints).
- **Scheme Validation**: Strictly allows `http` and `https` schemes; rejects `file://`, `ftp://`, `gopher://`, or `data://`.

---

## 5. Local IPC Security & Token Authentication

Communication between secondary instances (or browser native hosts) and the main desktop process occurs over a local socket:
1. **Per-Session Secret Token**: At startup, P-Downloader writes a random 32-character cryptographic token to `~/.pdownloader/.ipc_token` with `0o600` permissions.
2. **Handshake Verification**: Every IPC connection must supply this token in its initial handshake frame. Messages lacking a valid token are rejected and dropped immediately.
3. **Loopback Only**: The IPC socket server binds exclusively to `127.0.0.1`, never to external network interfaces (`0.0.0.0`).

---

## 6. Secret Redaction in Diagnostic Logs

To ensure user tokens, session cookies, and passwords never appear in bug reports or log files, [`core/http_errors.py:redact_secrets()`](file:///core/http_errors.py) automatically sanitizes sensitive fields:

- Masks `Authorization: Bearer <token>` -> `Authorization: Bearer [REDACTED]`
- Masks `Cookie: ...` -> `Cookie: [REDACTED]`
- Masks embedded credentials in URLs (`https://user:password@example.com` -> `https://user:[REDACTED]@example.com`)

---

## 7. Native Messaging Host Bounded Parsing

[`browser_extension/pdownloader_native_host.py`](file:///browser_extension/pdownloader_native_host.py) enforces:
- **Length Cap**: Native messaging frame lengths exceeding **1,048,576 bytes (1 MiB)** are rejected immediately to protect against integer-overflow memory allocations.
- **Strict JSON Deserialization**: Incoming payloads are strictly parsed and schema-validated before dispatching to the desktop IPC socket.

