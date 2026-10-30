import test from 'node:test';
import assert from 'node:assert/strict';
import { classifyDownload } from '../../browser_extension/capture_policy.js';
import { offerEarlyGetLink } from '../../browser_extension/link_capture.js';

test('classifyDownload rejects blob: and data: schemes', () => {
  const blobRes = classifyDownload('blob:https://example.com/uuid-1234', 'GET', 'https://example.com', 'application/zip');
  assert.equal(blobRes.captureable, false);
  assert.equal(blobRes.reason, 'UNSUPPORTED_SCHEME');

  const dataRes = classifyDownload('data:image/png;base64,iVBORw0KGgo...', 'GET', 'https://example.com', 'image/png');
  assert.equal(dataRes.captureable, false);
  assert.equal(dataRes.reason, 'UNSUPPORTED_SCHEME');
});

test('classifyDownload rejects non-GET methods to protect browser form submissions', () => {
  const postRes = classifyDownload('https://example.com/checkout/download', 'POST', 'https://example.com', 'application/zip');
  assert.equal(postRes.captureable, false);
  assert.equal(postRes.reason, 'UNSUPPORTED_METHOD');
});

test('classifyDownload rejects non-attachment HTML documents', () => {
  const htmlRes = classifyDownload('https://example.com/article/123', 'GET', 'https://example.com', 'text/html; charset=utf-8');
  assert.equal(htmlRes.captureable, false);
  assert.equal(htmlRes.reason, 'HTML_DOCUMENT');
});

test('classifyDownload accepts legitimate media and archive downloads', () => {
  const zipRes = classifyDownload('https://example.com/file.zip', 'GET', 'https://example.com', 'application/zip');
  assert.equal(zipRes.captureable, true);
  assert.equal(zipRes.reason, 'ELIGIBLE');

  const videoRes = classifyDownload('https://example.com/video.mp4', 'GET', 'https://example.com', 'video/mp4');
  assert.equal(videoRes.captureable, true);
  assert.equal(videoRes.reason, 'ELIGIBLE');
});

test('offerEarlyGetLink ignores events with modifier keys', () => {
  const eventCtrl = {
    button: 0,
    ctrlKey: true,
    metaKey: false,
    shiftKey: false,
    altKey: false,
    defaultPrevented: false,
    target: { tagName: 'A', href: 'https://example.com/release.zip' },
    preventDefault: () => {}
  };
  assert.equal(offerEarlyGetLink(eventCtrl, { enabled: true }), false);
});

test('offerEarlyGetLink ignores non-primary mouse clicks', () => {
  const eventRight = {
    button: 2,
    ctrlKey: false,
    metaKey: false,
    shiftKey: false,
    altKey: false,
    defaultPrevented: false,
    target: { tagName: 'A', href: 'https://example.com/release.zip' },
    preventDefault: () => {}
  };
  assert.equal(offerEarlyGetLink(eventRight, { enabled: true }), false);
});

test('offerEarlyGetLink respects opt-in setting', () => {
  const eventPrimary = {
    button: 0,
    ctrlKey: false,
    metaKey: false,
    shiftKey: false,
    altKey: false,
    defaultPrevented: false,
    target: { tagName: 'A', href: 'https://example.com/release.zip' },
    preventDefault: () => {}
  };
  // Disabled by default
  assert.equal(offerEarlyGetLink(eventPrimary, { enabled: false }), false);
  // When enabled and linking to archive
  assert.equal(offerEarlyGetLink(eventPrimary, { enabled: true }), true);
});
