import test from 'node:test';
import assert from 'node:assert/strict';
import { coordinateHandoff } from '../../browser_extension/handoff_state.js';

test('Desktop decline leaves original browser download intact', async () => {
  const downloadItem = { id: 101, url: 'https://example.com/file.zip' };
  let cancelCalled = false;

  const mockBrowserApi = {
    downloads: {
      cancel: (id, cb) => {
        cancelCalled = true;
        cb();
      }
    },
    runtime: { lastError: null }
  };

  const mockBridge = {
    sendRequest: async (action) => {
      if (action === 'reserve') {
        // Desktop declines offer (e.g. disk quota or auth failed)
        return { ok: false, code: 'DECLINED' };
      }
      return { ok: false };
    }
  };

  const outcome = await coordinateHandoff(downloadItem, mockBrowserApi, mockBridge);
  assert.equal(outcome, 'browser');
  assert.equal(cancelCalled, false, 'Browser download must never be cancelled when desktop declines');
});

test('Successful reservation and cancellation commits ownership to desktop', async () => {
  const downloadItem = { id: 202, url: 'https://example.com/app.exe' };
  let cancelCalled = false;
  let commitCalled = false;

  const mockBrowserApi = {
    downloads: {
      cancel: (id, cb) => {
        cancelCalled = true;
        cb();
      }
    },
    runtime: { lastError: null }
  };

  const mockBridge = {
    sendRequest: async (action, payload) => {
      if (action === 'reserve') {
        return { ok: true, state: 'PREPARED', handoffId: 'hnd_123' };
      }
      if (action === 'commit') {
        commitCalled = true;
        return { ok: true, state: 'COMMITTED', taskId: 'tsk_456' };
      }
      return { ok: true };
    }
  };

  const outcome = await coordinateHandoff(downloadItem, mockBrowserApi, mockBridge);
  assert.equal(outcome, 'desktop');
  assert.equal(cancelCalled, true);
  assert.equal(commitCalled, true);
});

test('Browser cancellation failure releases offer and keeps browser', async () => {
  const downloadItem = { id: 303, url: 'https://example.com/fast.zip' };
  let releaseCalled = false;

  const mockBrowserApi = {
    downloads: {
      cancel: (id, cb) => {
        // Simulation: item already finished downloading in browser
        mockBrowserApi.runtime.lastError = { message: 'Download already complete' };
        cb();
      }
    },
    runtime: { lastError: null }
  };

  const mockBridge = {
    sendRequest: async (action, payload) => {
      if (action === 'reserve') {
        return { ok: true, state: 'PREPARED', handoffId: 'hnd_fast' };
      }
      if (action === 'release') {
        releaseCalled = true;
        return { ok: true, state: 'RELEASED' };
      }
      return { ok: true };
    }
  };

  const outcome = await coordinateHandoff(downloadItem, mockBrowserApi, mockBridge);
  assert.equal(outcome, 'browser');
  assert.equal(releaseCalled, true, 'Reservation must be released if browser download was not cancelled');
});
