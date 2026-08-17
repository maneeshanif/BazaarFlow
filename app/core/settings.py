"""Centralised application settings loaded from environment variables.

Usage:
    from app.core.settings import settings
    print(settings.DATABASE_URL)

All variables are validated at startup — missing required vars raise an error
instead of silently returning None.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # -- Application -----------------------------------------------------------
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    # -- Database (Supabase PostgreSQL / SQLite fallback) ----------------------
    DATABASE_URL: str = "sqlite+aiosqlite:///./dev.db"

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

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


# Singleton — import this everywhere
settings = Settings()
