const api = globalThis.browser || chrome;

document.addEventListener('DOMContentLoaded', async () => {
  const chkIntercept = document.getElementById('intercept');
  const chkOverlay = document.getElementById('show-overlay');
  const txtExcluded = document.getElementById('excluded-sites');
  const btnSave = document.getElementById('btn-save');
  const btnDiag = document.getElementById('btn-diag');
  const saveStatus = document.getElementById('save-status');
  const diagResult = document.getElementById('diag-result');

  // Load existing configuration
  try {
    const config = await api.storage.local.get(['interceptDownloads', 'showVideoOverlay', 'excludedHosts']);
    chkIntercept.checked = !!config.interceptDownloads;
    chkOverlay.checked = config.showVideoOverlay !== false;
    if (Array.isArray(config.excludedHosts)) {
      txtExcluded.value = config.excludedHosts.join('\n');
    }
  } catch (err) {
    saveStatus.textContent = 'Failed to load settings: ' + err.message;
  }

  // Save settings
  btnSave.addEventListener('click', async () => {
    try {
      const excluded = txtExcluded.value
        .split('\n')
        .map(s => s.trim().toLowerCase())
        .filter(Boolean);

      await api.storage.local.set({
        interceptDownloads: chkIntercept.checked,
        showVideoOverlay: chkOverlay.checked,
        excludedHosts: excluded
      });

      saveStatus.textContent = 'Settings saved successfully.';
      saveStatus.style.color = '#059669';
      setTimeout(() => { saveStatus.textContent = ''; }, 3000);
    } catch (err) {
      saveStatus.textContent = 'Error saving settings: ' + err.message;
      saveStatus.style.color = '#dc2626';
    }
  });

  // Diagnostics check
  btnDiag.addEventListener('click', async () => {
    diagResult.style.display = 'block';
    diagResult.textContent = 'Sending ping to desktop native messaging bridge (com.pdownloader.host)...';

    try {
      const response = await api.runtime.sendMessage({ action: 'pingDesktop' });
      if (response && response.ok) {
        diagResult.innerHTML = `<span class="status-badge status-ok">CONNECTED</span> Ping round-trip latency: <strong>${response.latency} ms</strong>\n` +
          `Desktop Host: ${JSON.stringify(response.data, null, 2)}`;
      } else {
        diagResult.innerHTML = `<span class="status-badge status-err">ERROR</span> Native messaging bridge failed:\n` +
          `${response?.error || 'No response from bridge'}\n\n` +
          `Troubleshooting:\n` +
          `1. Ensure P-Downloader desktop application has been launched.\n` +
          `2. Check Tools -> Browser Integration -> Refresh Browsers to re-register the native manifest.`;
      }
    } catch (err) {
      diagResult.innerHTML = `<span class="status-badge status-err">FAILED</span> ${err.message}\n\n` +
        `Make sure P-Downloader is installed and the native messaging manifest exists in the registry.`;
    }
  });
});
