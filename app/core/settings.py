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
    # Local development only: lets the API start without SECRET_KEY using a throwaway key. Ignored in production/staging.
    ALLOW_INSECURE_DEV_SECRET: bool = False
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    # A rotated refresh token presented again within this many seconds is a lost response (reload, second tab), not
    # theft: it gets a fresh token instead of ending the session. 0 restores the strict rule.
    REFRESH_REUSE_GRACE_SECONDS: int = 10
    # Twilio WhatsApp sandbox for the demo (platform level). Per-tenant encrypted credentials replace these in phase 2.
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    LOGIN_MAX_FAILURES: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15
    # Sign-ups allowed per client address per hour (0 = no limit). The only abuse control for the public demo.
    SIGNUP_MAX_PER_HOUR: int = 10
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
    # App secret used to verify X-Hub-Signature-256 on inbound webhooks (required in production/staging)
    META_APP_SECRET: str = ""
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

    # Legacy v1 routers share one JSON store across tenants: off in production/staging unless set to true
    LEGACY_V1_ROUTES: bool | None = None

    # -- Scheduler -------------------------------------------------------------
    MARKETING_SCHEDULER_ENABLED: bool = True

    @model_validator(mode="after")
    def _require_secret_outside_dev(self) -> "Settings":
        """Fail fast when no signing key is configured in a real environment (PRD §14, RK-06)."""
        if self.SECRET_KEY:
            return self
        if self.APP_ENV == "test":
            self.SECRET_KEY = _DEV_SECRET
            return self
        if self.ALLOW_INSECURE_DEV_SECRET and self.APP_ENV not in {"production", "staging"}:
            _log.warning("SECRET_KEY is not set; using an insecure development key (ALLOW_INSECURE_DEV_SECRET)")
            self.SECRET_KEY = _DEV_SECRET
            return self
        # Fail closed for every other environment name (typos such as "prod" included): a signing key that is
        # public in the repository would let anyone forge an owner or platform-admin token.
        raise ValueError(
            "SECRET_KEY must be set (for local development you can set ALLOW_INSECURE_DEV_SECRET=true instead)"
        )

    @property
    def migrations_url(self) -> str:
        return self.DATABASE_URL_MIGRATIONS or self.DATABASE_URL

    @property
    def legacy_routes_enabled(self) -> bool:
        if self.LEGACY_V1_ROUTES is not None:
            return self.LEGACY_V1_ROUTES
        return self.APP_ENV not in {"production", "staging"}

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


# Singleton � import this everywhere
settings = Settings()
