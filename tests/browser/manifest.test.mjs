import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

test('Firefox manifest contains all background scripts, content scripts, and valid permissions', () => {
  const fxPath = path.resolve('browser_extension/manifest.firefox.json');
  const raw = fs.readFileSync(fxPath, 'utf8');
  const manifest = JSON.parse(raw);

  assert.equal(manifest.manifest_version, 2);
  assert.equal(manifest.name, 'P-Downloader Integration Module');

  // Verify background scripts include hls.js, youtube-media.js, and background.js
  assert.ok(Array.isArray(manifest.background.scripts));
  assert.ok(manifest.background.scripts.includes('hls.js'));
  assert.ok(manifest.background.scripts.includes('youtube-media.js'));
  assert.ok(manifest.background.scripts.includes('background.js'));

  // Verify content scripts exist and match YouTube and general web pages
  assert.ok(Array.isArray(manifest.content_scripts));
  assert.ok(manifest.content_scripts.length >= 2);
  const allJs = manifest.content_scripts.flatMap(cs => cs.js);
  assert.ok(allJs.includes('media-choices.js'));
  assert.ok(allJs.includes('link_capture.js'));
  assert.ok(allJs.includes('content.js'));

  // Verify permissions
  assert.ok(manifest.permissions.includes('nativeMessaging'));
  assert.ok(manifest.permissions.includes('webRequest'));

  // Verify options_ui
  assert.ok(manifest.options_ui);
  assert.equal(manifest.options_ui.page, 'options.html');
});

test('Chrome MV3 manifest contains service worker, content scripts, and options_ui', () => {
  const crPath = path.resolve('browser_extension/manifest.json');
  const raw = fs.readFileSync(crPath, 'utf8');
  const manifest = JSON.parse(raw);

  assert.equal(manifest.manifest_version, 3);
  assert.equal(manifest.background.service_worker, 'background.js');
  assert.ok(Array.isArray(manifest.content_scripts));
  assert.ok(manifest.options_ui);
  assert.equal(manifest.options_ui.page, 'options.html');
});
