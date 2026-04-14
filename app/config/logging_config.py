from __future__ import annotations

import logging
import os
from pathlib import Path

DEFAULT_LOG_FILE = "logs/magic-assistant.log"
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
CONSOLE_FORMAT = "%(levelname)s [%(name)s] %(message)s"


def configure_logging() -> Path:
    log_file = Path(os.getenv("APP_LOG_FILE") or DEFAULT_LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    resolved_log_file = log_file.resolve()

    if not any(
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, logging.FileHandler)
        for handler in root_logger.handlers
    ):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
        root_logger.addHandler(console_handler)

    if not any(
        isinstance(handler, logging.FileHandler) and Path(
            handler.baseFilename) == resolved_log_file
        for handler in root_logger.handlers
    ):
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root_logger.addHandler(file_handler)

    root_logger.setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    return log_file
