from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class StartStream(BaseModel):
    type: str = Field("start", const=True)
    meeting_id: str
    sample_rate_hz: int


class StopStream(BaseModel):
    type: str = Field("stop", const=True)
    meeting_id: str


class SentimentUpdate(BaseModel):
    type: str = Field("sentiment_update", const=True)
    meeting_id: str
    text: str
    is_final: bool
    compound: float
    label: str
    avg_compound: float


class Alert(BaseModel):
    type: str = Field("alert", const=True)
    meeting_id: str
    reason: str
    avg_compound: float