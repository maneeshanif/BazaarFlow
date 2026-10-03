"""Task 29: one test per shop tool, against real Postgres, through the real agent loop and permission gate."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.evals.replay import ToolCall, Turn
from tests.pg.agent_support import RUNS, PricedReplay, say, shop, use_model
from tests.pg.agent_support import scripted_provider as scripted_provider  # noqa: F401  (autouse fixture)
from tests.pg.conftest import bearer, member, register
from tests.pg.test_sales_api import SALES, sale
from tests.unit.test_agent_tool_catalog import DB_BACKED_READS

pytestmark = pytest.mark.pg


async def call(client: AsyncClient, monkeypatch: pytest.MonkeyPatch, who: dict[str, Any], owner: dict[str, Any], tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Run one tool through the real loop; returns its trace step."""
    use_model(monkeypatch, PricedReplay([Turn(tool_calls=[ToolCall(tool, args)]), Turn(text="ok")]))
    reply = await say(client, who, f"run {tool}", f"t-{tool}")
    detail = (await client.get(f"{RUNS}{reply['run_id']}", headers=bearer(owner))).json()
    step: dict[str, Any] = detail["trace"][0]
    return step


async def test_every_database_backed_read_tool_is_covered_here(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    await client.post(SALES, json=sale([(items["shirt"], 2)], payment_method="udhaar", customer_id=items["ali"]["id"]), headers=bearer(owner))
    line = {"product_id": items["shirt"]["id"], "qty": 1, "unit_price": None}
    covered = {
        "find_product": {"query": "shirt"},
        "find_customer": {"query": "ali"},
        "get_balance": {"customer_id": items["ali"]["id"]},
        "draft_order": {"items": [line], "customer_id": None, "payment_method": "cash", "amount_paid": None, "discount": None},
        "get_sales_summary": {"period": "today"},
        "get_profit": {"period": "today"},
    }
    assert set(covered) == set(DB_BACKED_READS), "add a case for every database-backed read tool"
    results = {name: await call(client, monkeypatch, owner, owner, name, args) for name, args in covered.items()}
    assert all(step["ok"] for step in results.values()), results
    assert "SHIRT" in results["find_product"]["result"] and "8 in stock" in results["find_product"]["result"]
    assert "[customer]" in results["find_customer"]["result"] or "id=" in results["find_customer"]["result"]
    assert "owes Rs 5,000.00" in results["get_balance"]["result"] or "[customer] owes Rs 5,000.00" in results["get_balance"]["result"]
    assert "Draft sale" in results["draft_order"]["result"] and "total Rs 2,500.00" in results["draft_order"]["result"]
    assert "1 sales, total Rs 5,000.00" in results["get_sales_summary"]["result"]
    assert "profit Rs 1,400.00" in results["get_profit"]["result"]  # 5000 - 2 x 1800


async def test_the_reads_answer_in_words_when_there_is_nothing_to_find(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await register(client, "Shop A")
    none_p = await call(client, monkeypatch, owner, owner, "find_product", {"query": "unicorn"})
    none_c = await call(client, monkeypatch, owner, owner, "find_customer", {"query": "nobody"})
    empty = await call(client, monkeypatch, owner, owner, "get_sales_summary", {"period": "week"})
    assert "No product matches" in none_p["result"] and "No customer matches" in none_c["result"]
    assert "0 sales, total Rs 0.00" in empty["result"]


async def test_bad_arguments_are_explained_to_the_model_not_raised(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    bad_id = await call(client, monkeypatch, owner, owner, "get_balance", {"customer_id": "Ali Raza"})
    assert bad_id["ok"] is False and "id returned by a search" in bad_id["result"]
    bad_qty = await call(
        client, monkeypatch, owner, owner, "draft_order",
        {"items": [{"product_id": items["shirt"]["id"], "qty": 0, "unit_price": None}], "customer_id": None, "payment_method": "cash", "amount_paid": None, "discount": None},
    )
    assert bad_qty["ok"] is False and "qty" in bad_qty["result"]
    bad_money = await call(
        client, monkeypatch, owner, owner, "draft_order",
        {"items": [{"product_id": items["shirt"]["id"], "qty": 1, "unit_price": "lots"}], "customer_id": None, "payment_method": "cash", "amount_paid": None, "discount": None},
    )
    assert bad_money["ok"] is False and "amount" in bad_money["result"]


async def test_write_tools_only_ever_propose(client: AsyncClient, app_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    manager = await member(client, app_engine, owner, "manager")
    await client.post(SALES, json=sale([(items["shirt"], 1)], payment_method="udhaar", customer_id=items["ali"]["id"]), headers=bearer(owner))
    payment = await call(client, monkeypatch, manager, owner, "record_payment", {"customer_id": items["ali"]["id"], "amount": "500", "method": "cash"})
    stock = await call(client, monkeypatch, manager, owner, "adjust_stock", {"product_id": items["shirt"]["id"], "delta": 3, "reason": "purchase", "note": None})
    assert payment["ok"] and "Sent for approval" in payment["result"]
    assert stock["ok"] and "Sent for approval" in stock["result"]
    assert (await client.get(f"/api/v1/customers/{items['ali']['id']}", headers=bearer(owner))).json()["balance"] == "2500.00", "nothing changed yet"
    over = await call(client, monkeypatch, manager, owner, "record_payment", {"customer_id": items["ali"]["id"], "amount": "99999", "method": "cash"})
    assert over["ok"] is False and "only owe" in over["result"]
    too_far = await call(client, monkeypatch, manager, owner, "adjust_stock", {"product_id": items["shirt"]["id"], "delta": -999, "reason": "adjustment", "note": None})
    assert too_far["ok"] is False and "in stock" in too_far["result"]
