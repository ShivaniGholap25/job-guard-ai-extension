"""
core/config.py
--------------
Centralised application settings loaded from environment variables.

All other modules import from here — never call os.getenv() directly.
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    # ── Application ───────────────────────────────────────────
    app_name:    str = "Job Guard API"
    app_version: str = "1.0.0"
    debug:       bool = False

    # ── Groq AI ───────────────────────────────────────────────
    groq_api_key:  str = ""
    groq_model:    str = "llama-3.3-70b-versatile"
    groq_max_tokens: int = 300

    # ── CORS ──────────────────────────────────────────────────
    cors_origins: list[str] = ["*"]

    # ── Logging ───────────────────────────────────────────────
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings singleton. Safe to call anywhere."""
    return Settings()
