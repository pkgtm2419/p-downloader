// P-Downloader Ultra - In-Page Video Sniffer & Floating Download Bar
(function () {
  'use strict';

  if (window.__pdownloader_sniffer_injected) return;
  window.__pdownloader_sniffer_injected = true;

  const BADGE_ID = 'pdownloader-video-badge';
  let activeBadge = null;

  function createBadge(videoEl, mediaUrl, videoTitle) {
    if (activeBadge) {
      activeBadge.remove();
      activeBadge = null;
    }

    const badge = document.createElement('div');
    badge.id = BADGE_ID;
    badge.innerHTML = `
      <div style="
        position: absolute;
        z-index: 2147483647;
        top: 12px;
        right: 12px;
        background: rgba(18, 20, 24, 0.92);
        color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-size: 13px;
        font-weight: 600;
        padding: 6px 14px;
        border-radius: 20px;
        border: 1px solid #1E88E5;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 8px;
        backdrop-filter: blur(8px);
        transition: all 0.2s ease;
        user-select: none;
      " onmouseover="this.style.background='#1E88E5'; this.style.transform='scale(1.04)';" onmouseout="this.style.background='rgba(18, 20, 24, 0.92)'; this.style.transform='scale(1)';">
        <span style="font-size: 14px;">⚡</span>
        <span>Download Video</span>
        <span style="font-size: 10px; background: rgba(255,255,255,0.2); padding: 2px 6px; border-radius: 10px;">Ultra</span>
      </div>
    `;

    badge.addEventListener('click', (e) => {
      e.stopPropagation();
      e.preventDefault();

      chrome.runtime.sendMessage({
        action: 'video_detected',
        url: mediaUrl,
        title: videoTitle || document.title || 'Web_Video',
        page_url: window.location.href
      });

      // Quick feedback animation
      const inner = badge.firstElementChild;
      if (inner) {
        inner.innerHTML = '<span>✔️ Sending to P-Downloader...</span>';
        inner.style.background = '#2E7D32';
        setTimeout(() => badge.remove(), 2500);
      }
    });

    // Position container
    const parent = videoEl.parentElement || document.body;
    const computedPos = window.getComputedStyle(parent).position;
    if (computedPos === 'static') {
      parent.style.position = 'relative';
    }
    parent.appendChild(badge);
    activeBadge = badge;
  }

  function inspectVideo(video) {
    if (!video) return;

    let mediaUrl = video.currentSrc || video.src;
    if (!mediaUrl) {
      const source = video.querySelector('source');
      if (source) mediaUrl = source.src;
    }

    if (!mediaUrl || mediaUrl.startsWith('blob:') || mediaUrl.startsWith('data:')) {
      // Look for HLS / MP4 links in page performance entries or window variables
      return;
    }

    createBadge(video, mediaUrl, document.title);
  }

  // Scan on video play and loadedmetadata
  document.addEventListener('play', (e) => {
    if (e.target && e.target.tagName === 'VIDEO') {
      inspectVideo(e.target);
    }
  }, true);

  document.addEventListener('loadedmetadata', (e) => {
    if (e.target && e.target.tagName === 'VIDEO') {
      inspectVideo(e.target);
    }
  }, true);

  // Scan existing videos on page
  function scanExisting() {
    const videos = document.querySelectorAll('video');
    videos.forEach(v => {
      if (v.currentTime > 0 || !v.paused) {
        inspectVideo(v);
      }
    });
  }

  setInterval(scanExisting, 3000);
})();
