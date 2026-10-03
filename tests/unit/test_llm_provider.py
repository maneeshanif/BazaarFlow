"""Task 49: the LLM provider (PRD I-005) against recorded responses, no network.

The contract: the happy path returns the model's text; a timeout, a 429 and a 5xx are each retried once and then end in
a plain sentence for the user (never a stack trace or provider internals); the provider is switched by two settings.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from agents import Agent, Runner

from app.agent_runtime import llm
from app.core.settings import settings

COMPLETION = {
    "id": "chatcmpl-recorded-1",
    "object": "chat.completion",
    "created": 1759478400,
    "model": "gemini-2.0-flash",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "Salaam! How can I help?"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 21, "completion_tokens": 6, "total_tokens": 27},
}


@pytest.fixture(autouse=True)
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "LLM_MAX_RETRIES", 1)
    monkeypatch.setattr(settings, "LLM_TIMEOUT_SECONDS", 5.0)


def client_for(handler: Callable[[httpx.Request], httpx.Response]) -> tuple[httpx.AsyncClient, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    return httpx.AsyncClient(transport=httpx.MockTransport(record)), seen


async def ask(client: httpx.AsyncClient) -> str:
    agent = Agent(name="t", instructions="Be brief.", model=llm.build_model(client))
    return str((await Runner.run(agent, "hello")).final_output)


async def test_the_happy_path_returns_the_models_text_and_sends_the_configured_model() -> None:
    client, seen = client_for(lambda r: httpx.Response(200, json=COMPLETION))
    assert await ask(client) == "Salaam! How can I help?"
    assert len(seen) == 1
    assert seen[0].url.path.endswith("/chat/completions") and seen[0].headers["authorization"] == "Bearer test-key"
    assert b'"model":"gemini-2.0-flash"' in seen[0].content.replace(b" ", b"")


async def test_a_5xx_is_retried_once_and_then_succeeds() -> None:
    answers = iter([httpx.Response(503, json={"error": {"message": "overloaded"}}), httpx.Response(200, json=COMPLETION)])
    client, seen = client_for(lambda r: next(answers))
    assert await ask(client) == "Salaam! How can I help?"
    assert len(seen) == 2


async def test_a_persistent_5xx_gives_up_after_one_retry_with_a_plain_message() -> None:
    client, seen = client_for(lambda r: httpx.Response(500, json={"error": {"message": "secret internal detail"}}))
    with pytest.raises(Exception) as caught:
        await ask(client)
    assert len(seen) == 2, "one try and one retry, not a loop"
    message = llm.describe_failure(caught.value)
    assert "problem" in message and "secret internal detail" not in message


async def test_a_429_is_retried_once_and_then_reported_as_busy() -> None:
    client, seen = client_for(lambda r: httpx.Response(429, json={"error": {"message": "quota"}}))
    with pytest.raises(Exception) as caught:
        await ask(client)
    assert len(seen) == 2
    assert "busy" in llm.describe_failure(caught.value)


async def test_a_timeout_is_retried_once_and_then_reported_in_words() -> None:
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("took too long", request=request)

    client, seen = client_for(slow)
    with pytest.raises(Exception) as caught:
        await ask(client)
    assert len(seen) == 2
    assert "too long" in llm.describe_failure(caught.value)


async def test_a_rejected_key_never_leaks_into_the_message() -> None:
    client, _ = client_for(lambda r: httpx.Response(401, json={"error": {"message": "Incorrect API key test-key"}}))
    with pytest.raises(Exception) as caught:
        await ask(client)
    assert "test-key" not in llm.describe_failure(caught.value)


def test_the_provider_is_chosen_by_settings_only(monkeypatch: pytest.MonkeyPatch) -> None:
    assert llm.provider_settings()[0] == "gemini"
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "OPENAI_MODEL", "gpt-test")
    provider, key, base_url, model = llm.provider_settings()
    assert (provider, key, base_url, model) == ("openai", "sk-test", "https://api.openai.com/v1", "gpt-test")
    monkeypatch.setattr(settings, "LLM_PROVIDER", "carrier-pigeon")
    with pytest.raises(llm.LlmNotConfigured):
        llm.provider_settings()


def test_a_missing_key_is_a_clear_not_configured_error_not_a_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    with pytest.raises(llm.LlmNotConfigured) as caught:
        llm.build_model()
    assert "switched on" in llm.describe_failure(caught.value)


def test_the_scripted_model_never_loads_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LLM_PROVIDER", "scripted")
    monkeypatch.setattr(settings, "APP_ENV", "production")
    with pytest.raises(llm.LlmNotConfigured):
        llm.build_model()
    monkeypatch.setattr(settings, "APP_ENV", "test")
    assert type(llm.build_model()).__name__ == "ScriptedModel"


def test_unknown_errors_become_a_calm_sentence() -> None:
    assert "Nothing was changed" in llm.describe_failure(RuntimeError("boom with /secret/path"))


def _unused(_: Any) -> None:
    return None
