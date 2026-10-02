"""Chat endpoints and the sales agent wiring, fully offline (replaces the two live-LLM chat test files).

The agent runner is replaced by a recording fake, so every assertion is about *our* behaviour: what is passed to the
agent, what comes back, how sessions are reused, which roles may call which endpoint, and that failures never leak.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from agents import Runner
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agents.sales_agent import sales_agent
from app.api.controllers.chat_controller import router
from app.core.auth import get_principal
from app.core.tenancy import Principal
from app.models.tenant import TenantRole


def _client(role: TenantRole) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    principal = Principal(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role=role)  # one caller for every request
    app.dependency_overrides[get_principal] = lambda: principal
    return TestClient(app)


@pytest.fixture
def runner_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    async def fake_run(*args: Any, **kwargs: Any) -> SimpleNamespace:
        calls.append({"input": kwargs.get("input"), "session": kwargs.get("session"), "agent": kwargs.get("starting_agent")})
        return SimpleNamespace(final_output=f"agent says: {kwargs.get('input')}")

    monkeypatch.setattr(Runner, "run", fake_run)
    return calls


def test_sales_chat_returns_the_agent_answer_and_a_generated_session_id(runner_calls: list[dict[str, Any]]) -> None:
    res = _client(TenantRole.staff).post("/chat/sales", json={"message": "What products do you have?"})
    assert res.status_code == 200
    body = res.json()
    assert body["response"] == "agent says: What products do you have?"
    assert body["session_id"].startswith("web_")
    assert runner_calls[0]["agent"] is sales_agent


def test_a_provided_session_id_is_echoed_and_the_same_session_is_reused(runner_calls: list[dict[str, Any]]) -> None:
    client = _client(TenantRole.owner)
    first = client.post("/chat/sales", json={"message": "I want to buy a phone", "session_id": "s-continue"})
    second = client.post("/chat/sales", json={"message": "Under 100000?", "session_id": "s-continue"})
    assert first.json()["session_id"] == second.json()["session_id"] == "s-continue"
    assert runner_calls[0]["session"] is runner_calls[1]["session"], "conversation context lives in one session"


def test_messages_reach_the_agent_unchanged_including_unicode_and_long_text(runner_calls: list[dict[str, Any]]) -> None:
    client = _client(TenantRole.owner)
    special = "What's the price of iPhone 15? 📱 café"
    long_text = "Hello " * 1000
    assert client.post("/chat/sales", json={"message": special}).status_code == 200
    assert client.post("/chat/sales", json={"message": long_text}).status_code == 200
    assert client.post("/chat/sales", json={"message": ""}).status_code == 200
    assert [c["input"] for c in runner_calls] == [special, long_text, ""]


def test_a_malformed_request_is_a_422_and_never_reaches_the_agent(runner_calls: list[dict[str, Any]]) -> None:
    assert _client(TenantRole.owner).post("/chat/sales", json={}).status_code == 422
    assert runner_calls == []


def test_agent_failures_give_a_polite_answer_and_never_leak_the_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("secret upstream detail: key=abc123")

    monkeypatch.setattr(Runner, "run", boom)
    res = _client(TenantRole.owner).post("/chat/sales", json={"message": "hello", "session_id": "s-err"})
    assert res.status_code == 200
    assert "abc123" not in res.text and "secret upstream detail" not in res.text
    assert "try again" in res.json()["response"].lower()


def test_finance_chat_is_for_managers_and_owners_only(runner_calls: list[dict[str, Any]]) -> None:
    assert _client(TenantRole.staff).post("/chat/finance", json={"message": "revenue?"}).status_code == 403
    assert _client(TenantRole.manager).post("/chat/finance", json={"message": "revenue?"}).status_code == 200
    assert _client(TenantRole.staff).post("/chat/inventory", json={"message": "stock?"}).status_code == 200


def test_the_chat_health_check_is_public_and_reports_the_services() -> None:
    app = FastAPI()
    app.include_router(router)  # no auth override: the route must work without a token
    res = TestClient(app).get("/health/chat")
    assert res.status_code == 200
    assert res.json() == {"status": "chat services are running"}


def test_the_sales_agent_delegates_to_the_finance_and_inventory_agents_only() -> None:
    """Replaces the live 'run the real agent' test with a check of how the agent is wired."""
    tool_names = sorted(t.name for t in sales_agent.tools)
    assert tool_names == ["consult_finance_agent", "consult_inventory_agent"]
    instructions = str(sales_agent.instructions).lower()
    assert "never mention stock counts" in instructions, "customers must not be shown stock levels"
