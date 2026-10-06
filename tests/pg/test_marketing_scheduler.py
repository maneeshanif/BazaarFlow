"""Tasks 75, 76, 84, 85 (F-015, F-016, W-004): the posting schedule, the activity list and the scheduler tick.

Times are the shop's local day (Asia/Karachi, UTC+5). With a 10:00-20:00 window and two posts a day the posts are timed at
12:30 and 17:30. The tick is called with an explicit ``now``, so nothing here waits for a clock.
"""

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

from app.core.tenancy import system_session, tenant_session
from app.services import marketing_publisher
from tests.pg.agent_support import scripted_provider  # noqa: F401  (autouse fixture: the offline writer)
from tests.pg.channel_support import PAGE_ID, PAGE_TOKEN, FakeProviders, connect_facebook
from tests.pg.conftest import bearer, member, register
from tests.unit.provider_support import fixture_json

pytestmark = pytest.mark.pg

SCHEDULE = "/api/v1/marketing/schedule"
ACTIVITY = "/api/v1/marketing/activity"
KARACHI = timezone(timedelta(hours=5))


def local(hour: int, minute: int = 0, day: int = 7) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=KARACHI).astimezone(timezone.utc)


@pytest_asyncio.fixture(autouse=True)
async def clean_slate(admin_conn: asyncpg.Connection) -> None:
    """The scheduler scans every shop, and the container is shared, so each test starts with no posts or schedules."""
    await admin_conn.execute("DELETE FROM marketing_schedules")
    await admin_conn.execute("DELETE FROM marketing_posts")
    await admin_conn.execute("DELETE FROM agent_actions WHERE tool = 'approve_post'")


def plan(**over: Any) -> dict[str, Any]:
    return {"enabled": True, "goal": "general", "posts_per_day": 2, "window_start": "10:00", "window_end": "20:00", "approval_mode": "auto", **over}


async def ready_shop(client: AsyncClient, name: str = "Shop A", **over: Any) -> dict[str, Any]:
    owner = await register(client, name)
    await connect_facebook(client, owner)
    res = await client.put(SCHEDULE, json=plan(**over), headers=bearer(owner))
    assert res.status_code == 200, res.text
    return owner


async def posts(client: AsyncClient, owner: dict[str, Any], status: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = (await client.get(ACTIVITY, params={"status": status} if status else {}, headers=bearer(owner))).json()["items"]
    return out


# -- F-015 the schedule ------------------------------------------------------------------------------------------


async def test_the_schedule_starts_unconfigured_and_is_saved_with_the_owners_choices(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    blank = (await client.get(SCHEDULE, headers=bearer(owner))).json()
    assert (blank["configured"], blank["enabled"], blank["facebook_connected"]) == (False, False, False)
    await connect_facebook(client, owner)
    saved = (await client.put(SCHEDULE, json=plan(tone="festive", language="roman_urdu", notes="Eid sale", approval_mode="manual"), headers=bearer(owner))).json()
    assert (saved["configured"], saved["enabled"], saved["posts_per_day"], saved["tone"], saved["approval_mode"]) == (True, True, 2, "festive", "manual")
    assert (saved["window_start"], saved["window_end"], saved["notes"], saved["facebook_connected"]) == ("10:00:00", "20:00:00", "Eid sale", True)
    assert (await client.get(SCHEDULE, headers=bearer(owner))).json()["language"] == "roman_urdu"


@pytest.mark.parametrize(
    ("over", "field"),
    [
        ({"posts_per_day": 0}, "posts_per_day"),
        ({"posts_per_day": 6}, "posts_per_day"),
        ({"window_start": "20:00", "window_end": "10:00"}, "request"),
        ({"window_start": "10:00", "window_end": "10:00"}, "request"),
        ({"goal": "promote_product"}, "goal"),
        ({"tone": "angry"}, "tone"),
        ({"approval_mode": "yolo"}, "approval_mode"),
        ({"notes": "n" * 301}, "notes"),
        ({"window_start": "late"}, "window_start"),
        ({"surprise": 1}, "surprise"),
    ],
)
async def test_each_schedule_rule_is_enforced(client: AsyncClient, providers: FakeProviders, over: dict[str, Any], field: str) -> None:
    owner = await register(client, "Shop A")
    await connect_facebook(client, owner)
    res = await client.put(SCHEDULE, json=plan(**over), headers=bearer(owner))
    assert res.status_code == 422 and res.json()["code"] == "validation_failed"
    assert field in {e["field"] for e in res.json()["errors"]}


async def test_a_schedule_cannot_be_switched_on_without_facebook(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    res = await client.put(SCHEDULE, json=plan(), headers=bearer(owner))
    assert res.status_code == 409 and res.json()["code"] == "facebook_not_connected"
    assert (await client.put(SCHEDULE, json=plan(enabled=False), headers=bearer(owner))).status_code == 200  # saving it off is fine


async def test_managers_can_edit_the_schedule_and_staff_cannot_open_marketing(client: AsyncClient, app_engine: AsyncEngine, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    await connect_facebook(client, owner)
    manager = await member(client, app_engine, owner, "manager")
    staff = await member(client, app_engine, owner, "staff")
    assert (await client.put(SCHEDULE, json=plan(), headers=bearer(manager))).status_code == 200
    for url in (SCHEDULE, ACTIVITY):
        assert (await client.get(url, headers=bearer(staff))).status_code == 403
        assert (await client.get(url)).status_code == 401
    assert (await client.put(SCHEDULE, json=plan(), headers=bearer(staff))).status_code == 403


# -- the scheduler -----------------------------------------------------------------------------------------------


async def test_the_tick_drafts_the_days_posts_across_the_window_and_publishes_each_when_due(
    client: AsyncClient, providers: FakeProviders
) -> None:
    owner = await ready_shop(client)
    first = await marketing_publisher.tick(local(11, 0))
    assert (first.generated, first.published) == (2, 0)
    queued = await posts(client, owner, "queued")
    assert len(queued) == 2 and all(p["source"] == "schedule" for p in queued)
    when = sorted(datetime.fromisoformat(p["scheduled_for"]).astimezone(KARACHI) for p in queued)
    assert [(w.hour, w.minute) for w in when] == [(12, 30), (17, 30)]
    assert providers.calls("fb.feed") == [] and providers.calls("fb.photos") == []  # not due yet
    assert providers.calls("pexels.search")  # but the pictures were looked up

    at_1231 = await marketing_publisher.tick(local(12, 31))
    assert (at_1231.generated, at_1231.published) == (0, 1)
    assert len(await posts(client, owner, "published")) == 1 and len(await posts(client, owner, "queued")) == 1
    at_1731 = await marketing_publisher.tick(local(17, 31))
    assert at_1731.published == 1
    done = await posts(client, owner, "published")
    assert len(done) == 2 and all(p["published_at"] and p["attempts"] == 1 and p["last_error"] is None for p in done)

    again = await marketing_publisher.tick(local(19, 0))  # the same day: nothing new, nothing posted twice
    assert (again.generated, again.published) == (0, 0)
    assert len(await posts(client, owner)) == 2


async def test_a_post_is_published_with_its_picture_when_it_has_one(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await ready_shop(client, posts_per_day=1)
    await marketing_publisher.tick(local(11, 0))
    assert (await marketing_publisher.tick(local(15, 5))).published == 1
    sent = providers.calls("fb.photos")
    assert len(sent) == 1 and b"pexels-photo-2379004.jpeg" in sent[0].content  # image_url came from Pexels
    assert providers.calls("fb.feed") == []
    assert len(await posts(client, owner, "published")) == 1


async def test_without_a_pexels_key_the_post_goes_out_as_text(client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import settings

    monkeypatch.setattr(settings, "PEXELS_API_KEY", "")
    owner = await ready_shop(client, posts_per_day=1)
    await marketing_publisher.tick(local(11, 0))
    await marketing_publisher.tick(local(15, 5))
    assert len(providers.calls("fb.feed")) == 1 and providers.calls("fb.photos") == []
    assert len(await posts(client, owner, "published")) == 1


async def test_nothing_is_drafted_before_the_window_after_it_when_off_or_without_facebook(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await ready_shop(client)
    assert (await marketing_publisher.tick(local(8, 0))).generated == 0  # window not open yet
    assert (await marketing_publisher.tick(local(21, 0))).generated == 0  # window already closed
    await client.put(SCHEDULE, json=plan(enabled=False), headers=bearer(owner))
    assert (await marketing_publisher.tick(local(11, 0))).generated == 0
    await client.put(SCHEDULE, json=plan(), headers=bearer(owner))
    await client.delete("/api/v1/integrations/facebook", headers=bearer(owner))
    assert (await marketing_publisher.tick(local(11, 0))).generated == 0
    assert await posts(client, owner) == []


async def test_in_manual_mode_posts_wait_for_approval_and_go_to_the_queue_when_approved(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await ready_shop(client, approval_mode="manual", posts_per_day=1)
    assert (await marketing_publisher.tick(local(11, 0))).generated == 1
    pending = await posts(client, owner, "pending_approval")
    assert len(pending) == 1 and (await marketing_publisher.tick(local(15, 5))).published == 0  # not approved: never published
    actions = (await client.get("/api/v1/approvals/", params={"status": "pending"}, headers=bearer(owner))).json()["items"]
    assert len(actions) == 1 and actions[0]["tool"] == "approve_post"
    approved = await client.post(f"/api/v1/approvals/{actions[0]['id']}/approve", headers=bearer(owner))
    assert approved.status_code == 200, approved.text
    assert len(await posts(client, owner, "queued")) == 1  # a scheduled post goes straight to the queue
    assert (await marketing_publisher.tick(local(15, 6))).published == 1


async def test_a_failing_provider_is_retried_later_then_marked_failed_with_a_reason_and_can_be_retried(
    client: AsyncClient, providers: FakeProviders
) -> None:
    owner = await ready_shop(client, posts_per_day=1)
    await marketing_publisher.tick(local(11, 0))
    providers.on("fb.feed", httpx.ReadTimeout("slow"))
    providers.on("fb.photos", httpx.ReadTimeout("slow"))
    t1 = await marketing_publisher.tick(local(15, 5))
    assert (t1.published, t1.retried) == (0, 1)
    post = (await posts(client, owner, "queued"))[0]
    assert post["attempts"] == 1 and "not answering" in post["last_error"]
    assert datetime.fromisoformat(post["scheduled_for"]) == local(15, 5) + timedelta(minutes=5)

    assert (await marketing_publisher.tick(local(15, 6))).retried == 0  # not due again yet
    assert (await marketing_publisher.tick(local(15, 11))).retried == 1  # +5 minutes: second failure, next try +15
    t3 = await marketing_publisher.tick(local(15, 30))
    assert t3.failed == 1
    failed = (await posts(client, owner, "failed"))[0]
    assert failed["attempts"] == 3 and failed["last_error"]
    shown = (await client.get("/api/v1/integrations/", headers=bearer(owner))).json()[2]
    assert shown["status"] == "connected" and shown["last_error"]  # degraded, still connected

    providers.on("fb.feed")  # the provider recovers
    providers.on("fb.photos")
    again = await client.post(f"{ACTIVITY}/{failed['id']}/retry", headers=bearer(owner))
    assert again.status_code == 200 and again.json()["status"] == "queued" and again.json()["attempts"] == 0
    assert (await marketing_publisher.tick(local(15, 40))).published == 1


async def test_a_refused_token_pauses_publishing_until_the_owner_reconnects(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await ready_shop(client, posts_per_day=1)
    await marketing_publisher.tick(local(11, 0))
    expired = httpx.Response(400, json=fixture_json("fb_error_190.json"))
    providers.on("fb.feed", expired)
    providers.on("fb.photos", expired)
    paused = await marketing_publisher.tick(local(15, 5))
    assert (paused.published, paused.paused) == (0, 1)
    shown = (await client.get("/api/v1/integrations/", headers=bearer(owner))).json()[2]
    assert shown["status"] == "error" and shown["reconnect_required"] is True
    calls = len(providers.requests)
    again = await marketing_publisher.tick(local(15, 30))
    assert again.paused == 1 and len(providers.requests) == calls  # nothing is called while the token is refused
    assert len(await posts(client, owner, "queued")) == 1

    providers.on("fb.feed")
    providers.on("fb.photos")
    reconnect = await client.put(
        "/api/v1/integrations/facebook", json={"credentials": {"page_id": PAGE_ID, "access_token": PAGE_TOKEN}}, headers=bearer(owner)
    )
    assert reconnect.status_code == 200
    assert (await marketing_publisher.tick(local(15, 40))).published == 1


async def test_a_post_that_already_has_its_facebook_id_is_never_published_twice(client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection) -> None:
    owner = await ready_shop(client, posts_per_day=1)
    await marketing_publisher.tick(local(11, 0))
    await admin_conn.execute("UPDATE marketing_posts SET fb_post_id = 'already_there' WHERE tenant_id = $1", uuid.UUID(owner["tenant_id"]))
    result = await marketing_publisher.tick(local(15, 5))
    assert result.published == 0 and providers.calls("fb.feed") == [] and providers.calls("fb.photos") == []
    assert len(await posts(client, owner, "published")) == 1


async def test_a_day_that_could_not_be_finished_resumes_instead_of_duplicating(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await ready_shop(client, posts_per_day=3)
    assert (await client.put("/api/v1/agent-runs/switch", json={"enabled": False}, headers=bearer(owner))).status_code == 200
    assert (await marketing_publisher.tick(local(11, 0))).generated == 0  # the AI is off: nothing drafted, nothing spent
    await client.put("/api/v1/agent-runs/switch", json={"enabled": True}, headers=bearer(owner))
    assert (await marketing_publisher.tick(local(11, 5))).generated == 3
    assert len(await posts(client, owner)) == 3


# -- F-016 the activity list and its actions ---------------------------------------------------------------------


async def _approved_post(admin: asyncpg.Connection, owner: dict[str, Any]) -> str:
    post_id = uuid.uuid4()
    await admin.execute(
        "INSERT INTO marketing_posts (id, tenant_id, title, message, hashtags, status, attempts, source, created_at, updated_at) "
        "VALUES ($1, $2, 'Sale', 'Big sale today', '#sale', 'approved', 0, 'manual', now(), now())",
        post_id,
        uuid.UUID(owner["tenant_id"]),
    )
    return str(post_id)


async def test_an_approved_post_can_be_queued_for_later_and_cancelled(client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection) -> None:
    owner = await register(client, "Shop A")
    await connect_facebook(client, owner)
    post_id = await _approved_post(admin_conn, owner)
    when = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    queued = await client.post(f"{ACTIVITY}/{post_id}/queue", json={"scheduled_for": when}, headers=bearer(owner))
    assert queued.status_code == 200 and queued.json()["status"] == "queued"
    assert (await client.get(SCHEDULE, headers=bearer(owner))).json()["next_post_at"] is not None
    assert (await client.post(f"{ACTIVITY}/{post_id}/queue", json={"scheduled_for": when}, headers=bearer(owner))).json()["code"] == "not_approved"
    cancelled = await client.post(f"{ACTIVITY}/{post_id}/cancel", headers=bearer(owner))
    assert cancelled.json()["status"] == "cancelled"
    assert (await client.post(f"{ACTIVITY}/{post_id}/cancel", headers=bearer(owner))).json()["code"] == "not_cancellable"
    assert (await client.post(f"{ACTIVITY}/{post_id}/retry", headers=bearer(owner))).json()["code"] == "not_failed"


async def test_a_time_in_the_past_or_no_facebook_blocks_queueing(client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection) -> None:
    owner = await register(client, "Shop A")
    post_id = await _approved_post(admin_conn, owner)
    soon = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    assert (await client.post(f"{ACTIVITY}/{post_id}/queue", json={"scheduled_for": soon}, headers=bearer(owner))).json()["code"] == "facebook_not_connected"
    await connect_facebook(client, owner)
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert (await client.post(f"{ACTIVITY}/{post_id}/queue", json={"scheduled_for": past}, headers=bearer(owner))).json()["code"] == "time_in_the_past"
    assert (await client.post(f"{ACTIVITY}/{post_id}/queue", json={"scheduled_for": "not a time"}, headers=bearer(owner))).status_code == 422


async def test_the_activity_list_filters_by_status_and_is_private_to_the_shop(
    client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection
) -> None:
    a = await ready_shop(client, "Shop A", posts_per_day=1)
    b = await register(client, "Shop B")
    await marketing_publisher.tick(local(11, 0))
    await _approved_post(admin_conn, a)
    assert {p["status"] for p in await posts(client, a)} == {"queued", "approved"}
    assert len(await posts(client, a, "approved")) == 1
    assert (await client.get(ACTIVITY, params={"status": "draft"}, headers=bearer(a))).status_code == 422  # drafts live in the studio
    assert await posts(client, b) == []
    post_id = (await posts(client, a))[0]["id"]
    assert (await client.post(f"{ACTIVITY}/{post_id}/cancel", headers=bearer(b))).status_code == 404


async def test_the_scan_sees_which_shops_have_work_but_nothing_else(client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection) -> None:
    from sqlalchemy import text

    owner = await ready_shop(client, posts_per_day=1)
    await marketing_publisher.tick(local(11, 0))
    async with system_session() as db:
        assert (await db.execute(text("SELECT count(*) FROM marketing_posts"))).scalar_one() == 1
        assert (await db.execute(text("SELECT count(*) FROM marketing_schedules"))).scalar_one() == 1
        for table in ("customers", "products", "orders", "payments", "messages", "tenant_integrations", "agent_actions"):
            assert (await db.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one() == 0, f"{table} must stay closed"
    async with tenant_session(uuid.UUID(owner["tenant_id"])) as db:  # while a normal session is unaffected by the flag
        assert (await db.execute(text("SELECT current_setting('app.system_job', true)"))).scalar_one() in (None, "")
