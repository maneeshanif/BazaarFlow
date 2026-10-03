"""Settings for the agent service. There is deliberately no database field here (ADR 0003)."""

from __future__ import annotations

from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    # shared secret the API sends in X-Agent-Service-Token; the service is unusable without it
    AGENT_SERVICE_TOKEN: str = ""
    # how the service reaches business data: through the API, with the caller's scoped token, never SQL
    API_BASE_URL: str = "http://localhost:8000"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    @model_validator(mode="after")
    def _token_required_outside_tests(self) -> Self:
        if self.APP_ENV != "test" and not self.AGENT_SERVICE_TOKEN:
            raise ValueError("AGENT_SERVICE_TOKEN must be set (the service refuses unauthenticated calls)")
        return self
