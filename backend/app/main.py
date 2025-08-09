from __future__ import annotations

import asyncio
import json
from collections import defaultdict, deque
from typing import AsyncGenerator, Deque, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.logging_conf import configure_logging
from app.models.sentiment import Alert, SentimentUpdate
from app.services.email_service import EmailService
from app.services.sentiment_service import SentimentService, SentimentTrendTracker
from app.services.stt_service import STTService


configure_logging()
app = FastAPI(title="Meet Sentiment Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

email_service = EmailService()
sentiment_service = SentimentService()


class StreamState:
    def __init__(self, meeting_id: str, sample_rate_hz: int) -> None:
        self.meeting_id = meeting_id
        self.sample_rate_hz = sample_rate_hz
        self.buffer: Deque[bytes] = deque()
        self.closed = False
        self.tracker = SentimentTrendTracker(window_seconds=max(60, settings.sentiment_neg_duration_sec))

    def append(self, data: bytes) -> None:
        self.buffer.append(data)

    def close(self) -> None:
        self.closed = True


streams: Dict[str, StreamState] = {}


async def _pcm_generator(meeting_id: str) -> AsyncGenerator[bytes, None]:
    state = streams[meeting_id]
    while not state.closed or state.buffer:
        if not state.buffer:
            await asyncio.sleep(0.01)
            continue
        data = state.buffer.popleft()
        yield data


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.post("/api/join")
async def api_join(payload: dict) -> JSONResponse:
    meeting_url = payload.get("meeting_url")
    if not meeting_url:
        raise HTTPException(status_code=400, detail="meeting_url required")

    # Lazy import to avoid UC overhead on startup
    from app.services.meet_bot import MeetBot

    bot = MeetBot(
        profile_dir=settings.chrome_profile_path,
        chrome_binary=settings.chrome_binary_path,
        extension_path=settings.extension_path,
    )

    asyncio.get_event_loop().run_in_executor(None, bot.join, meeting_url)
    return JSONResponse({"status": "joining"})


@app.websocket("/ws/audio-stream")
async def ws_audio_stream(ws: WebSocket):
    await ws.accept()
    meeting_id: Optional[str] = None
    sample_rate = settings.stt_sample_rate_hz

    try:
        while True:
            message = await ws.receive()
            if "text" in message and message["text"]:
                try:
                    data = json.loads(message["text"])  # control frames
                except json.JSONDecodeError:
                    continue
                msg_type = data.get("type")
                if msg_type == "start":
                    meeting_id = data.get("meeting_id")
                    sample_rate = int(data.get("sample_rate_hz", sample_rate))
                    if not meeting_id:
                        await ws.close(code=1008)
                        return
                    streams[meeting_id] = StreamState(meeting_id, sample_rate)

                    async def run_stt():
                        try:
                            async for result in _stream_stt(meeting_id, sample_rate):
                                await ws.send_text(json.dumps(result))
                        except Exception as exc:
                            logger.exception(f"STT loop error: {exc}")

                    asyncio.create_task(run_stt())
                elif msg_type == "stop" and meeting_id:
                    state = streams.get(meeting_id)
                    if state:
                        state.close()
                else:
                    # ignore unknown control
                    pass
            elif "bytes" in message and message["bytes"]:
                if not meeting_id:
                    # ignore data before start
                    continue
                state = streams.get(meeting_id)
                if not state:
                    continue
                state.append(message["bytes"])
    except WebSocketDisconnect:
        pass
    finally:
        if meeting_id and meeting_id in streams:
            streams[meeting_id].close()
            del streams[meeting_id]


async def _stream_stt(meeting_id: str, sample_rate: int):
    state = streams[meeting_id]

    async def gen():
        async for chunk in _pcm_generator(meeting_id):
            yield chunk

    loop = asyncio.get_event_loop()

    def blocking_iter():
        # Bridge async -> sync generator for Vosk
        async_gen = gen()
        try:
            while True:
                chunk = asyncio.run_coroutine_threadsafe(async_gen.__anext__(), loop).result()
                yield chunk
        except StopAsyncIteration:
            return

    for stt_result in STTService.stream_recognize(blocking_iter(), sample_rate):
        s = sentiment_service.analyze_text(stt_result.text)
        state.tracker.add(s.compound)
        avg = state.tracker.average()
        payload = SentimentUpdate(
            meeting_id=meeting_id,
            text=stt_result.text,
            is_final=stt_result.is_final,
            compound=s.compound,
            label=s.label,
            avg_compound=avg,
        ).model_dump()
        payload["type"] = "sentiment_update"
        yield payload

        if state.tracker.sustained_negative(
            threshold=settings.sentiment_neg_threshold,
            duration_sec=settings.sentiment_neg_duration_sec,
        ):
            subject = f"Negative sentiment alert: {meeting_id}"
            html = f"""
            <h3>Negative Sentiment Detected</h3>
            <p>Meeting: {meeting_id}</p>
            <p>Average compound: {avg:.3f}</p>
            """
            email_service.send_alert(subject, html)
            # avoid spamming: wait a bit before next alert window
            await asyncio.sleep(settings.sentiment_neg_duration_sec)