# Google Meet Sentiment Monitor (Chrome Extension + Python Backend)

An enterprise-grade system where a bot joins Google Meet, records tab audio, performs real-time sentiment analysis, and emails alerts when sentiment trends negative.

- Chrome Extension (Manifest V3): UI with HTML/CSS/jQuery, tab audio capture, streaming via WebSocket, live sentiment display.
- Python Backend (FastAPI): WebSocket audio ingestion, Vosk streaming speech-to-text (STT), NLTK VADER sentiment analysis, email alerts, and Selenium (undetected-chromedriver) to join meetings.

## Features
- Use Selenium (undetected-chromedriver) to join Google Meet with low automation fingerprint.
- Real-time STT via Vosk (local, no cloud dependency) with live sentiment scoring.
- Tab audio recording with MediaRecorder (Ogg/Opus) and PCM streaming for STT.
- Email alerts when sustained negative sentiment crosses threshold.
- Enterprise patterns: modular services, configuration via environment, structured logging, basic tests, Docker.

## Architecture
- Chrome Extension
  - Popup UI (HTML/CSS/jQuery) to start/stop monitoring, configure backend URL, display live sentiment.
  - Background service worker + Offscreen document to capture Meet tab audio and stream to backend via WebSocket.
  - Content script injects a minimal in-page overlay and coordinates with background.
- Backend (FastAPI)
  - WebSocket endpoint `/ws/audio-stream` for audio frames; streams through Vosk recognizer.
  - Sentiment service (VADER) provides compound scores and trend tracking with configurable thresholds.
  - Email service via SMTP for alerts.
  - REST endpoint `/api/join` to launch Selenium Meet bot with extension preloaded.

## Requirements
- OS: Linux (tested), macOS; Windows should work with adjustments.
- Python 3.11+
- Chrome/Chromium installed
- For Selenium: a dedicated Chrome profile pre-authenticated with Google (recommended) or credentials via env.

## Quick Start

### 1) Backend (local)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# (First run will auto-download Vosk small model and NLTK VADER lexicon)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Environment variables (create a `.env` in `backend/` or export):

```
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
SENTIMENT_NEG_THRESHOLD=-0.5
SENTIMENT_NEG_DURATION_SEC=20
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=alerts@example.com
SMTP_PASSWORD=change_me
EMAIL_FROM=alerts@example.com
EMAIL_TO=security@example.com,ops@example.com
CHROME_PROFILE_PATH=/home/you/.config/google-chrome/Profile 1
CHROME_BINARY_PATH=/usr/bin/google-chrome
EXTENSION_PATH=/workspace/chrome_extension
```

### 2) Chrome Extension (unpacked)
- Open `chrome://extensions` → Enable Developer Mode
- Load unpacked → select `/workspace/chrome_extension`
- Open the popup, set backend URL (e.g., `ws://localhost:8000/ws/audio-stream`), then open a Google Meet tab and click Start.

### 3) Selenium Meet Bot (optional)
From another terminal:

```bash
cd backend
source .venv/bin/activate
python -m app.services.meet_bot "https://meet.google.com/abc-defg-hij" --profile "$CHROME_PROFILE_PATH" --extension "/workspace/chrome_extension"
```

The bot joins with mic/camera off and relies on the extension to capture tab audio.

## Docker

```bash
docker build -t meet-backend:latest ./backend
docker run --rm -it -p 8000:8000 --env-file backend/.env meet-backend:latest
```

Or with docker-compose (from repo root):

```bash
docker compose up --build
```

## Tests

```bash
cd backend
pytest -q
```

## Notes
- Google Meet UI changes regularly; Selenium selectors are resilient but may need maintenance.
- Audio capture uses Chrome APIs; ensure Chrome prompts are acceptable, and extension permissions are granted.
- For production, secure the WebSocket (wss), configure auth, and harden email (SPF/DKIM/DMARC).
