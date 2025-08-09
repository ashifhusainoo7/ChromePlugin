(function() {
  const pill = document.createElement('div');
  pill.style.position = 'fixed';
  pill.style.bottom = '12px';
  pill.style.right = '12px';
  pill.style.background = 'rgba(0,0,0,0.7)';
  pill.style.color = '#fff';
  pill.style.padding = '6px 10px';
  pill.style.borderRadius = '999px';
  pill.style.fontFamily = 'system-ui, sans-serif';
  pill.style.fontSize = '12px';
  pill.style.zIndex = '999999';
  pill.textContent = 'Sentiment: —';
  document.body.appendChild(pill);

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg?.type === 'sentiment_update') {
      pill.textContent = `Sentiment: ${msg.label} (${msg.avg_compound.toFixed(2)})`;
      if (msg.avg_compound > 0.05) pill.style.background = '#27ae60';
      else if (msg.avg_compound < -0.05) pill.style.background = '#e74c3c';
      else pill.style.background = '#f1c40f';
    }
  });
})();