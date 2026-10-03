"""Helpers shared by the agent tests: the scripted model, scripted replay turns, and a few shop fixtures."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from agents import ModelResponse
from agents.usage import Usage
from httpx import AsyncClient
from openai import APITimeoutError

from app.core.settings import settings
from app.evals.replay import ReplayModel
from tests.pg.conftest import bearer
from tests.pg.test_sales_api import customer as make_customer
from tests.pg.test_sales_api import product as make_product

CHAT = "/api/v1/chat/sales"
APPROVALS = "/api/v1/approvals/"
RUNS = "/api/v1/agent-runs/"


@pytest.fixture(autouse=True)
def scripted_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every agent test runs the rule-based model unless it installs its own."""
    monkeypatch.setattr(settings, "LLM_PROVIDER", "scripted")
    monkeypatch.setattr(settings, "AGENT_MONTHLY_SPEND_CAP_USD", 5.0)
    monkeypatch.setattr(settings, "AGENT_MAX_TOOL_CALLS", 8)
    monkeypatch.setattr(settings, "AGENTS_ENABLED", True)
    monkeypatch.setattr(settings, "AGENT_AUTO_POST_LIMIT", settings.AGENT_AUTO_POST_LIMIT.__class__("0"))


class PricedReplay(ReplayModel):
    """A replay that reports token usage, so spend can be tested."""

    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        response = await super().get_response(*args, **kwargs)
        response.usage = Usage(requests=1, input_tokens=1000, output_tokens=500)
        return response


class FailingAfter(ReplayModel):
    """Serves its turns, then the provider times out."""

    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        if self._next >= len(self._turns):
            raise APITimeoutError(request=httpx.Request("POST", "https://llm.invalid/chat/completions"))  # type: ignore[arg-type]
        return await super().get_response(*args, **kwargs)


def use_model(monkeypatch: pytest.MonkeyPatch, model: Any) -> None:
    monkeypatch.setattr("app.agent_runtime.runtime.build_model", lambda: model)


async def say(client: AsyncClient, acct: dict[str, Any], text: str, session: str = "s1") -> dict[str, Any]:
    res = await client.post(CHAT, json={"message": text, "session_id": session}, headers=bearer(acct))
    assert res.status_code == 200, res.text
    body: dict[str, Any] = res.json()
    return body


async def shop(client: AsyncClient, owner: dict[str, Any]) -> dict[str, Any]:
    """A shop with one product (Rs 2500, 10 in stock) and one customer called Ali Raza."""
    shirt = await make_product(client, owner, "SHIRT", "2500.00", 10, name="Classic Shirt", cost="1800.00")
    ali = await make_customer(client, owner, "+923001110001")
    patched = await client.patch(f"/api/v1/customers/{ali['id']}", json={"name": "Ali Raza"}, headers=bearer(owner))
    assert patched.status_code == 200
    return {"shirt": shirt, "ali": ali}


async def stock(client: AsyncClient, acct: dict[str, Any], product: dict[str, Any]) -> int:
    got: int = (await client.get(f"/api/v1/inventory/{product['id']}", headers=bearer(acct))).json()["qty_on_hand"]
    return got


async def propose_sale(client: AsyncClient, who: dict[str, Any], text: str = "sell 2 classic shirt to ali", session: str = "s1") -> dict[str, Any]:
    """Run the two-step chat (draft, then 'yes') and return the reply that carries the approval card."""
    draft = await say(client, who, text, session)
    assert "Draft sale" in draft["reply"], draft
    confirmed = await say(client, who, "yes", session)
    assert confirmed["actions"], confirmed
    return confirmed
