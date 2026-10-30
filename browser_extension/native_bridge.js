/**
 * Native Messaging Bridge with Protocol v2, Request IDs, and Deadlines.
 */

class NativeBridge {
  constructor(hostName = 'com.pdownloader.host') {
    this.hostName = hostName;
    this.port = null;
    this.pendingRequests = new Map();
  }

  ensureConnected() {
    if (this.port) return this.port;
    if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.connectNative) {
      try {
        this.port = chrome.runtime.connectNative(this.hostName);
        this.port.onMessage.addListener((msg) => this._onMessage(msg));
        this.port.onDisconnect.addListener(() => {
          this.port = null;
          for (const [id, req] of this.pendingRequests.entries()) {
            req.reject(new Error('Native host disconnected'));
          }
          this.pendingRequests.clear();
        });
      } catch (e) {
        this.port = null;
      }
    }
    return this.port;
  }

  _onMessage(msg) {
    const reqId = msg.requestId;
    if (reqId && this.pendingRequests.has(reqId)) {
      const { resolve, timer } = this.pendingRequests.get(reqId);
      clearTimeout(timer);
      this.pendingRequests.delete(reqId);
      resolve(msg);
    }
  }

  sendRequest(action, payload = {}, timeoutMs = 3000) {
    return new Promise((resolve, reject) => {
      const port = this.ensureConnected();
      if (!port) {
        return resolve({ ok: false, code: 'HOST_NOT_CONNECTED', message: 'Native host not connected' });
      }

      const requestId = 'req_' + Math.random().toString(36).substring(2, 10);
      const message = {
        protocolVersion: 2,
        requestId,
        action,
        ...payload
      };

      const timer = setTimeout(() => {
        this.pendingRequests.delete(requestId);
        resolve({ ok: false, code: 'TIMEOUT', message: 'Native request timed out' });
      }, timeoutMs);

      this.pendingRequests.set(requestId, { resolve, reject, timer });

      try {
        port.postMessage(message);
      } catch (err) {
        clearTimeout(timer);
        this.pendingRequests.delete(requestId);
        resolve({ ok: false, code: 'SEND_ERROR', message: err.message });
      }
    });
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { NativeBridge };
}
