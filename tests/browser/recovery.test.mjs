import test from 'node:test';
import assert from 'node:assert/strict';
import { coordinateHandoff } from '../../browser_extension/handoff_state.js';

test('Uncertain commit outcome after browser was canceled triggers recovery status', async () => {
  const downloadItem = { id: 404, url: 'https://example.com/asset.iso' };

  const mockBrowserApi = {
    downloads: {
      cancel: (id, cb) => cb()
    },
    runtime: { lastError: null }
  };

  const mockBridge = {
    sendRequest: async (action) => {
      if (action === 'reserve') {
        return { ok: true, state: 'PREPARED', handoffId: 'hnd_recover' };
      }
      if (action === 'commit') {
        // Host crashed or commit timed out
        return { ok: false, code: 'COMMIT_TIMEOUT' };
      }
      return { ok: false };
    }
  };

  const outcome = await coordinateHandoff(downloadItem, mockBrowserApi, mockBridge);
  assert.equal(outcome, 'recovery');
});
