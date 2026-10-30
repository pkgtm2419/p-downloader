/**
 * Optional early GET anchor link capture coordinator.
 * Preserves normal browser navigation, SPA links, form submissions, and context menus.
 */

const DOWNLOAD_EXTENSIONS = new Set([
  'zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz',
  'exe', 'msi', 'dmg', 'pkg', 'deb', 'rpm', 'apk',
  'iso', 'img', 'bin',
  'mp4', 'mkv', 'webm', 'avi', 'mov', 'flv',
  'mp3', 'flac', 'wav', 'aac', 'm4a', 'ogg',
  'pdf', 'epub'
]);

function isDownloadableAnchor(anchor) {
  if (!anchor || !anchor.href) return false;
  const href = anchor.href.trim();
  if (href.startsWith('#') || href.startsWith('javascript:')) return false;

  if (typeof anchor.hasAttribute === 'function' && anchor.hasAttribute('download')) {
    return true;
  }
  if (anchor.download) {
    return true;
  }

  try {
    const url = new URL(href);
    const pathname = url.pathname.toLowerCase();
    const dotIndex = pathname.lastIndexOf('.');
    if (dotIndex !== -1) {
      const ext = pathname.substring(dotIndex + 1);
      if (DOWNLOAD_EXTENSIONS.has(ext)) {
        return true;
      }
    }
  } catch (e) {
    return false;
  }

  return false;
}

function offerEarlyGetLink(event, options = {}) {
  // Opt-in check: must be explicitly enabled
  if (!options || !options.enabled) {
    return false;
  }

  // Preserve events that were already cancelled or use modifiers
  if (!event || event.defaultPrevented) {
    return false;
  }

  // Only handle primary left click
  if (event.button !== 0) {
    return false;
  }

  // Do not interfere if user is opening in new tab or window via modifiers
  if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
    return false;
  }

  // Find enclosing anchor element
  let target = event.target;
  while (target && target.tagName !== 'A') {
    target = target.parentElement;
  }

  if (!target || !isDownloadableAnchor(target)) {
    return false;
  }

  // Eligible for early capture
  return true;
}

// Support both ES Modules and CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { offerEarlyGetLink, isDownloadableAnchor };
}
