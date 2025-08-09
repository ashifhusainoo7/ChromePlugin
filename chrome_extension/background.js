const OFFSCREEN_DOC = "offscreen.html";
let offscreenCreated = false;

async function ensureOffscreenDocument() {
  if (offscreenCreated) return;
  const existing = await chrome.offscreen.hasDocument?.();
  if (existing) {
    offscreenCreated = true;
    return;
  }
  await chrome.offscreen.createDocument({
    url: OFFSCREEN_DOC,
    reasons: ["BLOBS", "AUDIO_PLAYBACK"],
    justification: "Capture Meet tab audio and stream to backend for STT",
  });
  offscreenCreated = true;
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type === "start_capture") {
    ensureOffscreenDocument().then(async () => {
      const tabId = msg.tabId || sender.tab?.id;
      const wsUrl = msg.wsUrl;
      const meetingId = msg.meetingId || String(tabId);
      await chrome.runtime.sendMessage({
        target: "offscreen",
        action: "start",
        tabId,
        wsUrl,
        meetingId,
      });
      sendResponse({ ok: true });
    });
    return true;
  } else if (msg?.type === "stop_capture") {
    chrome.runtime.sendMessage({ target: "offscreen", action: "stop" });
    sendResponse({ ok: true });
    return true;
  } else if (msg?.type === "sentiment_update") {
    // Relay updates to content script and popup
    if (msg.meetingId) {
      chrome.tabs.sendMessage(msg.tabId || sender.tab?.id, msg);
    }
    chrome.runtime.sendMessage(msg);
  }
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url?.startsWith("https://meet.google.com")) {
    // Optionally: auto-start based on a stored setting
  }
});