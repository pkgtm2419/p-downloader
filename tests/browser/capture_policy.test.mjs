import test from 'node:test';
import assert from 'node:assert/strict';
import { decideEligibility } from '../../browser_extension/capture_policy.js';

test('Eligible normal HTTP GET download', () => {
  const item = { url: 'https://example.com/archive.zip', method: 'GET', fileSize: 5000000 };
  const res = decideEligibility(item);
  assert.equal(res.eligible, true);
  assert.equal(res.reason, 'OK');
});

test('Ineligible when capture mode is off', () => {
  const item = { url: 'https://example.com/archive.zip' };
  const res = decideEligibility(item, { captureMode: 'off' });
  assert.equal(res.eligible, false);
  assert.equal(res.reason, 'CAPTURE_MODE_OFF');
});

test('Ineligible for blob: and data: schemes', () => {
  const blobItem = { url: 'blob:https://example.com/uuid-123' };
  assert.equal(decideEligibility(blobItem).eligible, false);
  assert.equal(decideEligibility(blobItem).reason, 'UNSUPPORTED_SCHEME');

  const dataItem = { url: 'data:text/plain;base64,SGVsbG8=' };
  assert.equal(decideEligibility(dataItem).eligible, false);
});

test('Ineligible for POST downloads', () => {
  const postItem = { url: 'https://example.com/export', method: 'POST' };
  assert.equal(decideEligibility(postItem).eligible, false);
  assert.equal(decideEligibility(postItem).reason, 'UNSUPPORTED_METHOD');
});

test('Ineligible for excluded domains', () => {
  const item = { url: 'https://bank.internal.net/statement.pdf' };
  const settings = { excludedHosts: ['bank.internal.net', 'secure.com'] };
  assert.equal(decideEligibility(item, settings).eligible, false);
  assert.equal(decideEligibility(item, settings).reason, 'EXCLUDED_HOST');
});
