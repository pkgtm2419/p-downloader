/**
 * Download capture eligibility policy and filtering.
 */

function decideEligibility(downloadItem, settings = {}) {
  const mode = settings.captureMode || 'auto';
  if (mode === 'off') {
    return { eligible: false, reason: 'CAPTURE_MODE_OFF' };
  }

  const url = (downloadItem && downloadItem.url) ? downloadItem.url : '';
  if (!url) {
    return { eligible: false, reason: 'NO_URL' };
  }

  // Scheme checks
  const schemeMatch = url.match(/^([a-z0-9+.-]+):/i);
  const scheme = schemeMatch ? schemeMatch[1].toLowerCase() : '';
  if (scheme !== 'http' && scheme !== 'https') {
    return { eligible: false, reason: 'UNSUPPORTED_SCHEME' };
  }

  // Method checks (POST requests cannot be safely reproduced via standard GET)
  const method = (downloadItem.method || 'GET').toUpperCase();
  if (method !== 'GET') {
    return { eligible: false, reason: 'UNSUPPORTED_METHOD' };
  }

  // Excluded domains
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.toLowerCase();
    const excluded = (settings.excludedHosts || []).map(h => h.toLowerCase());
    if (excluded.some(ex => host === ex || host.endsWith('.' + ex))) {
      return { eligible: false, reason: 'EXCLUDED_HOST' };
    }
  } catch (e) {
    return { eligible: false, reason: 'INVALID_URL' };
  }

  // Minimum size threshold
  const minBytes = settings.minimumBytes || 0;
  if (minBytes > 0 && downloadItem.fileSize && downloadItem.fileSize > 0) {
    if (downloadItem.fileSize < minBytes) {
      return { eligible: false, reason: 'BELOW_MINIMUM_SIZE' };
    }
  }

  return { eligible: true, reason: 'OK' };
}

// Support both ES Modules and CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { decideEligibility };
}
