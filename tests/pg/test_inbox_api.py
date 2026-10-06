"""Task 71 (F-005): the unified inbox: roles, filters, replying, AI / Human toggle, retry, isolation, validation."""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.evals.replay import ReplayModel, ToolCall, Turn
from tests.pg.agent_support import scripted_provider, use_model  # noqa: F401  (autouse fixture + helper)
from tests.pg.channel_support import FakeProviders, connect_twilio, post_webhook, twilio_form
from tests.pg.conftest import bearer, member, register
from tests.unit.provider_support import fixture_json

pytestmark = pytest.mark.pg

URL = "/api/v1/conversations/"


def handover() -> ReplayModel:
    return ReplayModel([Turn(text="HANDOVER")])


async def open_thread(client: AsyncClient, monkeypatch: pytest.MonkeyPatch, owner: dict[str, Any], phone: str = "+923001234567", text: str = "Hello") -> dict[str, Any]:
    use_model(monkeypatch, ReplayModel([Turn(tool_calls=[ToolCall("find_product", {"query": "x"})]), Turn(text="We are open until 9pm.")]))
    assert (await post_webhook(client, twilio_form(sender=phone, text=text))).status_code == 200
    items = (await client.get(URL, headers=bearer(owner))).json()["items"]
    found: dict[str, Any] = next(c for c in items if c["phone"] == phone)
    return found


async def test_every_role_can_read_and_list_conversations_and_nobody_else(
    client: AsyncClient, app_engine: AsyncEngine, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    convo = await open_thread(client, monkeypatch, owner)
    for role in ("manager", "staff"):
        who = await member(client, app_engine, owner, role)
        assert (await client.get(URL, headers=bearer(who))).json()["total"] == 1
        assert (await client.get(f"{URL}{convo['id']}", headers=bearer(who))).status_code == 200
    assert (await client.get(URL)).status_code == 401
    assert (await client.get(f"{URL}{convo['id']}")).status_code == 401


async def test_the_list_filters_by_status_and_searches_by_phone_or_name(
    client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    await open_thread(client, monkeypatch, owner, "+923001110001")
    second = await open_thread(client, monkeypatch, owner, "+923002220002")
    await client.patch(f"{URL}{second['id']}", json={"status": "resolved"}, headers=bearer(owner))
    assert (await client.get(URL, params={"status": "resolved"}, headers=bearer(owner))).json()["total"] == 1
    assert (await client.get(URL, params={"status": "ai_handling"}, headers=bearer(owner))).json()["total"] == 1
    assert (await client.get(URL, params={"q": "2220"}, headers=bearer(owner))).json()["items"][0]["phone"] == "+923002220002"
    assert (await client.get(URL, params={"q": "sara"}, headers=bearer(owner))).json()["total"] == 2  # the profile name Twilio sent
    assert (await client.get(URL, params={"status": "weird"}, headers=bearer(owner))).status_code == 422
    newest = (await client.get(URL, headers=bearer(owner))).json()["items"]
    assert [c["last_message_at"] for c in newest] == sorted((c["last_message_at"] for c in newest), reverse=True)


async def test_a_reply_is_sent_and_takes_the_conversation_over_from_the_ai(
    client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    convo = await open_thread(client, monkeypatch, owner)
    assert (convo["mode"], convo["status"]) == ("ai", "ai_handling")
    before = len(providers.calls("twilio.send"))
    res = await client.post(f"{URL}{convo['id']}/messages", json={"text": "Yes, come by anytime."}, headers=bearer(owner))
    assert res.status_code == 201 and (res.json()["status"], res.json()["sender"]) == ("sent", "staff")
    assert len(providers.calls("twilio.send")) == before + 1
    after = (await client.get(f"{URL}{convo['id']}", headers=bearer(owner))).json()["conversation"]
    assert (after["mode"], after["status"]) == ("human", "open") and after["assigned_to"] is not None

    use_model(monkeypatch, ReplayModel([]))  # a person is in charge now: the AI must not be asked
    await post_webhook(client, twilio_form(text="Thanks!"))
    assert len(providers.calls("twilio.send")) == before + 1


async def test_the_same_reply_sent_twice_with_one_key_is_sent_once(client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    convo = await open_thread(client, monkeypatch, owner)
    before = len(providers.calls("twilio.send"))
    key = {"text": "Ready for pickup", "idempotency_key": "click-" + uuid.uuid4().hex[:12]}
    first = await client.post(f"{URL}{convo['id']}/messages", json=key, headers=bearer(owner))
    second = await client.post(f"{URL}{convo['id']}/messages", json=key, headers=bearer(owner))
    assert first.json()["id"] == second.json()["id"] and len(providers.calls("twilio.send")) == before + 1


async def test_replying_without_whatsapp_is_refused_with_a_reason_and_stores_nothing(
    client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    convo = await open_thread(client, monkeypatch, owner)
    await client.delete("/api/v1/integrations/whatsapp_twilio", headers=bearer(owner))
    res = await client.post(f"{URL}{convo['id']}/messages", json={"text": "Hello"}, headers=bearer(owner))
    assert res.status_code == 422 and res.json()["code"] == "integration_not_connected"
    detail = (await client.get(f"{URL}{convo['id']}", headers=bearer(owner))).json()
    assert [m["sender"] for m in detail["messages"]] == ["customer", "ai"]  # nothing was added
    assert "not connected" in detail["provider_notice"]


async def test_a_failed_send_keeps_its_reason_and_can_be_retried(client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    convo = await open_thread(client, monkeypatch, owner)
    providers.on("twilio.send", httpx.Response(400, json=fixture_json("twilio_error_63015.json")))
    sent = await client.post(f"{URL}{convo['id']}/messages", json={"text": "Hello again"}, headers=bearer(owner))
    assert sent.status_code == 201 and sent.json()["status"] == "send_failed" and "join" in sent.json()["error"]

    providers.on("twilio.send", httpx.Response(201, json=fixture_json("twilio_message_created.json")))
    retried = await client.post(f"{URL}{convo['id']}/messages/{sent.json()['id']}/retry", headers=bearer(owner))
    assert retried.status_code == 200 and retried.json()["status"] == "sent" and retried.json()["error"] is None
    again = await client.post(f"{URL}{convo['id']}/messages/{sent.json()['id']}/retry", headers=bearer(owner))
    assert again.status_code == 422 and again.json()["code"] == "not_retryable"


async def test_the_ai_human_toggle_stops_and_resumes_the_ai_and_a_new_message_reopens_a_resolved_thread(
    client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    convo = await open_thread(client, monkeypatch, owner)
    sends = len(providers.calls("twilio.send"))
    human = (await client.patch(f"{URL}{convo['id']}", json={"mode": "human"}, headers=bearer(owner))).json()
    assert (human["mode"], human["status"]) == ("human", "open")
    use_model(monkeypatch, ReplayModel([]))
    await post_webhook(client, twilio_form(text="Are you there?"))
    assert len(providers.calls("twilio.send")) == sends  # the AI stayed silent
    assert (await client.get(f"{URL}{convo['id']}", headers=bearer(owner))).json()["conversation"]["status"] == "needs_human"

    ai = (await client.patch(f"{URL}{convo['id']}", json={"mode": "ai"}, headers=bearer(owner))).json()
    assert (ai["mode"], ai["status"], ai["handoff_note"]) == ("ai", "ai_handling", None)
    done = (await client.patch(f"{URL}{convo['id']}", json={"status": "resolved"}, headers=bearer(owner))).json()
    assert done["status"] == "resolved"
    use_model(monkeypatch, ReplayModel([Turn(text="Welcome back! How can I help?")]))
    await post_webhook(client, twilio_form(text="Hi again"))
    assert (await client.get(f"{URL}{convo['id']}", headers=bearer(owner))).json()["conversation"]["status"] == "ai_handling"


async def test_assigning_needs_a_member_of_the_shop(client: AsyncClient, app_engine: AsyncEngine, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await register(client, "Shop A")
    outsider = await register(client, "Shop B")
    await connect_twilio(client, owner)
    convo = await open_thread(client, monkeypatch, owner)
    staff = await member(client, app_engine, owner, "staff")
    staff_id = (await client.get("/api/v1/auth/me", headers=bearer(staff))).json()["user"]["id"]
    outsider_id = (await client.get("/api/v1/auth/me", headers=bearer(outsider))).json()["user"]["id"]
    ok = await client.patch(f"{URL}{convo['id']}", json={"assigned_to": staff_id}, headers=bearer(owner))
    assert ok.status_code == 200 and ok.json()["assigned_to"] == staff_id
    bad = await client.patch(f"{URL}{convo['id']}", json={"assigned_to": outsider_id}, headers=bearer(owner))
    assert bad.status_code == 422 and bad.json()["code"] == "not_a_member"
    cleared = await client.patch(f"{URL}{convo['id']}", json={"unassign": True}, headers=bearer(owner))
    assert cleared.json()["assigned_to"] is None


@pytest.mark.parametrize(
    ("body", "code"),
    [({"text": ""}, 422), ({"text": "   "}, 422), ({"text": "x" * 1001}, 422), ({"text": "ok", "idempotency_key": "short"}, 422), ({"text": "ok", "idempotency_key": "has spaces in it!"}, 422)],
)
async def test_reply_validation(client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch, body: dict[str, str], code: int) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    convo = await open_thread(client, monkeypatch, owner)
    res = await client.post(f"{URL}{convo['id']}/messages", json=body, headers=bearer(owner))
    assert res.status_code == code and res.json()["code"] == "validation_failed"


async def test_update_validation(client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    convo = await open_thread(client, monkeypatch, owner)
    assert (await client.patch(f"{URL}{convo['id']}", json={}, headers=bearer(owner))).json()["code"] == "empty_update"
    assert (await client.patch(f"{URL}{convo['id']}", json={"mode": "robot"}, headers=bearer(owner))).status_code == 422
    assert (await client.patch(f"{URL}{convo['id']}", json={"status": "needs_human"}, headers=bearer(owner))).status_code == 422
    assert (await client.patch(f"{URL}{convo['id']}", json={"phone": "+1"}, headers=bearer(owner))).status_code == 422


async def test_another_shop_cannot_see_reply_to_or_change_a_conversation(
    client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await register(client, "Shop A")
    other = await register(client, "Shop B")
    await connect_twilio(client, owner)
    convo = await open_thread(client, monkeypatch, owner)
    assert (await client.get(URL, headers=bearer(other))).json()["total"] == 0
    assert (await client.get(f"{URL}{convo['id']}", headers=bearer(other))).status_code == 404
    assert (await client.patch(f"{URL}{convo['id']}", json={"status": "resolved"}, headers=bearer(other))).status_code == 404
    assert (await client.post(f"{URL}{convo['id']}/messages", json={"text": "hi"}, headers=bearer(other))).status_code == 404


async def test_the_detail_shows_the_thread_oldest_first_and_staff_do_not_see_credit(
    client: AsyncClient, app_engine: AsyncEngine, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.pg.test_sales_api import customer

    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    await customer(client, owner, "+923001234567")
    convo = await open_thread(client, monkeypatch, owner)
    staff = await member(client, app_engine, owner, "staff")
    as_owner = (await client.get(f"{URL}{convo['id']}", headers=bearer(owner))).json()
    as_staff = (await client.get(f"{URL}{convo['id']}", headers=bearer(staff))).json()
    created = [m["created_at"] for m in as_owner["messages"]]
    assert created == sorted(created) and as_owner["messages"][0]["direction"] == "inbound"
    assert as_owner["context"]["balance"] == "0.00" and as_staff["context"]["balance"] is None
    assert as_owner["provider_notice"] is None
