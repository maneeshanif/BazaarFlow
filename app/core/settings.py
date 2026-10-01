"""Centralised application settings loaded from environment variables.

Usage:
    from app.core.settings import settings
    print(settings.DATABASE_URL)

All variables are validated at startup � missing required vars raise an error
instead of silently returning None.
"""

from __future__ import annotations

import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_log = logging.getLogger(__name__)
_DEV_SECRET = "dev-only-insecure-secret-key-change-me-before-deploying"


def to_async_url(url: str) -> str:
    """Accept plain ``postgresql://`` and ``+psycopg`` URLs; the app and Alembic both use asyncpg."""
    for prefix in ("postgresql+psycopg://", "postgresql+psycopg2://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix):]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # -- Application -----------------------------------------------------------
    APP_ENV: str = "development"
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    # -- Database (Supabase PostgreSQL / SQLite fallback) ----------------------
    DATABASE_URL: str = "sqlite+aiosqlite:///./dev.db"
    # Direct (non-pooler) connection as the `migrator` role; Alembic only. Falls back to DATABASE_URL.
    DATABASE_URL_MIGRATIONS: str = ""

    # -- AI / LLM --------------------------------------------------------------
    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # -- Meta / WhatsApp Cloud API ---------------------------------------------
    META_VERIFY_TOKEN: str = "test123"
    META_GRAPH_VERSION: str = "v17.0"
    META_GRAPH_BASE: str = "https://graph.facebook.com"

    # -- Meta / Facebook Graph API ---------------------------------------------
    FACEBOOK_PAGE_ID: str = ""
    FACEBOOK_ACCESS_TOKEN: str = ""

    # -- VAPI Voice AI ---------------------------------------------------------
    VAPI_API_KEY: str = ""
    VAPI_WEBHOOK_SECRET: str = ""

    # -- Pexels Images ---------------------------------------------------------
    PEXELS_API_KEY: str = ""

    # -- Scheduler -------------------------------------------------------------
    MARKETING_SCHEDULER_ENABLED: bool = True

    @model_validator(mode="after")
    def _require_secret_outside_dev(self) -> "Settings":
        """Fail fast when no signing key is configured in a real environment (PRD §14, RK-06)."""
        if self.SECRET_KEY:
            return self
        if self.APP_ENV in {"production", "staging"}:
            raise ValueError("SECRET_KEY must be set when APP_ENV is production or staging")
        _log.warning("SECRET_KEY is not set; using an insecure development key (APP_ENV=%s)", self.APP_ENV)
        self.SECRET_KEY = _DEV_SECRET
        return self

    @property
    def migrations_url(self) -> str:
        return self.DATABASE_URL_MIGRATIONS or self.DATABASE_URL

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


# Singleton � import this everywhere
settings = Settings()
