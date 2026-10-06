"""Task 78 (F-020): the owner's shop profile and settings, and the per-shop auto-post limit the sales agent obeys."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.tenancy import tenant_session
from tests.pg.agent_support import propose_sale, say, scripted_provider, shop, stock  # noqa: F401
from tests.pg.conftest import bearer, member, register

pytestmark = pytest.mark.pg

URL = "/api/v1/settings/shop"


async def test_the_owner_reads_the_shop_profile(client: AsyncClient) -> None:
    acct = await register(client, "Ali Mart")
    body = (await client.get(URL, headers=bearer(acct))).json()
    assert body["id"] == acct["tenant_id"] and body["name"] == "Ali Mart"
    assert (body["currency"], body["timezone"], body["plan"]) == ("PKR", "Asia/Karachi", "demo")
    assert body["auto_post_limit"] is None and body["effective_auto_post_limit"] == "0.00"
    assert "credentials" not in body and "tenant_id" not in body


async def test_the_owner_edits_the_profile_and_the_change_is_audited(client: AsyncClient) -> None:
    acct = await register(client, "Ali Mart")
    res = await client.patch(
        URL, json={"name": "Ali Mart Lahore", "owner_phone": "+923001234567", "city": "Lahore", "auto_post_limit": "2500.00"}, headers=bearer(acct)
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["name"], body["owner_phone"], body["city"]) == ("Ali Mart Lahore", "+923001234567", "Lahore")
    assert body["auto_post_limit"] == "2500.00" and body["effective_auto_post_limit"] == "2500.00"
    assert (await client.get(URL, headers=bearer(acct))).json()["name"] == "Ali Mart Lahore"
    tid = uuid.UUID(acct["tenant_id"])
    async with tenant_session(tid) as session:
        rows = (await session.execute(text("SELECT action, after_json FROM audit_logs WHERE action = 'shop.updated'"))).all()
    assert len(rows) == 1 and rows[0][1]["name"] == "Ali Mart Lahore"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "a"),
        ("name", "n" * 81),
        ("owner_phone", "03001234567"),
        ("owner_phone", "+1"),
        ("city", "c" * 61),
        ("auto_post_limit", "-1"),
        ("auto_post_limit", "1.234"),
        ("auto_post_limit", "abc"),
    ],
)
async def test_each_field_rule_is_enforced(client: AsyncClient, field: str, value: str) -> None:
    acct = await register(client, "Ali Mart")
    res = await client.patch(URL, json={field: value}, headers=bearer(acct))
    assert res.status_code == 422 and res.json()["code"] == "validation_failed"
    assert field in {e["field"] for e in res.json()["errors"]}


@pytest.mark.parametrize("field", ["plan", "currency", "timezone", "tenant_id", "agents_enabled", "agent_cap_usd", "slug"])
async def test_fields_the_owner_may_not_set_are_rejected(client: AsyncClient, field: str) -> None:
    acct = await register(client, "Ali Mart")
    res = await client.patch(URL, json={field: "x"}, headers=bearer(acct))
    assert res.status_code == 422


async def test_an_empty_update_is_refused_and_null_limit_returns_to_the_default(client: AsyncClient) -> None:
    acct = await register(client, "Ali Mart")
    empty = await client.patch(URL, json={}, headers=bearer(acct))
    assert empty.status_code == 422 and empty.json()["code"] == "empty_update"
    await client.patch(URL, json={"auto_post_limit": "900"}, headers=bearer(acct))
    cleared = (await client.patch(URL, json={"auto_post_limit": None}, headers=bearer(acct))).json()
    assert cleared["auto_post_limit"] is None and cleared["effective_auto_post_limit"] == "0.00"


async def test_only_the_owner_may_open_or_change_settings(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Ali Mart")
    for role in ("manager", "staff"):
        other = await member(client, app_engine, owner, role)
        assert (await client.get(URL, headers=bearer(other))).status_code == 403
        assert (await client.patch(URL, json={"city": "Karachi"}, headers=bearer(other))).status_code == 403
    assert (await client.get(URL)).status_code == 401


async def test_a_shop_only_ever_changes_itself(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    await client.patch(URL, json={"city": "Multan"}, headers=bearer(a))
    assert (await client.get(URL, headers=bearer(b))).json()["city"] != "Multan"


async def test_the_shops_own_limit_decides_whether_the_agent_posts_or_asks(client: AsyncClient) -> None:
    owner: dict[str, Any] = await register(client, "Shop A")
    items = await shop(client, owner)
    asked = await propose_sale(client, owner, "sell 1 classic shirt", "d1")
    assert asked["actions"] and await stock(client, owner, items["shirt"]) == 10  # no limit set: it asks

    await client.patch(URL, json={"auto_post_limit": "3000"}, headers=bearer(owner))
    await say(client, owner, "sell 1 classic shirt", "d2")
    posted = await say(client, owner, "yes", "d2")
    assert posted["actions"] == [] and "Posted" in posted["reply"]
    assert await stock(client, owner, items["shirt"]) == 9

    await client.patch(URL, json={"auto_post_limit": "1000"}, headers=bearer(owner))
    over = await propose_sale(client, owner, "sell 2 classic shirt", "d3")  # Rs 5,000 is above this shop's 1,000
    assert over["actions"], "a sale above the shop's limit still waits for approval"
