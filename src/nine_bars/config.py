"""Application configuration, loaded from environment variables and ``.env``."""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for 9Bars.

    Values resolve from environment variables prefixed with ``NINE_BARS_``
    (e.g. ``NINE_BARS_PORT``). The ``port`` field also honours Railway's
    injected ``PORT`` variable so the same image works locally and on Railway.
    """

    model_config = SettingsConfigDict(
        env_prefix="NINE_BARS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "9Bars"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = Field(default=9009, validation_alias=AliasChoices("NINE_BARS_PORT", "PORT"))
    log_level: str = "info"
    duckdb_path: str = "data/nine_bars.duckdb"

    # Device boundary: when set, the app talks to a live machine over HTTP/WS
    # instead of replaying the committed fixture shots. e.g. "gaggimate.local".
    device_host: str | None = None

    # Coffee research (issue #7): DeepSeek is OpenAI-compatible. When no API key
    # is configured the researcher falls back to a no-fabrication offline stub.
    deepseek_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("NINE_BARS_DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY"),
    )
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    research_timeout_s: float = 10.0


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance (loads env only once per process)."""
    return Settings()
