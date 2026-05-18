"""
core/logging_config.py
-----------------------
Structured logging configuration for Job Guard.

Call configure_logging() once at app startup.
All modules then use: logger = logging.getLogger(__name__)
"""

import logging
import sys
from core.config import get_settings


def configure_logging() -> None:
    """Set up root logger with a consistent format and level."""
    settings = get_settings()

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)

    # Avoid duplicate handlers on reload
    if not root.handlers:
        root.addHandler(handler)
    else:
        root.handlers.clear()
        root.addHandler(handler)

    # Quieten noisy third-party loggers
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
