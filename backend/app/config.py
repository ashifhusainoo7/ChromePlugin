from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    backend_host: str = Field("0.0.0.0", description="Backend host bind")
    backend_port: int = Field(8000, description="Backend port")

    # Audio / STT
    stt_sample_rate_hz: int = Field(16000, description="Expected PCM sample rate for STT")

    # Sentiment thresholds
    sentiment_neg_threshold: float = Field(-0.5, description="Compound score threshold to consider negative")
    sentiment_neg_duration_sec: int = Field(20, description="Duration in seconds of sustained negativity to alert")

    # Email
    smtp_host: Optional[str] = Field(None)
    smtp_port: int = Field(587)
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None
    email_to: List[str] = []

    # Selenium / Chrome
    chrome_profile_path: Optional[Path] = None
    chrome_binary_path: Optional[Path] = None
    extension_path: Optional[Path] = None

    # Model paths
    vosk_model_dir: Path = Field(Path("/workspace/backend/app/models/vosk"))

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    @classmethod
    def _split_email_to(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [e.strip() for e in v.split(",") if e.strip()]
        return v


settings = Settings()