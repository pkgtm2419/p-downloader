// P-Downloader Ultra Chrome / Edge / Firefox Extension Service Worker
const NATIVE_HOST = "com.pdownloader.host";

// Context Menu Setup
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "pdownloader_download_link",
    title: "⚡ Download with P-Downloader Ultra",
    contexts: ["link", "video", "audio", "image"]
  });
  chrome.contextMenus.create({
    id: "pdownloader_download_all",
    title: "📋 Download All Links on Page",
    contexts: ["page"]
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  let targetUrl = info.linkUrl || info.srcUrl;
  if (targetUrl) {
    sendToPDownloader(targetUrl, tab ? tab.url : "", tab ? tab.title : "");
  }
});

// In-Page Video Sniffer Message Receiver
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "video_detected" && message.url) {
    sendToPDownloader(message.url, message.page_url || (sender.tab ? sender.tab.url : ""), message.title || "");
    sendResponse({ status: "ok" });
  }
  return true;
});

// Intercept browser downloads and route to P-Downloader
chrome.downloads.onCreated.addListener((downloadItem) => {
  if (!downloadItem.url || downloadItem.url.startsWith("blob:") || downloadItem.url.startsWith("data:")) {
    return;
  }

  // Cancel slow default browser download
  chrome.downloads.cancel(downloadItem.id, () => {
    chrome.downloads.erase({ id: downloadItem.id });
  });

  // Forward to P-Downloader
  sendToPDownloader(downloadItem.url, downloadItem.referrer || "", downloadItem.filename || "");

  // Notify user
  try {
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icons/icon128.png",
      title: "P-Downloader Ultra",
      message: "Download redirected to P-Downloader for ultra multi-threaded speed!"
    });
  } catch (e) {
    // Notifications optional
  }
});

function sendToPDownloader(url, referer = "", filename = "") {
  try {
    chrome.runtime.sendNativeMessage(
      NATIVE_HOST,
      {
        action: "download",
        url: url,
        referer: referer,
        filename: filename
      },
      (response) => {
        if (chrome.runtime.lastError) {
          console.warn("P-Downloader native host note:", chrome.runtime.lastError.message);
        } else {
          console.log("P-Downloader response:", response);
        }
      }
    );
  } catch (err) {
    console.error("Failed to send download to P-Downloader:", err);
  }
}
