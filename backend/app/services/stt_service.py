from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional

import numpy as np
import requests
from loguru import logger
from vosk import KaldiRecognizer, Model

from app.config import settings


_MODEL_URL = (
    "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
)
_MODEL_NAME = "vosk-model-small-en-us-0.15"


def _download_and_extract_model(target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    model_dir = target_dir / _MODEL_NAME
    if model_dir.exists():
        logger.info(f"Vosk model already present at {model_dir}")
        return model_dir

    zip_path = target_dir / f"{_MODEL_NAME}.zip"
    logger.info(f"Downloading Vosk model to {zip_path}")
    with requests.get(_MODEL_URL, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    logger.info(f"Extracting {zip_path}")
    import zipfile

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(target_dir)

    zip_path.unlink(missing_ok=True)
    logger.info(f"Vosk model ready at {model_dir}")
    return model_dir


@dataclass
class STTResult:
    text: str
    is_final: bool


class STTService:
    _instance_lock = threading.Lock()
    _model: Optional[Model] = None

    @classmethod
    def ensure_model(cls) -> None:
        with cls._instance_lock:
            if cls._model is not None:
                return
            model_path = _download_and_extract_model(settings.vosk_model_dir)
            cls._model = Model(str(model_path))
            logger.info("Vosk model loaded")

    @classmethod
    def stream_recognize(
        cls, pcm_chunks: Generator[bytes, None, None], sample_rate_hz: int
    ) -> Generator[STTResult, None, None]:
        cls.ensure_model()
        assert cls._model is not None

        recognizer = KaldiRecognizer(cls._model, sample_rate_hz)
        recognizer.SetWords(True)

        for chunk in pcm_chunks:
            if recognizer.AcceptWaveform(chunk):
                result_json = recognizer.Result()
                try:
                    data = json.loads(result_json)
                    text = data.get("text", "").strip()
                except json.JSONDecodeError:
                    text = ""
                if text:
                    yield STTResult(text=text, is_final=True)
            else:
                partial_json = recognizer.PartialResult()
                try:
                    data = json.loads(partial_json)
                    text = data.get("partial", "").strip()
                except json.JSONDecodeError:
                    text = ""
                if text:
                    yield STTResult(text=text, is_final=False)

        final_json = recognizer.FinalResult()
        try:
            data = json.loads(final_json)
            text = data.get("text", "").strip()
        except json.JSONDecodeError:
            text = ""
        if text:
            yield STTResult(text=text, is_final=True)


__all__ = ["STTService", "STTResult"]