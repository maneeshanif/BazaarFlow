"""Tasks 32, 33, 66-69, 87, 91 (W-007, F-023): the voice agent: webhook trust, tools, read-back, handoff, privacy, cost, cap."""

from __future__ import annotations

import json
import uuid
from typing import Any

import asyncpg
import httpx
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.evals import voice_replay
from app.services import automation_service
from tests.pg.channel_support import VAPI_ASSISTANT, VAPI_SECRET, FakeProviders, connect_vapi
from tests.pg.conftest import bearer, member, register
from tests.pg.test_sales_api import customer, product

pytestmark = pytest.mark.pg

HOOK = "/api/v1/webhooks/vapi"
SETTINGS = "/api/v1/voice/settings"
CALLS = "/api/v1/voice/calls"
CALLER = "+923009990001"


@pytest_asyncio.fixture(autouse=True)
async def clean_slate(admin_conn: asyncpg.Connection) -> None:
    await admin_conn.execute("DELETE FROM voice_calls")
    await admin_conn.execute("DELETE FROM voice_settings")
    await admin_conn.execute("DELETE FROM webhook_events WHERE provider = 'vapi'")


def settings_body(**over: Any) -> dict[str, Any]:
    return {
        "enabled": True,
        "greeting": "Hello, Ali Mart. How can I help?",
        "consent_notice": "This call may be recorded and transcribed to help us serve you.",
        "max_call_seconds": 300,
        "monthly_cap_usd": "5.00",
        "handoff_phone": None,
        "retention_days": 30,
        **over,
    }


def message(kind: str, call: str = "call-1", assistant: str = VAPI_ASSISTANT, caller: str = CALLER, **fields: Any) -> dict[str, Any]:
    return {"message": {"type": kind, "call": {"id": call, "assistantId": assistant, "type": "inboundPhoneCall", "customer": {"number": caller}}, **fields}}


def tool(name: str, call_id: str = "toolu_1", **arguments: Any) -> dict[str, Any]:
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": arguments}}


async def post(client: AsyncClient, payload: dict[str, Any], secret: str | None = VAPI_SECRET, header: str = "authorization") -> httpx.Response:
    headers: dict[str, str] = {}
    if secret is not None:
        headers = {"Authorization": f"Bearer {secret}"} if header == "authorization" else {"X-Vapi-Secret": secret}
    return await client.post(HOOK, content=json.dumps(payload), headers={"Content-Type": "application/json", **headers})


async def ready_shop(client: AsyncClient, **over: Any) -> dict[str, Any]:
    owner = await register(client, "Ali Mart")
    await connect_vapi(client, owner)
    res = await client.put(SETTINGS, json=settings_body(**over), headers=bearer(owner))
    assert res.status_code == 200, res.text
    return owner


# -- connecting VAPI (91) and who may call the webhook -----------------------------------------------------------


async def test_vapi_connects_with_or_without_an_api_key_and_the_secret_is_never_returned(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    body = await connect_vapi(client, owner)
    assert body["status"] == "connected" and body["external_id"] == VAPI_ASSISTANT and body["token_hint"] == f"****{VAPI_SECRET[-4:]}"
    assert VAPI_SECRET not in str((await client.get("/api/v1/integrations/", headers=bearer(owner))).json())
    assert providers.calls("vapi.assistant") == []  # no API key: webhook mode, nothing to check
    await client.delete("/api/v1/integrations/vapi", headers=bearer(owner))
    with_key = await client.put(
        "/api/v1/integrations/vapi",
        json={"credentials": {"assistant_id": VAPI_ASSISTANT, "webhook_secret": VAPI_SECRET, "api_key": "k" * 24}},
        headers=bearer(owner),
    )
    assert with_key.status_code == 200 and len(providers.calls("vapi.assistant")) == 1
    await client.delete("/api/v1/integrations/vapi", headers=bearer(owner))
    providers.on("vapi.assistant", httpx.Response(200, json={"id": "someone-elses-assistant"}))
    wrong = await client.put(
        "/api/v1/integrations/vapi",
        json={"credentials": {"assistant_id": VAPI_ASSISTANT, "webhook_secret": VAPI_SECRET, "api_key": "k" * 24}},
        headers=bearer(owner),
    )
    assert wrong.status_code == 422 and wrong.json()["code"] == "credentials_rejected"


@pytest.mark.parametrize(
    ("credentials", "field"),
    [({"assistant_id": "x", "webhook_secret": "s" * 20}, "assistant_id"), ({"assistant_id": VAPI_ASSISTANT, "webhook_secret": "short"}, "webhook_secret")],
)
async def test_vapi_credential_rules(client: AsyncClient, providers: FakeProviders, credentials: dict[str, str], field: str) -> None:
    owner = await register(client, "Shop A")
    res = await client.put("/api/v1/integrations/vapi", json={"credentials": credentials}, headers=bearer(owner))
    assert res.status_code == 422 and field in {e["field"] for e in res.json()["errors"]}


async def test_the_webhook_accepts_the_bearer_token_or_the_legacy_header_and_nothing_else(client: AsyncClient, providers: FakeProviders) -> None:
    await ready_shop(client)
    ok = message("status-update", status="in-progress")
    assert (await post(client, ok)).status_code == 200
    assert (await post(client, message("status-update", call="call-2", status="in-progress"), header="legacy")).status_code == 200
    for bad in (None, "wrong-token-wrong-token-0000"):
        assert (await post(client, message("status-update", call="call-3", status="in-progress"), secret=bad)).status_code == 403
    unknown = await post(client, message("status-update", call="call-4", assistant="asst-unknown-unknown"))
    assert unknown.status_code == 403 and unknown.json()["detail"] == "Invalid signature"
    assert (await client.post(HOOK, content=b"not json", headers={"Authorization": f"Bearer {VAPI_SECRET}"})).status_code == 400
    assert (await client.post(HOOK, content=json.dumps({"hello": 1}))).status_code == 400


async def test_a_disconnected_shop_no_longer_takes_calls(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await ready_shop(client)
    await client.delete("/api/v1/integrations/vapi", headers=bearer(owner))
    assert (await post(client, message("status-update", status="in-progress"))).status_code == 403


# -- assistant-request, the cap (32) -----------------------------------------------------------------------------


async def test_a_call_is_accepted_when_the_agent_is_on_and_refused_with_a_spoken_reason_when_it_is_off_or_over_its_cap(
    client: AsyncClient, providers: FakeProviders
) -> None:
    owner = await ready_shop(client, monthly_cap_usd="0.10")
    accepted = (await post(client, message("assistant-request"))).json()
    assert accepted == {"assistantId": VAPI_ASSISTANT}
    await post(client, message("status-update", status="in-progress"))
    await post(client, message("end-of-call-report", endedReason="customer-ended-call", cost=0.12, durationSeconds=60))
    over = (await post(client, message("assistant-request", call="call-9"))).json()
    assert "error" in over and "WhatsApp" in over["error"] and "assistantId" not in over
    assert (await client.get(SETTINGS, headers=bearer(owner))).json()["percent_used"] == 120

    await client.put(SETTINGS, json=settings_body(monthly_cap_usd="5.00", enabled=False), headers=bearer(owner))
    off = (await post(client, message("assistant-request", call="call-10"))).json()
    assert "error" in off


# -- the tools, read-back, correction and handoff (66, 68) -------------------------------------------------------


async def test_lookup_and_order_status_answer_from_the_shops_own_data(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await ready_shop(client)
    await product(client, owner, "SHIRT", "2500.00", 7, name="Classic Shirt", cost="1800.00")
    await product(client, owner, "CAP", "500.00", 0, name="Cap")
    answer = (await post(client, message("tool-calls", toolCallList=[tool("lookup_product", query="shirt")]))).json()
    text = answer["results"][0]["result"]
    assert answer["results"][0]["toolCallId"] == "toolu_1" and "Classic Shirt is Rs 2,500 and 7 in stock" in text and "1800" not in text
    out = (await post(client, message("tool-calls", call="c2", toolCallList=[tool("lookup_product", query="cap")]))).json()
    assert "out of stock" in out["results"][0]["result"]
    none = (await post(client, message("tool-calls", call="c3", toolCallList=[tool("lookup_product", query="unicorn")]))).json()
    assert "could not find" in none["results"][0]["result"]
    ali = await customer(client, owner, "+923009990001")
    assert ali["id"]
    unknown = (await post(client, message("tool-calls", call="c4", caller="+923000000000", toolCallList=[tool("order_status")]))).json()
    assert "could not find an order" in unknown["results"][0]["result"]


async def test_a_message_is_read_back_digit_by_digit_corrected_and_only_then_saved(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await ready_shop(client)
    first = (await post(client, message("tool-calls", toolCallList=[tool("create_support_ticket", "t1", contact="Imran 03001112233", issue_summary="Bulk order call back", confirmed=False)]))).json()
    assert "0 3 0 0 1 1 1 2 2 3 3" in first["results"][0]["result"] and "confirmed false" in first["results"][0]["result"]
    corrected = (await post(client, message("tool-calls", toolCallList=[tool("create_support_ticket", "t2", contact="Imran 03001112244", issue_summary="Bulk order call back", confirmed="false")]))).json()
    assert "0 3 0 0 1 1 1 2 2 4 4" in corrected["results"][0]["result"]
    assert (await client.get("/api/v1/voice/calls", headers=bearer(owner))).json()["items"][0]["has_ticket"] is False  # nothing is saved yet
    done = (await post(client, message("tool-calls", toolCallList=[tool("create_support_ticket", "t3", contact="Imran 03001112244", issue_summary="Bulk order call back", confirmed=True)]))).json()
    assert "reference" in done["results"][0]["result"]
    assert (await client.get(CALLS, headers=bearer(owner))).json()["items"][0]["has_ticket"] is True


async def test_a_ticket_needs_a_contact_and_a_summary(client: AsyncClient, providers: FakeProviders) -> None:
    await ready_shop(client)
    answer = (await post(client, message("tool-calls", toolCallList=[tool("create_support_ticket", contact="", issue_summary="", confirmed=True)]))).json()
    assert "still need" in answer["results"][0]["result"]


async def test_asking_for_a_person_escalates_with_context_and_leaves_a_callback_when_no_one_can_take_it(
    client: AsyncClient, providers: FakeProviders
) -> None:
    owner = await ready_shop(client)
    answer = (await post(client, message("tool-calls", toolCallList=[tool("transfer_to_human", reason="Complaint about a late delivery")]))).json()
    assert "callback request" in answer["results"][0]["result"]
    call = (await client.get(CALLS, headers=bearer(owner))).json()["items"][0]
    assert call["status"] == "escalated" and call["escalated"] is True and call["has_ticket"] is True
    detail = (await client.get(f"{CALLS}/{call['id']}", headers=bearer(owner))).json()
    assert "late delivery" in detail["handoff_note"]


async def test_with_a_handoff_number_the_agent_is_told_to_transfer(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await ready_shop(client, handoff_phone="+923001234567")
    answer = (await post(client, message("tool-calls", toolCallList=[tool("transfer_to_human", reason="Wants the owner")]))).json()
    assert "transfer the call" in answer["results"][0]["result"]
    assert (await client.get(CALLS, headers=bearer(owner))).json()["items"][0]["has_ticket"] is False  # no callback needed


async def test_an_unknown_tool_is_refused_and_a_replayed_tool_call_is_not_run_twice(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await ready_shop(client)
    refused = (await post(client, message("tool-calls", toolCallList=[tool("refund_order", order="x")]))).json()
    assert refused["results"][0]["error"] == "I cannot do that."
    save = message("tool-calls", call="c9", toolCallList=[tool("create_support_ticket", "same", contact="Imran 0300", issue_summary="Call me", confirmed=True)])
    first = (await post(client, save)).json()
    again = (await post(client, save)).json()
    assert "reference" in first["results"][0]["result"] and "already done" in again["results"][0]["result"]
    assert (await client.get(CALLS, headers=bearer(owner))).json()["items"][0]["has_ticket"] is True


# -- cost and latency per turn (32), privacy (69) -----------------------------------------------------------------


async def test_each_call_logs_per_turn_latency_and_cost_and_only_the_last_four_digits_of_the_number(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await ready_shop(client)
    await post(client, message("status-update", status="in-progress"))
    report = message(
        "end-of-call-report",
        endedReason="customer-ended-call",
        cost=0.0425,
        durationSeconds=75,
        artifact={"transcript": "AI: Hi. User: hello", "performanceMetrics": {"turnLatencies": [{"turnLatency": 800}, {"turnLatency": 1200}, {"turnLatency": 1000}]}},
    )
    await post(client, report)
    listed = (await client.get(CALLS, headers=bearer(owner))).json()["items"][0]
    assert (listed["turn_count"], listed["avg_latency_ms"], listed["max_latency_ms"], listed["cost_usd"]) == (3, 1000, 1200, "0.0425")
    assert (listed["status"], listed["duration_seconds"], listed["caller_hint"]) == ("completed", 75, "…0001")
    everything = json.dumps((await client.get(CALLS, headers=bearer(owner))).json()) + json.dumps((await client.get(f"{CALLS}/{listed['id']}", headers=bearer(owner))).json())
    assert "923009990001" not in everything
    assert (await client.get(SETTINGS, headers=bearer(owner))).json()["month_spend_usd"] == "0.04"
    assert (await post(client, report)).status_code == 200  # a replayed report changes nothing
    assert (await client.get(CALLS, headers=bearer(owner))).json()["total"] == 1


async def test_a_call_that_ends_in_an_error_is_marked_failed(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await ready_shop(client)
    await post(client, message("end-of-call-report", endedReason="pipeline-error-openai-llm-failed", cost=0.0, durationSeconds=3))
    assert (await client.get(CALLS, params={"status": "failed"}, headers=bearer(owner))).json()["total"] == 1


async def test_stored_transcripts_and_summaries_are_redacted_and_removed_after_the_retention_period(
    client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection
) -> None:
    owner = await ready_shop(client, retention_days=7)
    await customer(client, owner, "+923001234567")
    await post(
        client,
        message(
            "end-of-call-report",
            call="old",
            endedReason="customer-ended-call",
            cost=0.01,
            durationSeconds=30,
            summary="Ali asked about a shirt.",
            artifact={"transcript": "User: I am Ali, call me on 03001234567 or ali@example.com or +92 300 9990001."},
        ),
    )
    stored = (await client.get(CALLS, headers=bearer(owner))).json()["items"][0]
    detail = (await client.get(f"{CALLS}/{stored['id']}", headers=bearer(owner))).json()
    for secret in ("Ali", "03001234567", "ali@example.com", "9990001"):
        assert secret.lower() not in detail["transcript"].lower() and secret.lower() not in detail["summary"].lower()
    assert "[phone]" in detail["transcript"] and detail["transcript_removed"] is False

    await post(client, message("end-of-call-report", call="new", endedReason="customer-ended-call", cost=0.01, durationSeconds=30, summary="Recent call.", artifact={"transcript": "User: hello"}))
    await admin_conn.execute("UPDATE voice_calls SET started_at = now() - interval '10 days', ended_at = now() - interval '10 days' WHERE provider_call_id = 'old'")
    await automation_service.tick()
    after = {c["id"]: c for c in (await client.get(CALLS, headers=bearer(owner))).json()["items"]}
    old = (await client.get(f"{CALLS}/{stored['id']}", headers=bearer(owner))).json()
    assert old["transcript"] is None and old["summary"] is None and old["transcript_removed"] is True and old["duration_seconds"] == 30  # the record stays
    recent = next(c for c in after.values() if c["id"] != stored["id"])
    assert (await client.get(f"{CALLS}/{recent['id']}", headers=bearer(owner))).json()["transcript"] == "User: hello"
    assert await admin_conn.fetchval("SELECT count(*) FROM audit_logs WHERE action = 'voice.transcripts_purged' AND tenant_id = $1", uuid.UUID(owner["tenant_id"])) == 1


# -- settings (87) and the assistant to create in VAPI (67, 69) -----------------------------------------------------


async def test_settings_start_off_and_can_only_be_edited_by_the_owner(client: AsyncClient, app_engine: AsyncEngine, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    blank = (await client.get(SETTINGS, headers=bearer(owner))).json()
    assert (blank["configured"], blank["enabled"], blank["vapi_connected"], blank["retention_days"]) == (False, False, False, 30)
    assert blank["webhook_url"] == "https://api.bazaarflow.test/api/v1/webhooks/vapi" or blank["webhook_url"].endswith("/api/v1/webhooks/vapi")
    manager = await member(client, app_engine, owner, "manager")
    staff = await member(client, app_engine, owner, "staff")
    assert (await client.get(SETTINGS, headers=bearer(manager))).status_code == 200
    assert (await client.put(SETTINGS, json=settings_body(enabled=False), headers=bearer(manager))).status_code == 403
    assert (await client.get(SETTINGS, headers=bearer(staff))).status_code == 403
    assert (await client.get(SETTINGS)).status_code == 401
    for url in (CALLS, "/api/v1/voice/assistant-config"):
        assert (await client.get(url, headers=bearer(staff))).status_code == 403


async def test_it_cannot_be_switched_on_without_vapi(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    res = await client.put(SETTINGS, json=settings_body(), headers=bearer(owner))
    assert res.status_code == 409 and res.json()["code"] == "vapi_not_connected"
    assert (await client.put(SETTINGS, json=settings_body(enabled=False), headers=bearer(owner))).status_code == 200


@pytest.mark.parametrize(
    ("over", "field"),
    [
        ({"consent_notice": "short"}, "consent_notice"),
        ({"consent_notice": "n" * 301}, "consent_notice"),
        ({"greeting": "x"}, "greeting"),
        ({"max_call_seconds": 59}, "max_call_seconds"),
        ({"max_call_seconds": 901}, "max_call_seconds"),
        ({"monthly_cap_usd": "-1"}, "monthly_cap_usd"),
        ({"monthly_cap_usd": "501"}, "monthly_cap_usd"),
        ({"retention_days": 0}, "retention_days"),
        ({"retention_days": 366}, "retention_days"),
        ({"handoff_phone": "0300"}, "handoff_phone"),
        ({"surprise": 1}, "surprise"),
    ],
)
async def test_each_setting_rule_is_enforced(client: AsyncClient, providers: FakeProviders, over: dict[str, Any], field: str) -> None:
    owner = await register(client, "Shop A")
    await connect_vapi(client, owner)
    res = await client.put(SETTINGS, json=settings_body(**over), headers=bearer(owner))
    assert res.status_code == 422 and field in {e["field"] for e in res.json()["errors"]}


async def test_the_assistant_starts_with_the_consent_notice_can_be_interrupted_and_has_a_length_limit(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await ready_shop(client, max_call_seconds=240)
    body = (await client.get("/api/v1/voice/assistant-config", headers=bearer(owner))).json()
    assistant = body["assistant"]
    assert assistant["firstMessage"].startswith("This call may be recorded and transcribed") and "Hello, Ali Mart" in assistant["firstMessage"]
    assert assistant["firstMessageMode"] == "assistant-speaks-first" and assistant["maxDurationSeconds"] == 240
    assert assistant["stopSpeakingPlan"] == {"numWords": 2, "voiceSeconds": 0.2, "backoffSeconds": 1.0}
    assert assistant["server"]["url"].endswith("/api/v1/webhooks/vapi") and "tool-calls" in assistant["serverMessages"]
    names = [t["function"]["name"] for t in assistant["model"]["tools"] if t.get("type") == "function"]
    assert names == ["lookup_product", "order_status", "create_support_ticket", "transfer_to_human"]
    assert not any(t.get("type") == "transferCall" for t in assistant["model"]["tools"])
    assert "confirmed" in assistant["model"]["messages"][0]["content"] and "digit by digit" in assistant["model"]["messages"][0]["content"]
    assert any("silence timeout" in n for n in body["notes"]) and any("callback" in n for n in body["notes"])
    assert "webhook_secret" not in json.dumps(body) and VAPI_SECRET not in json.dumps(body)

    await client.put(SETTINGS, json=settings_body(handoff_phone="+923001234567"), headers=bearer(owner))
    with_handoff = (await client.get("/api/v1/voice/assistant-config", headers=bearer(owner))).json()["assistant"]
    transfer = next(t for t in with_handoff["model"]["tools"] if t.get("type") == "transferCall")
    assert transfer["destinations"][0]["number"] == "+923001234567"


# -- the list and isolation ---------------------------------------------------------------------------------------


async def test_a_shop_only_sees_its_own_calls_and_the_list_filters(client: AsyncClient, providers: FakeProviders) -> None:
    a = await ready_shop(client)
    b = await register(client, "Shop B")
    await post(client, message("status-update", call="x1", status="in-progress"))
    await post(client, message("end-of-call-report", call="x2", endedReason="customer-ended-call", cost=0.01, durationSeconds=5))
    assert (await client.get(CALLS, headers=bearer(a))).json()["total"] == 2
    assert (await client.get(CALLS, params={"status": "in_progress"}, headers=bearer(a))).json()["total"] == 1
    assert (await client.get(CALLS, params={"status": "weird"}, headers=bearer(a))).status_code == 422
    assert (await client.get(CALLS, headers=bearer(b))).json()["total"] == 0
    first = (await client.get(CALLS, headers=bearer(a))).json()["items"][0]["id"]
    assert (await client.get(f"{CALLS}/{first}", headers=bearer(b))).status_code == 404


# -- the recorded call set (33) ----------------------------------------------------------------------------------------


async def test_the_recorded_call_set_replays_offline_and_reports_task_success(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await ready_shop(client)
    await product(client, owner, "SHIRT", "2500.00", 7, name="Classic Shirt", cost="1800.00")
    await customer(client, owner, "+923001234567")
    await client.patch(f"/api/v1/customers/{(await client.get('/api/v1/customers/', headers=bearer(owner))).json()['items'][0]['id']}", json={"name": "Sara Khan"}, headers=bearer(owner))
    report = await voice_replay.run_set(uuid.UUID(owner["tenant_id"]), VAPI_ASSISTANT)
    assert report.total == 6, report.failures()
    assert report.failures() == [] and report.success_rate == 1.0
    assert providers.requests == []  # fully offline
