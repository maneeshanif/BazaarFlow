"""The LLM provider behind every agent (PRD I-005, build-plan task 49).

One OpenAI-compatible client serves both providers: Gemini through its OpenAI-compatible endpoint (the default) and
OpenAI itself. Switching is two environment variables, no code. Every call has a timeout and at most one retry, and a
provider failure becomes a plain sentence for the user instead of a stack trace. The key stays on the server.
"""

from __future__ import annotations

import httpx
from agents import Model, OpenAIChatCompletionsModel
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.core.settings import settings

GEMINI_URL_DEFAULT = "https://generativelanguage.googleapis.com/v1beta/openai/"
OPENAI_URL = "https://api.openai.com/v1"


class LlmNotConfigured(RuntimeError):
    """No API key for the chosen provider."""


def provider_settings() -> tuple[str, str, str, str]:
    """(provider, api key, base url, model) for the provider the environment selects."""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai":
        return provider, settings.OPENAI_API_KEY, OPENAI_URL, settings.OPENAI_MODEL
    if provider == "gemini":
        return provider, settings.GEMINI_API_KEY, settings.GEMINI_BASE_URL or GEMINI_URL_DEFAULT, settings.GEMINI_MODEL
    raise LlmNotConfigured(f"LLM_PROVIDER must be gemini or openai, not {settings.LLM_PROVIDER!r}")


def build_model(http_client: httpx.AsyncClient | None = None) -> Model:
    """The model every agent uses. ``http_client`` lets a contract test replace the network with recorded responses."""
    if settings.LLM_PROVIDER.lower() == "scripted":
        if settings.APP_ENV in {"production", "staging"}:
            raise LlmNotConfigured("The scripted model is for tests and offline demos only")
        from app.agent_runtime.scripted import ScriptedModel

        return ScriptedModel()
    provider, key, base_url, model = provider_settings()
    if not key:
        raise LlmNotConfigured(f"The {provider} API key is not set")
    client = AsyncOpenAI(
        api_key=key,
        base_url=base_url,
        timeout=settings.LLM_TIMEOUT_SECONDS,
        max_retries=settings.LLM_MAX_RETRIES,
        http_client=http_client,  # type: ignore[arg-type]  # the openai package types its own httpx fork
    )
    return OpenAIChatCompletionsModel(model=model, openai_client=client)


def describe_failure(error: BaseException) -> str:
    """A sentence the shopkeeper can act on, never a stack trace and never provider internals."""
    if isinstance(error, LlmNotConfigured):
        return "The AI assistant is not switched on for this shop yet. Ask the owner to finish setting it up."
    if isinstance(error, APITimeoutError):
        return "The AI assistant took too long to answer. Please send your message again in a moment."
    if isinstance(error, RateLimitError):
        return "The AI assistant is very busy right now. Please try again in a minute."
    if isinstance(error, APIConnectionError):
        return "I could not reach the AI assistant. Check your connection and try again."
    if isinstance(error, APIStatusError):
        return "The AI assistant had a problem and could not answer. Please try again in a moment."
    return "Something went wrong while I was working on that. Nothing was changed. Please try again."
