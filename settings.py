from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized configuration.

    This must be safe to import even when no environment variables are set.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: str = Field(default="dev", alias="APP_ENV")  # dev|prod
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    secret_key: Optional[str] = Field(default=None, alias="SECRET_KEY")

    # Watcher
    watch_path: Optional[Path] = Field(default=None, alias="WATCH_PATH")

    # Database
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    db_echo: bool = Field(default=False, alias="DB_ECHO")
    db_sslmode: Optional[str] = Field(default=None, alias="DB_SSLMODE")  # e.g. require|disable
    db_pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")

    # AI providers
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")

    # Social
    x_bearer_token: Optional[str] = Field(default=None, alias="X_BEARER_TOKEN")
    x_consumer_key: Optional[str] = Field(default=None, alias="X_CONSUMER_KEY")
    x_consumer_secret: Optional[str] = Field(default=None, alias="X_CONSUMER_SECRET")
    x_access_token: Optional[str] = Field(default=None, alias="X_ACCESS_TOKEN")
    x_access_token_secret: Optional[str] = Field(default=None, alias="X_ACCESS_TOKEN_SECRET")

    linkedin_access_token: Optional[str] = Field(default=None, alias="LINKEDIN_ACCESS_TOKEN")
    linkedin_organization_urn: Optional[str] = Field(default=None, alias="LINKEDIN_ORGANIZATION_URN")
    linkedin_author_urn: Optional[str] = Field(default=None, alias="LINKEDIN_AUTHOR_URN")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

