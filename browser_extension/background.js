// P-Downloader Chrome / Edge Integration Extension Service Worker
const NATIVE_HOST = "com.pdownloader.host";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "pdownloader_download_link",
    title: "Download with P-Downloader",
    contexts: ["link", "video", "audio", "image"]
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  let targetUrl = info.linkUrl || info.srcUrl;
  if (targetUrl) {
    sendToPDownloader(targetUrl);
  }
});

// Intercept browser downloads
chrome.downloads.onCreated.addListener((downloadItem) => {
  if (downloadItem.url && !downloadItem.url.startsWith("blob:") && !downloadItem.url.startsWith("data:")) {
    // Optionally cancel browser download and route to P-Downloader
    sendToPDownloader(downloadItem.url);
  }
});

function sendToPDownloader(url) {
  try {
    chrome.runtime.sendNativeMessage(
      NATIVE_HOST,
      { action: "download", url: url },
      (response) => {
        if (chrome.runtime.lastError) {
          console.warn("P-Downloader native host error:", chrome.runtime.lastError.message);
        } else {
          console.log("P-Downloader response:", response);
        }
      }
    );
  } catch (err) {
    console.error("Failed to communicate with P-Downloader:", err);
  }
}
