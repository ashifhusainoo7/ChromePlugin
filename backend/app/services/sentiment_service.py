from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

from loguru import logger
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk import download as nltk_download

from app.config import settings


@dataclass
class SentimentScore:
    compound: float
    pos: float
    neu: float
    neg: float
    label: str


class SentimentService:
    def __init__(self) -> None:
        try:
            self.analyzer = SentimentIntensityAnalyzer()
        except Exception:
            nltk_download("vader_lexicon")
            self.analyzer = SentimentIntensityAnalyzer()
        logger.info("Sentiment analyzer ready (VADER)")

    def analyze_text(self, text: str) -> SentimentScore:
        scores = self.analyzer.polarity_scores(text or "")
        compound = scores.get("compound", 0.0)
        label = (
            "positive" if compound >= 0.05 else "negative" if compound <= -0.05 else "neutral"
        )
        return SentimentScore(
            compound=compound,
            pos=scores.get("pos", 0.0),
            neu=scores.get("neu", 0.0),
            neg=scores.get("neg", 0.0),
            label=label,
        )


class SentimentTrendTracker:
    def __init__(self, window_seconds: int) -> None:
        self.window_seconds = window_seconds
        self.samples: Deque[tuple[float, float]] = deque()  # (timestamp, compound)

    def add(self, compound: float) -> None:
        now = time.time()
        self.samples.append((now, compound))
        self._evict_old(now)

    def average(self) -> float:
        if not self.samples:
            return 0.0
        return sum(v for _, v in self.samples) / len(self.samples)

    def sustained_negative(self, threshold: float, duration_sec: int) -> bool:
        now = time.time()
        self._evict_old(now)
        if not self.samples:
            return False
        # Negative for entire duration window
        earliest = now - duration_sec
        values = [v for t, v in self.samples if t >= earliest]
        if not values:
            return False
        avg = sum(values) / len(values)
        return avg <= threshold

    def _evict_old(self, now: float) -> None:
        earliest = now - self.window_seconds
        while self.samples and self.samples[0][0] < earliest:
            self.samples.popleft()


__all__ = ["SentimentService", "SentimentTrendTracker", "SentimentScore"]