from __future__ import annotations

import os
from loguru import logger


def configure_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    logger.remove()
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level=log_level,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )


__all__ = ["configure_logging", "logger"]