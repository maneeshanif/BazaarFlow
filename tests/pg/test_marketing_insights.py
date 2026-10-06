"""Task 86 (F-017): marketing insights checked against a hand-computed set of posts.

Dataset (one shop): published today x2 (one written by the schedule), published 3 days ago x1, published 10 days ago x1,
failed today x1, queued x2. In the 7-day range: published 3 (previous window 1), failed 1, success 75%, 1 from the schedule.
In the 30-day range: published 4 (previous 0). Comments come from the recorded Facebook response (2 per post).
"""

from __future__ import annotations

import uuid
from typing import Any

import asyncpg
import httpx
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.pg.channel_support import FakeProviders, connect_facebook
from tests.pg.conftest import bearer, member, register

pytestmark = pytest.mark.pg

URL = "/api/v1/marketing/insights"


@pytest_asyncio.fixture(autouse=True)
async def clean_slate(admin_conn: asyncpg.Connection) -> None:
    await admin_conn.execute("DELETE FROM marketing_posts")


async def _post(admin: asyncpg.Connection, owner: dict[str, Any], status: str, days_ago: float, source: str = "manual", fb: bool = True) -> None:
    published = status == "published"
    await admin.execute(
        "INSERT INTO marketing_posts (id, tenant_id, title, message, hashtags, status, fb_post_id, published_at, attempts, source, created_at, updated_at) "
        "VALUES ($1, $2, 'Post', 'text', '#a', $3, $4, CASE WHEN $5 THEN now() - make_interval(secs => $6) END, 1, $7, "
        "now() - make_interval(secs => $6), now() - make_interval(secs => $6))",
        uuid.uuid4(),
        uuid.UUID(owner["tenant_id"]),
        status,
        f"1234567890_{uuid.uuid4().hex[:8]}" if (published and fb) else None,
        published,
        days_ago * 86400,
        source,
    )


async def seeded(client: AsyncClient, admin: asyncpg.Connection, with_facebook: bool = True) -> dict[str, Any]:
    owner = await register(client, "Shop A")
    if with_facebook:
        await connect_facebook(client, owner)
    await _post(admin, owner, "published", 0.01, "schedule")
    await _post(admin, owner, "published", 0.02)
    await _post(admin, owner, "published", 3)
    await _post(admin, owner, "published", 10)
    await _post(admin, owner, "failed", 0.01)
    await _post(admin, owner, "queued", -1)
    await _post(admin, owner, "queued", -2)
    return owner


async def test_every_figure_matches_the_hand_computed_value(client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection) -> None:
    owner = await seeded(client, admin_conn)
    week = (await client.get(URL, params={"range": "7d"}, headers=bearer(owner))).json()
    assert (week["published"]["value"], week["published"]["previous"], week["published"]["change_percent"]) == (3, 1, 200)
    assert (week["failed"], week["queued"], week["success_percent"], week["from_schedule"]) == (1, 2, 75, 1)
    assert len(week["trend"]) == 7 and sum(d["published"] for d in week["trend"]) == 3
    assert week["is_empty"] is False
    month = (await client.get(URL, params={"range": "30d"}, headers=bearer(owner))).json()
    assert (month["published"]["value"], month["published"]["previous"], month["success_percent"]) == (4, 0, 80)
    assert len(month["trend"]) == 30 and sum(d["published"] for d in month["trend"]) == 4


async def test_the_latest_posts_carry_their_comment_counts_from_facebook(client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection) -> None:
    owner = await seeded(client, admin_conn)
    body = (await client.get(URL, headers=bearer(owner))).json()
    assert body["engagement"] == "available" and body["engagement_note"] is None
    assert len(body["top_posts"]) == 4 and all(p["comments"] == 2 for p in body["top_posts"])
    published = [p["published_at"] for p in body["top_posts"]]
    assert published == sorted(published, reverse=True)
    assert len(providers.calls("fb.comments")) == 4


async def test_when_facebook_is_down_the_counts_still_show_and_engagement_says_why(client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection) -> None:
    owner = await seeded(client, admin_conn)
    providers.on("fb.comments", httpx.ReadTimeout("slow"))
    body = (await client.get(URL, params={"range": "7d"}, headers=bearer(owner))).json()
    assert body["published"]["value"] == 3 and body["engagement"] == "unavailable" and "did not answer" in body["engagement_note"]
    assert all(p["comments"] is None for p in body["top_posts"])


async def test_without_facebook_the_counts_show_and_engagement_is_not_connected(client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection) -> None:
    owner = await seeded(client, admin_conn, with_facebook=False)
    body = (await client.get(URL, headers=bearer(owner))).json()
    assert body["engagement"] == "not_connected" and "not connected" in body["engagement_note"] and body["published"]["value"] == 4
    assert providers.calls("fb.comments") == []


async def test_a_shop_with_no_posts_gets_an_empty_state_not_an_error(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    res = await client.get(URL, headers=bearer(owner))
    assert res.status_code == 200
    body = res.json()
    assert body["is_empty"] is True and body["success_percent"] is None and body["top_posts"] == []
    assert (body["published"]["value"], body["failed"], body["queued"]) == (0, 0, 0)


async def test_roles_and_isolation(client: AsyncClient, app_engine: AsyncEngine, providers: FakeProviders, admin_conn: asyncpg.Connection) -> None:
    owner = await seeded(client, admin_conn)
    other = await register(client, "Shop B")
    manager = await member(client, app_engine, owner, "manager")
    staff = await member(client, app_engine, owner, "staff")
    assert (await client.get(URL, headers=bearer(manager))).status_code == 200
    assert (await client.get(URL, headers=bearer(staff))).status_code == 403
    assert (await client.get(URL)).status_code == 401
    assert (await client.get(URL, headers=bearer(other))).json()["is_empty"] is True
    assert (await client.get(URL, params={"range": "yesterday"}, headers=bearer(owner))).status_code == 422
