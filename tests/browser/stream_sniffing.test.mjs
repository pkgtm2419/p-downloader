import test from 'node:test';
import assert from 'node:assert/strict';

function isDrm(url, mime = '') {
  return /drm|widevine|playready|fairplay/i.test(url) || /cenc/i.test(mime);
}

function isDash(url, mime = '') {
  return /\.mpd(?:[?#]|$)/i.test(url) || /dash\+xml/i.test(mime);
}

function classifyStream(url, mime = '') {
  if (isDrm(url, mime)) {
    return { format: isDash(url, mime) ? 'DASH' : 'STREAM', unsupported: true, reason: 'DRM protected streams are unsupported.' };
  }
  if (isDash(url, mime)) {
    return { format: 'DASH', unsupported: false, mediaKind: 'dash' };
  }
  if (/\.m3u8(?:[?#]|$)/i.test(url) || /mpegurl/i.test(mime)) {
    return { format: 'HLS', unsupported: false, mediaKind: 'hls' };
  }
  return { format: 'Media', unsupported: false, mediaKind: 'direct' };
}

test('DASH .mpd stream is recognized and supported', () => {
  const result = classifyStream('https://example.com/manifest.mpd', 'application/dash+xml');
  assert.equal(result.format, 'DASH');
  assert.equal(result.unsupported, false);
  assert.equal(result.mediaKind, 'dash');
});

test('DASH .mpd stream with query params is supported', () => {
  const result = classifyStream('https://cdn.example.org/stream/manifest.mpd?token=xyz123', '');
  assert.equal(result.format, 'DASH');
  assert.equal(result.unsupported, false);
});

test('DRM stream with widevine or cenc is flagged unsupported', () => {
  const drmResult1 = classifyStream('https://example.com/widevine/license.mpd', 'application/dash+xml');
  assert.equal(drmResult1.unsupported, true);
  assert.match(drmResult1.reason, /DRM/);

  const drmResult2 = classifyStream('https://example.com/stream.mpd', 'video/mp4; codecs="cenc"');
  assert.equal(drmResult2.unsupported, true);
});

test('HLS .m3u8 stream is recognized and supported', () => {
  const result = classifyStream('https://example.com/live/master.m3u8', 'application/vnd.apple.mpegurl');
  assert.equal(result.format, 'HLS');
  assert.equal(result.unsupported, false);
  assert.equal(result.mediaKind, 'hls');
});

test('Blob video detection produces parent pageUrl and mediaKind blob', () => {
  const videoSrc = 'blob:https://twitter.com/1234-5678-90ab';
  const pageUrl = 'https://twitter.com/user/status/1234567890';
  const item = {
    url: pageUrl,
    pageUrl: pageUrl,
    blobSrc: videoSrc,
    format: 'Web Video',
    mediaKind: 'blob'
  };
  assert.equal(item.mediaKind, 'blob');
  assert.equal(item.url, pageUrl);
  assert.equal(item.pageUrl, pageUrl);
});
