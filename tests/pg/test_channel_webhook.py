"""Tasks 61, 83 and the inbound half of 71: the Twilio webhook: signature, replay protection, AI reply, handover, failures."""

from __future__ import annotations

import json
import uuid
from typing import Any

import asyncpg
import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.core.tenancy import tenant_session
from app.evals.replay import ReplayModel, ToolCall, Turn
from tests.pg.agent_support import scripted_provider, use_model  # noqa: F401  (autouse fixture + helper)
from tests.pg.channel_support import (
    TWILIO_SID,
    FakeProviders,
    connect_twilio,
    post_webhook,
    signed_webhook,
    twilio_form,
)
from tests.pg.conftest import bearer, register
from tests.pg.test_sales_api import customer, product
from tests.unit.provider_support import fixture_json

pytestmark = pytest.mark.pg

CONVERSATIONS = "/api/v1/conversations/"


def answers(price_text: str = "The Classic Shirt is Rs 2,500.00 and in stock.") -> ReplayModel:
    return ReplayModel([Turn(tool_calls=[ToolCall("find_product", {"query": "shirt"})]), Turn(text=price_text)])


class NeverCalled(ReplayModel):
    def __init__(self) -> None:
        super().__init__([])


async def shop_with_whatsapp(client: AsyncClient, name: str = "Shop A", sid: str = TWILIO_SID) -> dict[str, Any]:
    owner = await register(client, name)
    await connect_twilio(client, owner, sid)
    await product(client, owner, "SHIRT", "2500.00", 10, name="Classic Shirt", cost="1800.00")
    return owner


async def conversations(client: AsyncClient, owner: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = (await client.get(CONVERSATIONS, headers=bearer(owner))).json()["items"]
    return items


async def thread(client: AsyncClient, owner: dict[str, Any]) -> list[dict[str, Any]]:
    convo = (await conversations(client, owner))[0]
    messages: list[dict[str, Any]] = (await client.get(f"{CONVERSATIONS}{convo['id']}", headers=bearer(owner))).json()["messages"]
    return messages


async def test_a_signed_message_is_stored_answered_by_the_ai_and_the_reply_is_sent(
    client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await shop_with_whatsapp(client)
    use_model(monkeypatch, answers())
    res = await post_webhook(client, twilio_form())
    assert res.status_code == 200 and res.json() == {"status": "ok"}

    convo = (await conversations(client, owner))[0]
    assert (convo["phone"], convo["status"], convo["mode"], convo["contact_name"]) == ("+923001234567", "ai_handling", "ai", "Sara")
    messages = await thread(client, owner)
    assert [(m["direction"], m["sender"], m["status"]) for m in messages] == [("inbound", "customer", "received"), ("outbound", "ai", "sent")]
    assert messages[0]["text"] == "Do you have the blue shirt?" and "Rs 2,500.00" in messages[1]["text"]
    sent = providers.calls("twilio.send")
    assert len(sent) == 1 and b"whatsapp%3A%2B923001234567" in sent[0].content and b"Rs+2%2C500.00" in sent[0].content


async def test_the_ai_never_sees_cost_or_credit(client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await shop_with_whatsapp(client)
    use_model(monkeypatch, answers())
    await post_webhook(client, twilio_form())
    tid = uuid.UUID(owner["tenant_id"])
    async with tenant_session(tid) as db:
        trace = (await db.execute(text("SELECT agent, trace_json::text FROM agent_runs ORDER BY created_at"))).all()
    assert [r[0] for r in trace] == ["customer"]
    assert "1,800" not in trace[0][1] and "1800.00" not in trace[0][1] and "2,500.00" in trace[0][1]  # the price yes, the cost never


async def test_a_replayed_event_is_ignored_and_changes_nothing(client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await shop_with_whatsapp(client)
    use_model(monkeypatch, answers())
    form = twilio_form(sid="SM" + "1" * 32)
    first = await post_webhook(client, form)
    again = await post_webhook(client, form)
    assert first.json() == {"status": "ok"} and again.status_code == 200 and again.json() == {"status": "ignored"}
    assert len(await thread(client, owner)) == 2 and len(providers.calls("twilio.send")) == 1


async def test_a_bad_missing_or_foreign_signature_is_rejected_and_nothing_is_stored(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await shop_with_whatsapp(client)
    form = twilio_form()
    body, headers = signed_webhook(form)
    bad = await client.post("/api/v1/webhooks/twilio", content=body, headers={**headers, "X-Twilio-Signature": "AAAA"})
    none = await client.post("/api/v1/webhooks/twilio", content=body, headers={"Content-Type": headers["Content-Type"]})
    wrong_token = await post_webhook(client, form, token="another-shops-token-0000000000")
    tampered = await client.post("/api/v1/webhooks/twilio", content=body.replace(b"blue", b"red"), headers=headers)
    assert {bad.status_code, none.status_code, wrong_token.status_code, tampered.status_code} == {403}
    assert await conversations(client, owner) == [] and providers.calls("twilio.send") == []


async def test_an_unknown_shop_gets_the_same_answer_as_a_bad_signature(client: AsyncClient, providers: FakeProviders) -> None:
    await shop_with_whatsapp(client)
    unknown = await post_webhook(client, twilio_form(account="AC" + "b" * 32))
    bad = await client.post("/api/v1/webhooks/twilio", content=b"AccountSid=" + TWILIO_SID.encode() + b"&Body=x", headers={"X-Twilio-Signature": "AAAA"})
    assert unknown.status_code == bad.status_code == 403
    assert unknown.json()["detail"] == bad.json()["detail"] == "Invalid signature"


async def test_a_disconnected_shop_no_longer_receives_messages(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await shop_with_whatsapp(client)
    await client.delete("/api/v1/integrations/whatsapp_twilio", headers=bearer(owner))
    assert (await post_webhook(client, twilio_form())).status_code == 403


async def test_a_message_goes_to_the_shop_whose_account_it_names(client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch) -> None:
    a = await shop_with_whatsapp(client, "Shop A", TWILIO_SID)
    b = await shop_with_whatsapp(client, "Shop B", "AC" + "c" * 32)
    use_model(monkeypatch, answers())
    await post_webhook(client, twilio_form(account="AC" + "c" * 32))
    assert await conversations(client, a) == [] and len(await conversations(client, b)) == 1


async def test_a_delivery_receipt_is_acknowledged_without_creating_a_conversation(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await shop_with_whatsapp(client)
    receipt = {"SmsSid": "SM" + "2" * 32, "MessageStatus": "delivered", "MessageSid": "SM" + "2" * 32, "AccountSid": TWILIO_SID, "From": "whatsapp:+14155238886", "To": "whatsapp:+923001234567", "SmsMessageSid": "SM" + "2" * 32}
    res = await post_webhook(client, receipt)
    assert res.status_code == 200 and res.json() == {"status": "ignored"} and await conversations(client, owner) == []


async def test_when_the_ai_cannot_help_it_hands_over_tells_the_customer_and_goes_quiet(
    client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await shop_with_whatsapp(client)
    use_model(monkeypatch, ReplayModel([Turn(text="HANDOVER")]))
    await post_webhook(client, twilio_form(text="I want a refund"))
    convo = (await conversations(client, owner))[0]
    assert (convo["mode"], convo["status"]) == ("human", "needs_human") and "customer needs a person" in (convo["handoff_note"] or "")
    messages = await thread(client, owner)
    assert messages[-1]["sender"] == "ai" and "team will reply" in messages[-1]["text"]
    sent = len(providers.calls("twilio.send"))

    use_model(monkeypatch, NeverCalled())  # the next message must not reach the AI at all
    await post_webhook(client, twilio_form(text="Hello? Anyone?"))
    convo = (await conversations(client, owner))[0]
    assert (convo["mode"], convo["status"]) == ("human", "needs_human")
    assert len(providers.calls("twilio.send")) == sent  # and the customer is not answered by the AI


async def test_the_switch_off_pauses_the_ai_and_hands_over(client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await shop_with_whatsapp(client)
    assert (await client.put("/api/v1/agent-runs/switch", json={"enabled": False}, headers=bearer(owner))).status_code == 200
    use_model(monkeypatch, NeverCalled())
    await post_webhook(client, twilio_form())
    convo = (await conversations(client, owner))[0]
    assert convo["mode"] == "human" and "switched off" in (convo["handoff_note"] or "")
    tid = uuid.UUID(owner["tenant_id"])
    async with tenant_session(tid) as db:
        outcomes = [r[0] for r in (await db.execute(text("SELECT outcome FROM agent_runs WHERE agent = 'customer'"))).all()]
    assert outcomes == ["paused"]


async def test_a_provider_outage_while_replying_keeps_the_reply_as_failed_and_hands_over(
    client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch, admin_conn: asyncpg.Connection
) -> None:
    owner = await shop_with_whatsapp(client)
    providers.on("twilio.send", httpx.ReadTimeout("slow"))
    use_model(monkeypatch, answers())
    res = await post_webhook(client, twilio_form())
    assert res.status_code == 200  # the inbound message is safe whatever the provider does
    messages = await thread(client, owner)
    assert messages[0]["status"] == "received" and messages[1]["status"] == "send_failed" and "retry" in (messages[1]["error"] or "")
    convo = (await conversations(client, owner))[0]
    assert (convo["mode"], convo["status"]) == ("human", "needs_human")
    assert await admin_conn.fetchval("SELECT count(*) FROM audit_logs WHERE action = 'integration.degraded'") >= 1
    listed = (await client.get("/api/v1/integrations/", headers=bearer(owner))).json()[0]
    assert listed["status"] == "connected" and listed["last_error"]  # degraded, not disconnected


async def test_a_refused_credential_on_reply_pauses_sending_and_asks_to_reconnect(
    client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await shop_with_whatsapp(client)
    providers.on("twilio.send", httpx.Response(401, json=fixture_json("twilio_error_20003.json")))
    use_model(monkeypatch, answers())
    await post_webhook(client, twilio_form())
    assert (await thread(client, owner))[1]["status"] == "send_failed"
    listed = (await client.get("/api/v1/integrations/", headers=bearer(owner))).json()[0]
    assert listed["status"] == "error" and listed["reconnect_required"] is True
    # inbound keeps working for an integration in error? No: the webhook only accepts connected shops
    assert (await post_webhook(client, twilio_form())).status_code == 403


async def test_a_customer_with_the_same_phone_is_linked_and_the_panel_hides_credit_from_staff(
    client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await shop_with_whatsapp(client)
    ali = await customer(client, owner, "923001234567")  # stored without the plus: still the same person
    use_model(monkeypatch, answers())
    await post_webhook(client, twilio_form())
    convo = (await conversations(client, owner))[0]
    assert convo["customer_id"] == ali["id"]
    detail = (await client.get(f"{CONVERSATIONS}{convo['id']}", headers=bearer(owner))).json()
    assert detail["context"]["customer_name"] == "Ali" and detail["context"]["balance"] == "0.00"
    assert "Record a sale" in detail["context"]["suggested_actions"]


async def test_the_webhook_trace_holds_no_phone_number(client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await shop_with_whatsapp(client)
    use_model(monkeypatch, answers())
    await post_webhook(client, twilio_form(text="Hi, call me on 03001234567, I am Sara"))
    tid = uuid.UUID(owner["tenant_id"])
    async with tenant_session(tid) as db:
        row = (await db.execute(text("SELECT input_text, trace_json::text FROM agent_runs WHERE agent = 'customer'"))).one()
    assert "923001234567" not in json.dumps(row[0]) and "923001234567" not in row[1]
    assert "Sara" not in row[0]
