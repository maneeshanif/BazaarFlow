"""Shared Gemini / OpenAI-compatible client for all agents.

All agents MUST import from here — never create their own client.
"""
from __future__ import annotations

from app.core.settings import settings
from openai import AsyncOpenAI

# Build a client lazily so import does not fail when GEMINI_API_KEY is unset.
_gemini_client: AsyncOpenAI | None = None


def get_gemini_client() -> AsyncOpenAI:
    global _gemini_client
    if _gemini_client is None:
        key = settings.GEMINI_API_KEY or "placeholder-key-set-GEMINI_API_KEY-in-env"
        _gemini_client = AsyncOpenAI(
            api_key=key,
            base_url=settings.GEMINI_BASE_URL,
        )
    return _gemini_client


# Backwards-compat alias: agents that do `from app.agents.config import gemini_client`
# will now get a property-like proxy. If they call it like a client they just use
# get_gemini_client() instead, but most existing code just imports the name.
# We instantiate once here with placeholder if key missing; real calls will still 
# fail gracefully at runtime (not at import time).
try:
    gemini_client = AsyncOpenAI(
        api_key=settings.GEMINI_API_KEY or "placeholder",
        base_url=settings.GEMINI_BASE_URL,
    )
except Exception:
    gemini_client = None  # type: ignore[assignment]

DEFAULT_MODEL = settings.GEMINI_MODEL