"""Facebook comment replies (PRD W-004 step 4): comments are read once, a reply is proposed, approved, and posted once."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg
import httpx
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.services import marketing_publisher
from tests.pg.agent_support import scripted_provider  # noqa: F401  (autouse fixture: the offline writer)
from tests.pg.channel_support import FakeProviders, connect_facebook
from tests.pg.conftest import bearer, member, register
from tests.unit.provider_support import fixture_json

pytestmark = pytest.mark.pg

COMMENTS = "/api/v1/marketing/comments/"
SCHEDULE = "/api/v1/marketing/schedule"
APPROVALS = "/api/v1/approvals/"
NOW = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)


@pytest_asyncio.fixture(autouse=True)
async def clean_slate(admin_conn: asyncpg.Connection) -> None:
    """The scheduler scans every shop and the container is shared, so each test starts with none of these rows."""
    await admin_conn.execute("DELETE FROM comment_replies")
    await admin_conn.execute("DELETE FROM marketing_schedules")
    await admin_conn.execute("DELETE FROM marketing_posts")
    await admin_conn.execute("DELETE FROM agent_actions WHERE tool IN ('approve_comment_reply', 'approve_post')")


async def shop_with_published_post(client: AsyncClient, admin_conn: asyncpg.Connection, name: str = "Shop A", mode: str | None = None) -> dict[str, Any]:
    owner = await register(client, name)
    await connect_facebook(client, owner)
    if mode:
        body = {"enabled": False, "goal": "general", "posts_per_day": 1, "window_start": "10:00", "window_end": "20:00", "approval_mode": mode}
        assert (await client.put(SCHEDULE, json=body, headers=bearer(owner))).status_code == 200
    await admin_conn.execute(
        "INSERT INTO marketing_posts (id, tenant_id, title, message, hashtags, status, fb_post_id, published_at, attempts, source, created_at, updated_at) "
        "VALUES ($1, $2, 'Eid sale', 'Eid sale starts today!', '#eid', 'published', '2222222222', $3, 1, 'manual', now(), now())",
        uuid.uuid4(), uuid.UUID(owner["tenant_id"]), NOW - timedelta(hours=1),
    )
    return owner


async def replies(client: AsyncClient, owner: dict[str, Any], status: str | None = None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = (await client.get(COMMENTS, params={"status": status} if status else {}, headers=bearer(owner))).json()["items"]
    return items


async def pending(client: AsyncClient, owner: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = (await client.get(APPROVALS, params={"status": "pending"}, headers=bearer(owner))).json()["items"]
    return items


async def test_each_comment_is_stored_once_and_a_reply_is_proposed_for_approval(
    client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection
) -> None:
    owner = await shop_with_published_post(client, admin_conn)
    first = await marketing_publisher.tick(NOW)
    assert first.replies_proposed == 2 and first.replies_posted == 0
    proposed = await replies(client, owner, "proposed")
    assert {r["comment_text"] for r in proposed} == {"What is the price?", "Nice!"}
    assert all(r["post_title"] == "Eid sale" and r["reply_text"] for r in proposed)
    waiting = await pending(client, owner)
    assert len(waiting) == 2 and {w["tool"] for w in waiting} == {"approve_comment_reply"}
    assert providers.calls("fb.reply") == []  # nothing is posted before someone approves

    await marketing_publisher.tick(NOW + timedelta(minutes=30))  # the same comments again: nothing new
    assert len(await replies(client, owner)) == 2 and len(await pending(client, owner)) == 2


async def test_an_approved_reply_is_posted_once_under_its_own_comment(
    client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection
) -> None:
    owner = await shop_with_published_post(client, admin_conn)
    await marketing_publisher.tick(NOW)
    price = next(r for r in await replies(client, owner) if r["comment_text"] == "What is the price?")
    approved = await client.post(f"{APPROVALS}{price['action_id']}/approve", headers=bearer(owner))
    assert approved.status_code == 200 and approved.json()["status"] == "executed"
    assert (await replies(client, owner, "approved"))[0]["id"] == price["id"]

    result = await marketing_publisher.tick(NOW + timedelta(minutes=1))
    assert result.replies_posted == 1
    sent = providers.calls("fb.reply")
    assert len(sent) == 1 and "2222222222_3333333333" in sent[0].url.path
    posted = (await replies(client, owner, "posted"))[0]
    assert posted["id"] == price["id"] and posted["posted_at"] is not None

    await marketing_publisher.tick(NOW + timedelta(minutes=30))
    assert len(providers.calls("fb.reply")) == 1  # never twice
    audit = await admin_conn.fetch("SELECT action FROM audit_logs WHERE entity = 'comment_reply' AND entity_id = $1 ORDER BY created_at", price["id"])
    assert [a["action"] for a in audit] == ["marketing.comment_reply_proposed", "marketing.comment_reply_approved", "marketing.comment_reply_posted"]


async def test_in_auto_mode_replies_are_posted_without_asking(client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection) -> None:
    owner = await shop_with_published_post(client, admin_conn, mode="auto")
    result = await marketing_publisher.tick(NOW)
    assert result.replies_posted == 2 and len(providers.calls("fb.reply")) == 2
    assert len(await replies(client, owner, "posted")) == 2 and await pending(client, owner) == []


async def test_spam_and_the_pages_own_comments_are_not_answered(
    client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection
) -> None:
    owner = await shop_with_published_post(client, admin_conn)
    providers.on(
        "fb.comments",
        httpx.Response(
            200,
            json={
                "data": [
                    {"id": "2222222222_1", "message": "Win money at http://spam.example", "from": {"name": "Bot"}},
                    {"id": "2222222222_2", "message": "Thanks for visiting!", "from": {"name": "Ali Mart"}},  # the page itself
                    {"id": "2222222222_3", "message": "Is it in stock?", "from": {"name": "Sara"}},
                ]
            },
        ),
    )
    await marketing_publisher.tick(NOW)
    by_text = {r["comment_text"]: r["status"] for r in await replies(client, owner)}
    assert by_text == {"Win money at http://spam.example": "skipped", "Is it in stock?": "proposed"}
    assert len(await pending(client, owner)) == 1


async def test_skipping_a_proposed_reply_closes_its_approval(client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection) -> None:
    owner = await shop_with_published_post(client, admin_conn)
    await marketing_publisher.tick(NOW)
    target = (await replies(client, owner, "proposed"))[0]
    skipped = await client.post(f"{COMMENTS}{target['id']}/skip", headers=bearer(owner))
    assert skipped.status_code == 200 and skipped.json()["status"] == "skipped"
    assert target["action_id"] not in {w["id"] for w in await pending(client, owner)}
    again = await client.post(f"{COMMENTS}{target['id']}/skip", headers=bearer(owner))
    assert again.status_code == 409 and again.json()["code"] == "not_skippable"  # it is no longer proposed or approved


async def test_a_refused_token_pauses_replies_and_posts_nothing(client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection) -> None:
    owner = await shop_with_published_post(client, admin_conn)
    providers.on("fb.comments", httpx.Response(400, json=fixture_json("fb_error_190.json")))
    result = await marketing_publisher.tick(NOW)
    assert result.replies_proposed == 0 and await replies(client, owner) == []
    shown = (await client.get("/api/v1/integrations/", headers=bearer(owner))).json()[2]
    assert shown["status"] == "error" and shown["reconnect_required"] is True


async def test_roles_and_isolation(client: AsyncClient, app_engine: AsyncEngine, providers: FakeProviders, admin_conn: asyncpg.Connection) -> None:
    owner = await shop_with_published_post(client, admin_conn)
    staff = await member(client, app_engine, owner, "staff")
    other = await register(client, "Shop B")
    await marketing_publisher.tick(NOW)
    target = (await replies(client, owner))[0]
    assert (await client.get(COMMENTS, headers=bearer(staff))).status_code == 403
    assert (await client.post(f"{COMMENTS}{target['id']}/skip", headers=bearer(staff))).status_code == 403
    assert await replies(client, other) == []
    assert (await client.post(f"{COMMENTS}{target['id']}/skip", headers=bearer(other))).status_code == 404
