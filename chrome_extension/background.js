/**
 * LinkedIn Profile Scraper - Background Service Worker
 *
 * Handles screenshot capture and coordinates with content scripts.
 * Responds to messages from external connections (CDP / Native Messaging).
 */

// Allow external messages from the Python script via CDP
chrome.runtime.onMessageExternal.addListener(
  (message, sender, sendResponse) => {
    handleMessage(message, sendResponse);
    return true;
  }
);

// Also handle internal messages (from popup or content scripts)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sendResponse);
  return true;
});

async function handleMessage(message, sendResponse) {
  if (message.action === "captureScreenshot") {
    try {
      const [tab] = await chrome.tabs.query({
        active: true,
        currentWindow: true,
      });
      if (!tab) {
        sendResponse({ success: false, error: "No active tab" });
        return;
      }
      const dataUrl = await chrome.tabs.captureVisibleTab(null, {
        format: "png",
      });
      sendResponse({ success: true, dataUrl: dataUrl });
    } catch (err) {
      sendResponse({ success: false, error: err.message });
    }
  } else if (message.action === "extractFromTab") {
    try {
      const [tab] = await chrome.tabs.query({
        active: true,
        currentWindow: true,
      });
      if (!tab) {
        sendResponse({ success: false, error: "No active tab" });
        return;
      }
      const response = await chrome.tabs.sendMessage(tab.id, {
        action: "extractProfile",
      });
      sendResponse(response);
    } catch (err) {
      sendResponse({ success: false, error: err.message });
    }
  }
}
