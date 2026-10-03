"""Task 42: the marketing studio (PRD F-014): AI drafts, a person edits, a manager approves. Nothing is published."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.settings import settings
from app.core.tenancy import tenant_session
from tests.pg.agent_support import APPROVALS, RUNS, shop
from tests.pg.agent_support import scripted_provider as scripted_provider  # noqa: F401  (autouse fixture)
from tests.pg.conftest import bearer, member, register

pytestmark = pytest.mark.pg

POSTS = "/api/v1/marketing/posts/"
DRAFTS = "/api/v1/marketing/posts/drafts"


async def draft(client: AsyncClient, acct: dict[str, Any], **over: Any) -> Any:
    return await client.post(
        DRAFTS, json={"goal": "general", "tone": "friendly", "language": "english", **over}, headers=bearer(acct)
    )


async def test_a_draft_is_written_saved_and_recorded_in_the_activity_log(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    res = await draft(client, owner, goal="promote_product", product_id=items["shirt"]["id"], language="roman_urdu")
    assert res.status_code == 201, res.text
    post = res.json()
    assert (
        post["status"] == "draft"
        and "Classic Shirt" in post["title"]
        and "mein" in post["message"]
        and post["hashtags"].startswith("#")
    )
    assert (await client.get(f"{POSTS}{post['id']}", headers=bearer(owner))).json()["message"] == post["message"]
    runs = (await client.get(RUNS, params={"limit": 5}, headers=bearer(owner))).json()["items"]
    assert runs[0]["agent"] == "marketing" and runs[0]["outcome"] == "ok"


async def test_only_owners_and_managers_use_the_studio(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    manager = await member(client, app_engine, owner, "manager")
    staff = await member(client, app_engine, owner, "staff")
    post = (await draft(client, owner)).json()
    assert (await draft(client, manager)).status_code == 201
    for acct in (staff,):
        assert (await draft(client, acct)).status_code == 403
        assert (await client.get(POSTS, headers=bearer(acct))).status_code == 403
        assert (
            await client.patch(f"{POSTS}{post['id']}", json={"title": "x", "message": "y"}, headers=bearer(acct))
        ).status_code == 403
        assert (await client.post(f"{POSTS}{post['id']}/submit", headers=bearer(acct))).status_code == 403
        assert (await client.delete(f"{POSTS}{post['id']}", headers=bearer(acct))).status_code == 403
    assert (await client.get(POSTS)).status_code == 401


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"goal": "promote_product"}, "product"),  # a product is needed to promote one
        ({"goal": "sell_my_house"}, "goal"),
        ({"goal": "general", "tone": "rude"}, "tone"),
        ({"goal": "general", "language": "klingon"}, "language"),
        ({"goal": "announce_offer", "notes": "x" * 301}, "notes"),
    ],
)
async def test_a_brief_is_checked_field_by_field(client: AsyncClient, body: dict[str, Any], field: str) -> None:
    owner = await register(client, "Shop A")
    res = await client.post(DRAFTS, json=body, headers=bearer(owner))
    assert res.status_code == 422 and field in res.text.lower()


async def test_a_product_from_another_shop_cannot_be_promoted(client: AsyncClient) -> None:
    a, b = await register(client, "Shop A"), await register(client, "Shop B")
    items = await shop(client, a)
    res = await draft(client, b, goal="promote_product", product_id=items["shirt"]["id"])
    assert res.status_code == 404


@pytest.mark.parametrize(
    ("patch", "field"),
    [
        ({"title": "", "message": "ok"}, "title"),
        ({"title": "   ", "message": "ok"}, "title"),
        ({"title": "t" * 121, "message": "ok"}, "title"),
        ({"title": "t", "message": ""}, "message"),
        ({"title": "t", "message": "m" * 1001}, "message"),
        ({"title": "t", "message": "m", "hashtags": "#bad-tag"}, "hashtags"),
    ],
)
async def test_an_edit_is_checked_field_by_field(client: AsyncClient, patch: dict[str, Any], field: str) -> None:
    owner = await register(client, "Shop A")
    post = (await draft(client, owner)).json()
    res = await client.patch(f"{POSTS}{post['id']}", json=patch, headers=bearer(owner))
    assert res.status_code == 422 and field in res.text.lower()


async def test_editing_cleans_the_hashtags_and_only_a_draft_can_be_edited(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    post = (await draft(client, owner)).json()
    res = await client.patch(
        f"{POSTS}{post['id']}",
        json={"title": " Eid sale ", "message": "Big savings", "hashtags": "eid  #sale"},
        headers=bearer(owner),
    )
    assert res.status_code == 200 and res.json()["title"] == "Eid sale" and res.json()["hashtags"] == "#eid #sale"
    assert (await client.post(f"{POSTS}{post['id']}/submit", headers=bearer(owner))).json()[
        "status"
    ] == "pending_approval"
    again = await client.patch(f"{POSTS}{post['id']}", json={"title": "x", "message": "y"}, headers=bearer(owner))
    assert again.status_code == 409 and again.json()["code"] == "not_a_draft"
    assert (await client.post(f"{POSTS}{post['id']}/submit", headers=bearer(owner))).status_code == 409
    assert (await client.delete(f"{POSTS}{post['id']}", headers=bearer(owner))).status_code == 409


async def test_sending_for_approval_then_approving_marks_it_ready_and_posts_nothing(
    client: AsyncClient, app_engine: AsyncEngine
) -> None:
    owner = await register(client, "Shop A")
    manager = await member(client, app_engine, owner, "manager")
    post = (await draft(client, manager)).json()
    await client.post(f"{POSTS}{post['id']}/submit", headers=bearer(manager))
    waiting = (await client.get(APPROVALS, params={"status": "pending"}, headers=bearer(owner))).json()["items"]
    card = next(a for a in waiting if a["tool"] == "approve_post")
    assert (
        card["agent"] == "marketing"
        and card["summary"].startswith("Approve the post")
        and card["details"][0] == f"Title: {post['title']}"
    )
    assert card["details"][-1] == "Approving marks it ready. Nothing is posted to Facebook yet."
    done = (await client.post(f"{APPROVALS}{card['id']}/approve", headers=bearer(owner))).json()
    assert done["status"] == "executed"
    assert (await client.get(f"{POSTS}{post['id']}", headers=bearer(owner))).json()["status"] == "approved"
    assert [
        p["id"] for p in (await client.get(POSTS, params={"status": "approved"}, headers=bearer(owner))).json()["items"]
    ] == [post["id"]]


async def test_a_rejected_request_puts_the_post_back_to_a_draft(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    post = (await draft(client, owner)).json()
    await client.post(f"{POSTS}{post['id']}/submit", headers=bearer(owner))
    card = (await client.get(APPROVALS, params={"status": "pending"}, headers=bearer(owner))).json()["items"][0]
    assert (
        await client.post(f"{APPROVALS}{card['id']}/reject", json={"reason": "Wrong tone"}, headers=bearer(owner))
    ).status_code == 200
    assert (await client.get(f"{POSTS}{post['id']}", headers=bearer(owner))).json()["status"] == "draft"
    edit = await client.patch(
        f"{POSTS}{post['id']}", json={"title": "Better", "message": "Calmer words"}, headers=bearer(owner)
    )
    assert edit.status_code == 200


async def test_an_expired_request_does_not_leave_the_post_stuck(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    post = (await draft(client, owner)).json()
    await client.post(f"{POSTS}{post['id']}/submit", headers=bearer(owner))
    async with tenant_session(uuid.UUID(owner["tenant_id"])) as db:
        await db.execute(
            text("UPDATE agent_actions SET expires_at = now() - interval '1 hour' WHERE tool = 'approve_post'")
        )
    listed = (await client.get(POSTS, headers=bearer(owner))).json()["items"]
    assert [p["status"] for p in listed] == ["draft"]


async def test_removing_a_draft_hides_it_and_posts_stay_inside_their_shop(client: AsyncClient) -> None:
    a, b = await register(client, "Shop A"), await register(client, "Shop B")
    post = (await draft(client, a)).json()
    assert (await client.get(f"{POSTS}{post['id']}", headers=bearer(b))).status_code == 404
    assert (
        await client.patch(f"{POSTS}{post['id']}", json={"title": "x", "message": "y"}, headers=bearer(b))
    ).status_code == 404
    assert (await client.delete(f"{POSTS}{post['id']}", headers=bearer(b))).status_code == 404
    assert (await client.delete(f"{POSTS}{post['id']}", headers=bearer(a))).status_code == 204
    assert (await client.get(f"{POSTS}{post['id']}", headers=bearer(a))).status_code == 404  # removed means gone
    assert (await client.delete(f"{POSTS}{post['id']}", headers=bearer(a))).status_code == 404
    assert (await client.get(POSTS, headers=bearer(a))).json()["total"] == 0
    assert (await client.get(POSTS, headers=bearer(b))).json()["total"] == 0


async def test_a_paused_shop_a_used_up_allowance_and_a_provider_failure_each_say_why(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await register(client, "Shop A")
    assert (await client.put(f"{RUNS}switch", json={"enabled": False}, headers=bearer(owner))).status_code == 200
    paused = await draft(client, owner)
    assert paused.status_code == 409 and paused.json()["code"] == "agents_paused"
    await client.put(f"{RUNS}switch", json={"enabled": True}, headers=bearer(owner))

    monkeypatch.setattr(settings, "AGENT_MONTHLY_SPEND_CAP_USD", 0.0)
    assert (await draft(client, owner)).json()["code"] == "spend_limit"
    monkeypatch.setattr(settings, "AGENT_MONTHLY_SPEND_CAP_USD", 5.0)

    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    failed = await draft(client, owner)
    assert (
        failed.status_code == 502
        and failed.json()["code"] == "draft_failed"
        and "not switched on" in failed.json()["detail"]
    )
