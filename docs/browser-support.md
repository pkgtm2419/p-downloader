# P-Downloader Browser Support Matrix & Installation Guide

## Supported Browsers

| Browser | Engine | Native Messaging Registration | Capture Protocol | Incognito / Private Window Support |
| :--- | :--- | :--- | :--- | :--- |
| **Google Chrome** | Chromium MV3 | Windows Registry (`HKCU\Software\Google\Chrome\NativeMessagingHosts`) / Linux `~/.config/google-chrome/NativeMessagingHosts` | Protocol v2 (Reserve -> Commit -> Complete) | Supported (Requires enabling "Allow in Incognito" in `chrome://extensions`) |
| **Microsoft Edge** | Chromium MV3 | Windows Registry (`HKCU\Software\Microsoft\Edge\NativeMessagingHosts`) / Linux `~/.config/microsoft-edge/NativeMessagingHosts` | Protocol v2 (Reserve -> Commit -> Complete) | Supported (Requires enabling "Allow in InPrivate" in `edge://extensions`) |
| **Brave Browser** | Chromium MV3 | Windows Registry (`HKCU\Software\BraveSoftware\Brave-Browser\NativeMessagingHosts`) | Protocol v2 (Reserve -> Commit -> Complete) | Supported |
| **Chromium** | Chromium MV3 | Windows Registry / Linux `~/.config/chromium/NativeMessagingHosts` | Protocol v2 (Reserve -> Commit -> Complete) | Supported |
| **Mozilla Firefox** | Gecko WebExtension | Windows Registry (`HKCU\Software\Mozilla\NativeMessagingHosts`) / Linux `~/.mozilla/native-messaging-hosts` | Protocol v2 (Allowed Extensions: `pdownloader@ultra.download`) | Supported (Requires enabling "Run in Private Windows") |

---

## Architecture & Safety Guarantees

1. **Transactional 2-Phase Handoff**:
   - The browser extension probes eligibility (`classifyDownload`).
   - If eligible, the extension issues a `reserve` request with a timeout.
   - If the desktop daemon is unreachable, the extension cancels the reservation and lets the browser natively download the file without interference.
   - Only after receiving reservation success does the extension cancel the browser download and send `commit`.

2. **No Wildcard Native Origins**:
   - Native host manifests strictly bind to `chrome-extension://mngjniiiieccogdpplbdmmmmnemocbkb/` (Chromium) and `pdownloader@ultra.download` (Firefox).

3. **Secret Redaction & Origin Isolation**:
   - Cookies and authorization headers are strictly isolated to the original effective origin (`scheme://netloc`).
   - If a download redirects across origins to an untrusted domain, all cookies and `Authorization` headers are stripped.
   - Sensitive fields in IPC requests and native host logs are automatically sanitized to `[REDACTED]`.

4. **Link Capture & DOM Protection**:
   - Right clicks, middle clicks, and modifier-assisted clicks (Ctrl+Click, Cmd+Click, Shift+Click) bypass download capture to maintain default browser tab/window navigation.
   - Single-page application router clicks and form submissions are never intercepted.

---

## Installation & Diagnostic Commands

To register the native messaging host automatically for all detected browsers:
```powershell
python -m browser_extension.installer
```

To test the native host communication:
```powershell
python -m unittest tests.test_native_host -v
node --test tests/browser/*.test.mjs
```
