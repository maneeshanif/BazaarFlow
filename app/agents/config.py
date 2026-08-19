"""Shared Gemini / OpenAI-compatible client for all agents.

All agents MUST import from here � never create their own client.
"""
from __future__ import annotations
from openai import AsyncOpenAI
from app.core.settings import settings

gemini_client = AsyncOpenAI(
    api_key=settings.GEMINI_API_KEY,
    base_url=settings.GEMINI_BASE_URL,
)

DEFAULT_MODEL = settings.GEMINI_MODEL
