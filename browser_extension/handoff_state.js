/**
 * Transactional Browser Ownership Coordinator.
 * Guarantees that the browser download is kept if desktop declines or is unreachable.
 */

async function coordinateHandoff(downloadItem, browserApi, bridge) {
  const captureId = 'cap_' + downloadItem.id + '_' + Date.now();

  // 1. Send RESERVE offer to desktop
  let reserveReply;
  try {
    reserveReply = await bridge.sendRequest('reserve', {
      action: 'reserve',
      captureId,
      url: downloadItem.url,
      filename: downloadItem.filename || '',
      referrer: downloadItem.referrer || '',
      fileSize: downloadItem.fileSize || 0
    }, 2500);
  } catch (e) {
    reserveReply = { ok: false, code: 'BRIDGE_ERROR' };
  }

  // 2. If desktop declined, failed, or timed out -> Keep browser download!
  if (!reserveReply || !reserveReply.ok || reserveReply.state !== 'PREPARED') {
    return 'browser';
  }

  const handoffId = reserveReply.handoffId;

  // 3. Desktop prepared offer. Attempt to cancel original browser download
  let cancelSucceeded = false;
  try {
    if (browserApi && browserApi.downloads && browserApi.downloads.cancel) {
      await new Promise((resolve) => {
        browserApi.downloads.cancel(downloadItem.id, () => {
          cancelSucceeded = !browserApi.runtime.lastError;
          resolve();
        });
      });
    }
  } catch (e) {
    cancelSucceeded = false;
  }

  // 4. If cancellation failed (e.g. browser download finished in the meantime)
  if (!cancelSucceeded) {
    // Release desktop reservation so no duplicate is created
    bridge.sendRequest('release', { handoffId }, 1000).catch(() => {});
    return 'browser';
  }

  // 5. Browser download is cleanly cancelled. Now COMMIT ownership to desktop!
  let commitReply;
  try {
    commitReply = await bridge.sendRequest('commit', { handoffId }, 3000);
  } catch (e) {
    commitReply = { ok: false };
  }

  if (commitReply && commitReply.ok && commitReply.state === 'COMMITTED') {
    return 'desktop';
  }

  // 6. Uncertain commit outcome after browser was canceled -> trigger user recovery
  return 'recovery';
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { coordinateHandoff };
}
