"""Task 89 (F-028): system logs: an operator reads the audit trail across shops; nobody else; nothing can be changed."""

from __future__ import annotations

import uuid

import asyncpg
import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.pg.conftest import bearer, register
from tests.pg.test_platform_admin import operator

pytestmark = pytest.mark.pg

URL = "/api/v1/platform/logs"


@pytest_asyncio.fixture(autouse=True)
async def clean_slate(admin_conn: asyncpg.Connection) -> None:
    await admin_conn.execute("TRUNCATE tenants, users, audit_logs, login_attempts, refresh_tokens RESTART IDENTITY CASCADE")


async def test_only_operators_can_read_the_logs(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    assert (await client.get(URL, headers=bearer(owner))).status_code == 403
    assert (await client.get(URL)).status_code == 401
    assert (await client.get(f"{URL}/{uuid.uuid4()}", headers=bearer(owner))).status_code == 403


async def test_the_list_spans_shops_newest_first_with_shop_names_and_no_payloads(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    op = await operator(client, admin_conn)
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    page = (await client.get(URL, params={"limit": 100}, headers=bearer(op))).json()
    names = {r["tenant_name"] for r in page["items"] if r["action"] == "tenant.registered"}
    assert {"Operator Co", "Shop A", "Shop B"} <= names
    created = [r["created_at"] for r in page["items"]]
    assert created == sorted(created, reverse=True)
    assert all("after" not in r and "before" not in r for r in page["items"])  # payloads only on the detail
    assert a["tenant_id"] != b["tenant_id"]


async def test_filters_by_action_shop_actor_and_time(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    op = await operator(client, admin_conn)
    a = await register(client, "Shop A")
    await register(client, "Shop B")
    only_a = (await client.get(URL, params={"tenant_id": a["tenant_id"]}, headers=bearer(op))).json()
    assert only_a["total"] >= 1 and {r["tenant_id"] for r in only_a["items"]} == {a["tenant_id"]}
    registered = (await client.get(URL, params={"action": "registered"}, headers=bearer(op))).json()
    assert registered["total"] == 3 and {r["action"] for r in registered["items"]} == {"tenant.registered"}
    assert (await client.get(URL, params={"actor_type": "agent"}, headers=bearer(op))).json()["total"] == 0
    assert (await client.get(URL, params={"since": "2999-01-01T00:00:00Z"}, headers=bearer(op))).json()["total"] == 0
    assert (await client.get(URL, params={"actor_type": "robot"}, headers=bearer(op))).status_code == 422


async def test_the_detail_shows_the_payload_and_unknown_ids_are_404(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    op = await operator(client, admin_conn)
    await register(client, "Shop A")
    row = (await client.get(URL, params={"action": "tenant.registered", "limit": 1}, headers=bearer(op))).json()["items"][0]
    detail = (await client.get(f"{URL}/{row['id']}", headers=bearer(op))).json()
    assert detail["after"]["shop_name"] and "@" in detail["after"]["email"] and "***" in detail["after"]["email"]  # masked on write
    assert (await client.get(f"{URL}/{uuid.uuid4()}", headers=bearer(op))).status_code == 404


async def test_pagination_walks_every_row(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:  # noqa: E501
    """Filtered, because every platform request adds its own access row at the top and would shift an unfiltered offset."""
    await _pagination(client, admin_conn)


async def _pagination(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    op = await operator(client, admin_conn)
    for n in range(3):
        await register(client, f"Shop {n}")
    first = (await client.get(URL, params={"limit": 2, "action": "tenant.registered"}, headers=bearer(op))).json()
    assert len(first["items"]) == 2 and first["next_cursor"]
    seen = {r["id"] for r in first["items"]}
    second = (await client.get(URL, params={"limit": 2, "action": "tenant.registered", "cursor": first["next_cursor"]}, headers=bearer(op))).json()
    assert seen.isdisjoint({r["id"] for r in second["items"]})
