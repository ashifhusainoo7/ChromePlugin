$(function() {
  const wsUrlInput = $("#wsUrl");
  const statusEl = $("#status");
  const sentimentEl = $("#sentiment");
  const barFill = $("#barFill");

  chrome.storage.sync.get(["wsUrl"], (res) => {
    wsUrlInput.val(res.wsUrl || "ws://localhost:8000/ws/audio-stream");
  });

  const updateBar = (compound) => {
    const pct = Math.round(((compound + 1) / 2) * 100);
    barFill.css("width", pct + "%");
    if (compound > 0.05) barFill.css("background", "#27ae60");
    else if (compound < -0.05) barFill.css("background", "#e74c3c");
    else barFill.css("background", "#f1c40f");
  };

  $("#startBtn").on("click", async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const wsUrl = wsUrlInput.val();
    chrome.storage.sync.set({ wsUrl });
    chrome.runtime.sendMessage({ type: "start_capture", tabId: tab.id, wsUrl, meetingId: String(tab.id) }, (resp) => {
      statusEl.text("Capturing…");
    });
  });

  $("#stopBtn").on("click", async () => {
    chrome.runtime.sendMessage({ type: "stop_capture" }, () => {
      statusEl.text("Stopped");
    });
  });

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg?.type === "sentiment_update") {
      sentimentEl.text(`${msg.label} (${msg.compound.toFixed(2)}) avg ${msg.avg_compound.toFixed(2)}`);
      updateBar(msg.avg_compound);
    }
  });
});