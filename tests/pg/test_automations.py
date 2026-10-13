"""Task 88 (F-024, W-008): the six launch recipes, their toggles, history and failure handling, on Postgres."""

from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg
import httpx
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.services import automation_service
from app.services.automation_recipes import RECIPES, Outcome, RecipeError
from tests.pg.agent_support import scripted_provider  # noqa: F401  (autouse fixture: the offline writer)
from tests.pg.channel_support import FakeProviders, connect_twilio
from tests.pg.conftest import bearer, member, register
from tests.pg.test_sales_api import SALES, customer, product, sale

pytestmark = pytest.mark.pg

URL = "/api/v1/automations/"
KARACHI = timezone(timedelta(hours=5))


def local(hour: int, minute: int = 0, day: int = 7) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=KARACHI).astimezone(timezone.utc)


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(automation_service, "RETRY_DELAY_SECONDS", 0)


@pytest_asyncio.fixture(autouse=True)
async def clean_slate(admin_conn: asyncpg.Connection) -> None:
    await admin_conn.execute("DELETE FROM automations")
    await admin_conn.execute("DELETE FROM marketing_posts")
    await admin_conn.execute("DELETE FROM agent_actions WHERE tool IN ('send_whatsapp_message', 'approve_post')")


async def enable(client: AsyncClient, owner: dict[str, Any], key: str) -> dict[str, Any]:
    res = await client.post(f"{URL}{key}/toggle", json={"enabled": True}, headers=bearer(owner))
    assert res.status_code == 200, res.text
    body: dict[str, Any] = res.json()
    return body


async def run(client: AsyncClient, owner: dict[str, Any], key: str) -> dict[str, Any]:
    res = await client.post(f"{URL}{key}/run", headers=bearer(owner))
    assert res.status_code == 200, res.text
    body: dict[str, Any] = res.json()
    return body


async def pending(client: AsyncClient, owner: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = (await client.get("/api/v1/approvals/", params={"status": "pending"}, headers=bearer(owner))).json()["items"]
    return items


# -- the catalogue and its toggles -------------------------------------------------------------------------------


async def test_the_owner_sees_the_six_recipes_all_off(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    rows = (await client.get(URL, headers=bearer(owner))).json()
    assert [r["key"] for r in rows] == [
        "low_stock_vendor_draft",
        "new_order_confirmation",
        "daily_brief",
        "weekly_slow_stock_post",
        "overdue_udhaar_reminder",
        "unanswered_message_alert",
    ]
    assert all(r["enabled"] is False and r["last_run"] is None and r["needs_attention"] is False for r in rows)
    assert {r["key"] for r in rows if not r["requirements_met"]} == {"new_order_confirmation", "daily_brief", "unanswered_message_alert"}


async def test_roles(client: AsyncClient, app_engine: AsyncEngine, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    manager = await member(client, app_engine, owner, "manager")
    staff = await member(client, app_engine, owner, "staff")
    assert (await client.get(URL, headers=bearer(manager))).status_code == 200
    assert (await client.post(f"{URL}low_stock_vendor_draft/toggle", json={"enabled": True}, headers=bearer(manager))).status_code == 200
    for url in (URL, f"{URL}runs"):
        assert (await client.get(url, headers=bearer(staff))).status_code == 403
        assert (await client.get(url)).status_code == 401
    assert (await client.post(f"{URL}low_stock_vendor_draft/run", headers=bearer(staff))).status_code == 403


async def test_toggle_rules(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    assert (await client.post(f"{URL}nope/toggle", json={"enabled": True}, headers=bearer(owner))).status_code == 404
    assert (await client.post(f"{URL}daily_brief/toggle", json={"enabled": "maybe"}, headers=bearer(owner))).status_code == 422
    assert (await client.post(f"{URL}daily_brief/toggle", json={"enabled": True, "x": 1}, headers=bearer(owner))).status_code == 422
    blocked = await client.post(f"{URL}daily_brief/toggle", json={"enabled": True}, headers=bearer(owner))
    assert blocked.status_code == 409 and blocked.json()["code"] == "integration_required"
    await connect_twilio(client, owner)
    assert (await enable(client, owner, "daily_brief"))["enabled"] is True
    off = await client.post(f"{URL}daily_brief/toggle", json={"enabled": False}, headers=bearer(owner))
    assert off.json()["enabled"] is False
    assert (await client.post(f"{URL}daily_brief/run", headers=bearer(owner))).json()["code"] == "not_enabled"


# -- 1 low stock -> a drafted vendor message ---------------------------------------------------------------------


async def test_low_stock_drafts_one_vendor_message_for_approval_and_sending_it_needs_the_owner(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    vendor = (await client.post("/api/v1/vendors/", json={"name": "Cloth House", "phone": "+923009998888"}, headers=bearer(owner))).json()
    await product(client, owner, "SHIRT", "1000.00", 2, name="Classic Shirt", reorder_level=5, vendor_id=vendor["id"])
    await product(client, owner, "CAP", "500.00", 1, name="Cap", reorder_level=3, vendor_id=vendor["id"])
    await product(client, owner, "ROPE", "50.00", 0, name="Rope", reorder_level=2)  # low, but no vendor
    await enable(client, owner, "low_stock_vendor_draft")

    first = await run(client, owner, "low_stock_vendor_draft")
    assert first["status"] == "succeeded" and "1 vendor message" in first["summary"] and "1 low item" in first["summary"]
    waiting = await pending(client, owner)
    assert len(waiting) == 1 and waiting[0]["tool"] == "send_whatsapp_message" and "Cloth House" in waiting[0]["summary"]
    assert providers.calls("twilio.send") == []  # nothing is sent until someone approves
    await run(client, owner, "low_stock_vendor_draft")
    assert len(await pending(client, owner)) == 1  # the same draft is not filed twice

    approved = await client.post(f"/api/v1/approvals/{waiting[0]['id']}/approve", headers=bearer(owner))
    assert approved.status_code == 200, approved.text
    sent = providers.calls("twilio.send")
    assert len(sent) == 1 and b"923009998888" in sent[0].content and b"Classic+Shirt" in sent[0].content


async def test_nothing_low_means_a_manual_run_says_so(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    await enable(client, owner, "low_stock_vendor_draft")
    done = await run(client, owner, "low_stock_vendor_draft")
    assert done["status"] == "succeeded" and "Nothing is low" in done["summary"]


# -- 2 new order -> confirmation ----------------------------------------------------------------------------------


async def test_a_new_order_for_a_customer_is_confirmed_once_and_old_orders_are_left_alone(
    client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection
) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    shirt = await product(client, owner, "SHIRT", "1000.00", 50, name="Classic Shirt")
    ali = await customer(client, owner, "+923001110001")
    old = await client.post(SALES, json=sale([(shirt, 1)], customer_id=ali["id"]), headers=bearer(owner))
    await admin_conn.execute("UPDATE orders SET created_at = now() - interval '3 days' WHERE id = $1", uuid.UUID(old.json()["id"]))
    await enable(client, owner, "new_order_confirmation")
    assert (await client.post(SALES, json=sale([(shirt, 2)], customer_id=ali["id"]), headers=bearer(owner))).status_code == 201
    assert (await client.post(SALES, json=sale([(shirt, 1)]), headers=bearer(owner))).status_code == 201  # a walk-in has no phone

    first = await run(client, owner, "new_order_confirmation")
    assert first["status"] == "succeeded" and "1 order confirmation" in first["summary"]
    sent = providers.calls("twilio.send")
    assert len(sent) == 1 and b"923001110001" in sent[0].content and b"Rs+2%2C000" in sent[0].content
    again = await run(client, owner, "new_order_confirmation")
    assert "0 order confirmation" in again["summary"] and len(providers.calls("twilio.send")) == 1  # never twice


# -- 3 daily brief ------------------------------------------------------------------------------------------------


async def test_the_daily_brief_goes_to_the_owner_once_after_nine(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    await enable(client, owner, "daily_brief")
    await automation_service.tick(local(8, 30, day=20))
    assert providers.calls("twilio.send") == []  # too early
    await automation_service.tick(local(9, 5, day=20))
    sent = providers.calls("twilio.send")
    assert len(sent) == 1 and b"923001234567" in sent[0].content and b"business+brief" in sent[0].content
    await automation_service.tick(local(9, 40, day=20))
    await automation_service.tick(local(15, 0, day=20))
    assert len(providers.calls("twilio.send")) == 1  # once a day
    await automation_service.tick(local(9, 5, day=21))
    assert len(providers.calls("twilio.send")) == 2  # and again the next morning
    runs = (await client.get(f"{URL}runs", params={"automation": "daily_brief"}, headers=bearer(owner))).json()
    assert runs["total"] == 2 and all(r["trigger_source"] == "schedule" and r["status"] == "succeeded" for r in runs["items"])


# -- 4 weekly post from slow-moving stock -------------------------------------------------------------------------


async def test_on_monday_morning_a_post_about_a_slow_product_is_drafted_for_approval_once_a_week(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    await product(client, owner, "SLOW", "900.00", 20, name="Winter Shawl")
    sold = await product(client, owner, "FAST", "100.00", 20, name="Fast Cap")
    assert (await client.post(SALES, json=sale([(sold, 1)]), headers=bearer(owner))).status_code == 201
    await enable(client, owner, "weekly_slow_stock_post")
    await automation_service.tick(local(10, 30, day=6))  # a Tuesday
    assert await pending(client, owner) == []
    await automation_service.tick(local(9, 0, day=5))  # Monday, before ten
    assert await pending(client, owner) == []
    await automation_service.tick(local(10, 30, day=5))
    waiting = await pending(client, owner)
    assert len(waiting) == 1 and waiting[0]["tool"] == "approve_post" and "Winter Shawl" in waiting[0]["summary"]
    await automation_service.tick(local(11, 30, day=5))
    assert len(await pending(client, owner)) == 1  # one draft a week
    activity = (await client.get("/api/v1/marketing/activity", params={"status": "pending_approval"}, headers=bearer(owner))).json()
    assert activity["total"] == 1  # it also shows in the marketing activity list, waiting for approval


# -- 5 overdue udhaar -> reminder draft ---------------------------------------------------------------------------


async def test_an_overdue_customer_gets_one_reminder_draft_and_not_another_within_a_week(
    client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection
) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    shirt = await product(client, owner, "SHIRT", "1000.00", 50, name="Classic Shirt")
    ali = await customer(client, owner, "+923001110001")
    fresh = (await client.post("/api/v1/customers/", json={"phone": "+923001110002", "name": "Bina"}, headers=bearer(owner))).json()
    old = await client.post(SALES, json=sale([(shirt, 2)], payment_method="udhaar", customer_id=ali["id"]), headers=bearer(owner))
    await client.post(SALES, json=sale([(shirt, 1)], payment_method="udhaar", customer_id=fresh["id"]), headers=bearer(owner))
    await admin_conn.execute("UPDATE ledger_entries SET created_at = now() - interval '20 days' WHERE ref_id = $1", uuid.UUID(old.json()["id"]))
    await enable(client, owner, "overdue_udhaar_reminder")

    first = await run(client, owner, "overdue_udhaar_reminder")
    assert "1 payment reminder" in first["summary"]
    waiting = await pending(client, owner)
    assert len(waiting) == 1 and "Ali" in waiting[0]["summary"] and "Rs 2,000" in waiting[0]["summary"]  # only the 20-day-old credit
    assert providers.calls("twilio.send") == []
    await run(client, owner, "overdue_udhaar_reminder")
    assert len(await pending(client, owner)) == 1

    rejected = await client.post(f"/api/v1/approvals/{waiting[0]['id']}/reject", json={"reason": "I will call him"}, headers=bearer(owner))
    assert rejected.status_code == 200
    await run(client, owner, "overdue_udhaar_reminder")
    assert await pending(client, owner) == []  # asked and answered this week: no second reminder


async def test_a_customer_who_paid_is_not_reminded(client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection) -> None:
    owner = await register(client, "Shop A")
    shirt = await product(client, owner, "SHIRT", "1000.00", 50, name="Classic Shirt")
    ali = await customer(client, owner, "+923001110001")
    old = await client.post(SALES, json=sale([(shirt, 1)], payment_method="udhaar", customer_id=ali["id"]), headers=bearer(owner))
    await admin_conn.execute("UPDATE ledger_entries SET created_at = now() - interval '20 days' WHERE ref_id = $1", uuid.UUID(old.json()["id"]))
    await client.post(f"/api/v1/customers/{ali['id']}/payments", json={"amount": "1000.00", "method": "cash"}, headers=bearer(owner))
    await enable(client, owner, "overdue_udhaar_reminder")
    assert "Nobody is overdue" in (await run(client, owner, "overdue_udhaar_reminder"))["summary"]


# -- 6 unanswered message -> alert -------------------------------------------------------------------------------


async def _waiting_conversation(admin: asyncpg.Connection, owner: dict[str, Any], minutes: int, inbound: bool = True) -> None:
    tenant = uuid.UUID(owner["tenant_id"])
    conversation = uuid.uuid4()
    await admin.execute(
        "INSERT INTO conversations (id, tenant_id, channel, phone, contact_name, status, mode, last_message_at, created_at, updated_at) "
        "VALUES ($1, $2, 'whatsapp', '+923005550001', 'Sara', 'needs_human', 'human', now() - make_interval(mins => $3), now(), now())",
        conversation, tenant, minutes,
    )
    await admin.execute(
        "INSERT INTO messages (id, tenant_id, conversation_id, phone, direction, text, status, sender, created_at, updated_at) "
        "VALUES (gen_random_uuid(), $1, $2, '+923005550001', $3::messagedirection, 'hello?', 'received', 'customer', now() - make_interval(mins => $4), now())",
        tenant, conversation, "inbound" if inbound else "outbound", minutes,
    )


async def test_a_message_waiting_over_fifteen_minutes_alerts_the_owner_once(client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    await _waiting_conversation(admin_conn, owner, 20)
    await enable(client, owner, "unanswered_message_alert")
    first = await run(client, owner, "unanswered_message_alert")
    assert "1 waiting message" in first["summary"]
    sent = providers.calls("twilio.send")
    assert len(sent) == 1 and b"923001234567" in sent[0].content and b"Sara" in sent[0].content
    await run(client, owner, "unanswered_message_alert")
    assert len(providers.calls("twilio.send")) == 1  # the same waiting message is only reported once


async def test_a_recent_or_already_answered_conversation_does_not_alert(client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    await _waiting_conversation(admin_conn, owner, 5)
    await enable(client, owner, "unanswered_message_alert")
    assert "No customer is waiting" in (await run(client, owner, "unanswered_message_alert"))["summary"]
    other = await register(client, "Shop B")
    await connect_twilio(client, other, "AC" + "d" * 32)
    await _waiting_conversation(admin_conn, other, 30, inbound=False)  # the last message is ours
    await enable(client, other, "unanswered_message_alert")
    assert "No customer is waiting" in (await run(client, other, "unanswered_message_alert"))["summary"]


# -- failure handling and history ---------------------------------------------------------------------------------


async def test_failures_are_recorded_counted_and_raise_an_alert_on_the_third(
    client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection
) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    await _waiting_conversation(admin_conn, owner, 20)
    await enable(client, owner, "unanswered_message_alert")
    await client.delete("/api/v1/integrations/whatsapp_twilio", headers=bearer(owner))  # a failure that will not pass by itself
    for expected in (1, 2, 3):
        failed = await run(client, owner, "unanswered_message_alert")
        assert failed["status"] == "failed" and failed["error"]
        row = next(r for r in (await client.get(URL, headers=bearer(owner))).json() if r["key"] == "unanswered_message_alert")
        assert row["consecutive_failures"] == expected
    assert row["needs_attention"] is True and row["last_run"]["status"] == "failed" and row["enabled"] is True
    alerts = await admin_conn.fetch("SELECT action FROM audit_logs WHERE action = 'automation.failing' AND tenant_id = $1", uuid.UUID(owner["tenant_id"]))
    assert len(alerts) == 1

    await connect_twilio(client, owner)  # the owner reconnects WhatsApp
    ok = await run(client, owner, "unanswered_message_alert")
    assert ok["status"] == "succeeded"
    row = next(r for r in (await client.get(URL, headers=bearer(owner))).json() if r["key"] == "unanswered_message_alert")
    assert row["consecutive_failures"] == 0 and row["needs_attention"] is False


# -- retry, then fallback, then the banner (W-008) ---------------------------------------------------------------


def _stub(monkeypatch: pytest.MonkeyPatch, key: str, run_fn: Any) -> None:
    monkeypatch.setitem(RECIPES, key, dataclasses.replace(RECIPES[key], run=run_fn))


async def test_a_failure_that_passes_by_itself_is_retried_and_counts_as_no_failure(
    client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    await enable(client, owner, "unanswered_message_alert")
    calls = {"n": 0}

    async def flaky(db: Any, tenant_id: uuid.UUID, now: datetime) -> Outcome:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RecipeError("busy", transient=True)
        return Outcome("Alerted the owner about 1 waiting message(s).", 1)

    _stub(monkeypatch, "unanswered_message_alert", flaky)
    done = await run(client, owner, "unanswered_message_alert")
    assert calls["n"] == 3 and done["status"] == "succeeded"
    row = next(r for r in (await client.get(URL, headers=bearer(owner))).json() if r["key"] == "unanswered_message_alert")
    assert row["consecutive_failures"] == 0


async def test_a_configuration_error_is_not_retried(client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    await enable(client, owner, "unanswered_message_alert")
    calls = {"n": 0}

    async def missing_phone(db: Any, tenant_id: uuid.UUID, now: datetime) -> Outcome:
        calls["n"] += 1
        raise RecipeError("Add your phone number in Settings.")

    _stub(monkeypatch, "unanswered_message_alert", missing_phone)
    failed = await run(client, owner, "unanswered_message_alert")
    assert calls["n"] == 1 and failed["status"] == "failed"


async def test_when_whatsapp_keeps_failing_the_message_is_filed_for_approval_instead(
    client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection
) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    await _waiting_conversation(admin_conn, owner, 20)
    await enable(client, owner, "unanswered_message_alert")
    providers.on("twilio.send", httpx.ReadTimeout("slow"))  # every attempt times out
    done = await run(client, owner, "unanswered_message_alert")
    assert done["status"] == "succeeded" and "filed for your approval" in done["summary"]
    waiting = await pending(client, owner)
    assert len(waiting) == 1 and waiting[0]["tool"] == "send_whatsapp_message" and "Sara" in waiting[0]["summary"]
    row = next(r for r in (await client.get(URL, headers=bearer(owner))).json() if r["key"] == "unanswered_message_alert")
    assert row["consecutive_failures"] == 0 and row["needs_attention"] is False
    await run(client, owner, "unanswered_message_alert")
    assert len(await pending(client, owner)) == 1  # the same waiting message is not filed twice


async def test_when_the_fallback_fails_too_it_is_counted_and_the_banner_applies(
    client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    await enable(client, owner, "unanswered_message_alert")

    async def always_down(db: Any, tenant_id: uuid.UUID, now: datetime) -> Outcome:
        raise RecipeError("WhatsApp did not accept the message.", transient=True)

    _stub(monkeypatch, "unanswered_message_alert", always_down)
    for expected in (1, 2, 3):
        failed = await run(client, owner, "unanswered_message_alert")
        assert failed["status"] == "failed"
        row = next(r for r in (await client.get(URL, headers=bearer(owner))).json() if r["key"] == "unanswered_message_alert")
        assert row["consecutive_failures"] == expected
    assert row["needs_attention"] is True and row["enabled"] is True
    alerts = await admin_conn.fetch("SELECT action FROM audit_logs WHERE action = 'automation.failing' AND tenant_id = $1", uuid.UUID(owner["tenant_id"]))
    assert len(alerts) == 1


async def test_a_recipe_without_its_integration_fails_with_a_reason_and_sends_nothing(
    client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection
) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    await _waiting_conversation(admin_conn, owner, 20)  # independent of the time of day
    await enable(client, owner, "unanswered_message_alert")
    await client.delete("/api/v1/integrations/whatsapp_twilio", headers=bearer(owner))
    failed = await run(client, owner, "unanswered_message_alert")
    assert failed["status"] == "failed" and "not connected" in failed["error"]
    assert providers.calls("twilio.send") == []


async def test_history_filters_and_a_shop_only_sees_its_own_runs(client: AsyncClient, providers: FakeProviders) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    await enable(client, a, "low_stock_vendor_draft")
    await run(client, a, "low_stock_vendor_draft")
    mine = (await client.get(f"{URL}runs", headers=bearer(a))).json()
    assert mine["total"] == 1 and mine["items"][0]["automation_key"] == "low_stock_vendor_draft" and mine["items"][0]["trigger_source"] == "manual"
    assert (await client.get(f"{URL}runs", params={"status": "failed"}, headers=bearer(a))).json()["total"] == 0
    assert (await client.get(f"{URL}runs", params={"status": "weird"}, headers=bearer(a))).status_code == 422
    assert (await client.get(f"{URL}runs", params={"automation": "nope"}, headers=bearer(a))).status_code == 404
    assert (await client.get(f"{URL}runs", headers=bearer(b))).json()["total"] == 0


async def test_the_scheduler_only_runs_switched_on_recipes(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    await client.get(URL, headers=bearer(owner))  # creates the rows, all off
    assert await automation_service.tick(local(10, 0)) == 0
    await enable(client, owner, "low_stock_vendor_draft")
    assert await automation_service.tick(local(3, 0)) == 0  # nothing low: nothing to record
