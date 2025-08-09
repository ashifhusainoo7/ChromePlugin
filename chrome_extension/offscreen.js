let mediaStream = null;
let mediaRecorder = null;
let ws = null;
let meetingId = null;
let sampleRate = 16000;
let processorNode = null;
let audioCtx = null;
let sourceNode = null;
let targetTabId = null;

async function start(tabId, wsUrl, meeting) {
  targetTabId = tabId;
  meetingId = meeting;
  await startCapture(tabId);
  await startStreaming(wsUrl);
}

async function stop() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
  if (processorNode) processorNode.disconnect();
  if (sourceNode) sourceNode.disconnect();
  if (audioCtx) await audioCtx.close();
  if (mediaStream) mediaStream.getTracks().forEach(t => t.stop());
  mediaStream = null; processorNode = null; sourceNode = null; audioCtx = null;
  if (ws) { try { ws.close(); } catch(e){} ws = null; }
}

async function startCapture(tabId) {
  // Try capture with targetTabId if supported
  try {
    mediaStream = await new Promise((resolve, reject) => {
      chrome.tabCapture.capture({
        targetTabId: tabId,
        audio: true,
        video: false,
        audioConstraints: {
          mandatory: {
            echoCancellation: true,
            chromeMediaSource: 'tab'
          }
        }
      }, (stream) => {
        if (chrome.runtime.lastError) reject(chrome.runtime.lastError);
        else resolve(stream);
      });
    });
  } catch(e) {
    // Fallback: activate tab then capture active tab
    await chrome.tabs.update(tabId, { active: true });
    mediaStream = await new Promise((resolve, reject) => {
      chrome.tabCapture.capture({ audio: true, video: false }, (stream) => {
        if (chrome.runtime.lastError) reject(chrome.runtime.lastError);
        else resolve(stream);
      });
    });
  }

  // Setup AudioContext and ScriptProcessor for PCM frames
  audioCtx = new AudioContext();
  sampleRate = audioCtx.sampleRate;
  sourceNode = audioCtx.createMediaStreamSource(mediaStream);
  const bufferSize = 4096;
  processorNode = audioCtx.createScriptProcessor(bufferSize, 1, 1);
  sourceNode.connect(processorNode);
  const muteGain = audioCtx.createGain();
  muteGain.gain.value = 0.0;
  processorNode.connect(muteGain);
  muteGain.connect(audioCtx.destination);
  processorNode.onaudioprocess = (e) => {
    const input = e.inputBuffer.getChannelData(0);
    const pcm16 = floatTo16BitPCM(input);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(pcm16);
    }
  };

  // Optional recording of Ogg chunks for archival/storage
  try {
    mediaRecorder = new MediaRecorder(mediaStream, { mimeType: 'audio/ogg; codecs=opus' });
    mediaRecorder.ondataavailable = (ev) => {
      if (!ev.data || ev.data.size === 0) return;
      // Could upload OGG chunks to backend here if needed
    };
    mediaRecorder.start(5000);
  } catch(e) {
    // MediaRecorder may not be supported for tab streams in some cases
  }
}

function floatTo16BitPCM(float32Array) {
  const len = float32Array.length;
  const buffer = new ArrayBuffer(len * 2);
  const view = new DataView(buffer);
  let offset = 0;
  for (let i = 0; i < len; i++, offset += 2) {
    let s = Math.max(-1, Math.min(1, float32Array[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }
  return buffer;
}

async function startStreaming(wsUrl) {
  ws = new WebSocket(wsUrl);
  ws.binaryType = 'arraybuffer';
  ws.onopen = () => {
    ws.send(JSON.stringify({ type: 'start', meeting_id: meetingId, sample_rate_hz: sampleRate }));
  };
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'sentiment_update') {
        chrome.runtime.sendMessage({ ...data, tabId: targetTabId });
      }
    } catch(e) {
      // ignore non-JSON (if any)
    }
  };
  ws.onclose = () => {};
  ws.onerror = () => {};
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.target !== 'offscreen') return;
  if (msg.action === 'start') {
    start(msg.tabId, msg.wsUrl, msg.meetingId).then(() => sendResponse({ ok: true })).catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true;
  } else if (msg.action === 'stop') {
    stop().then(() => sendResponse({ ok: true }));
    return true;
  }
});