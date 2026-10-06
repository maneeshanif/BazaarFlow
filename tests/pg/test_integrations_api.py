"""Tasks 59, 62 and 77 (F-018): per-shop integrations: connect with a check, encrypted and write-only credentials,
a refused token means "reconnect", an outage degrades visibly and leaves an alert."""

from __future__ import annotations

import logging
import uuid

import asyncpg
import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.tenancy import tenant_session
from app.integrations.http import ProviderError
from app.services import integration_service
from tests.pg.channel_support import (
    PAGE_ID,
    PAGE_TOKEN,
    TWILIO_SID,
    TWILIO_TOKEN,
    FakeProviders,
    connect_facebook,
    connect_twilio,
    twilio_credentials,
)
from tests.pg.conftest import bearer, member, register
from tests.unit.provider_support import fixture_json

pytestmark = pytest.mark.pg

URL = "/api/v1/integrations/"


async def test_the_owner_sees_every_provider_and_only_two_are_available(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    rows = (await client.get(URL, headers=bearer(owner))).json()
    assert [r["provider"] for r in rows] == ["whatsapp_twilio", "whatsapp_meta", "facebook", "instagram", "vapi"]
    assert {r["provider"] for r in rows if r["available"]} == {"whatsapp_twilio", "facebook"}
    assert all(r["status"] == "not_connected" and r["token_hint"] is None for r in rows)
    twilio = rows[0]
    assert twilio["webhook_url"] == "https://api.bazaarflow.test/api/v1/webhooks/twilio"


async def test_only_the_owner_can_use_integrations(client: AsyncClient, app_engine: AsyncEngine, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    for role in ("manager", "staff"):
        other = await member(client, app_engine, owner, role)
        assert (await client.get(URL, headers=bearer(other))).status_code == 403
        res = await client.put(f"{URL}whatsapp_twilio", json={"credentials": twilio_credentials()}, headers=bearer(other))
        assert res.status_code == 403
        assert (await client.delete(f"{URL}whatsapp_twilio", headers=bearer(other))).status_code == 403
    assert (await client.get(URL)).status_code == 401


async def test_connecting_twilio_checks_the_credentials_and_never_returns_them(
    client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection
) -> None:
    owner = await register(client, "Shop A")
    body = await connect_twilio(client, owner)
    assert body["status"] == "connected" and body["external_id"] == TWILIO_SID and body["reconnect_required"] is False
    assert body["token_hint"] == f"****{TWILIO_TOKEN[-4:]}" and body["connected_at"]
    assert TWILIO_TOKEN not in str(body) and "credentials" not in body
    listed = (await client.get(URL, headers=bearer(owner))).text
    assert TWILIO_TOKEN not in listed
    assert len(providers.calls("twilio.account")) == 1  # it really checked with the provider

    stored = await admin_conn.fetchval("SELECT credentials_enc FROM tenant_integrations WHERE tenant_id = $1", uuid.UUID(owner["tenant_id"]))
    assert stored and TWILIO_TOKEN not in stored and TWILIO_SID not in stored  # encrypted at rest
    audit = await admin_conn.fetch("SELECT after_json::text AS a FROM audit_logs WHERE action = 'integration.connected'")
    assert audit and all(TWILIO_TOKEN not in row["a"] for row in audit)


async def test_connecting_facebook_checks_the_page(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    body = await connect_facebook(client, owner)
    assert body["status"] == "connected" and body["external_id"] == PAGE_ID and body["token_hint"] == f"****{PAGE_TOKEN[-4:]}"
    assert PAGE_TOKEN not in str((await client.get(URL, headers=bearer(owner))).json())


async def test_a_token_that_belongs_to_another_page_is_refused(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    providers.on("fb.page", httpx.Response(200, json={"id": "999", "name": "Not yours"}))
    res = await client.put(
        f"{URL}facebook", json={"credentials": {"page_id": PAGE_ID, "access_token": PAGE_TOKEN}}, headers=bearer(owner)
    )
    assert res.status_code == 422 and res.json()["code"] == "credentials_rejected"
    assert (await client.get(URL, headers=bearer(owner))).json()[2]["status"] == "not_connected"


@pytest.mark.parametrize(
    ("credentials", "field"),
    [
        ({"account_sid": "nope", "auth_token": TWILIO_TOKEN}, "account_sid"),
        ({"account_sid": TWILIO_SID, "auth_token": "short"}, "auth_token"),
        ({"account_sid": TWILIO_SID}, "auth_token"),
        ({"account_sid": TWILIO_SID, "auth_token": TWILIO_TOKEN, "whatsapp_number": "03001234567"}, "whatsapp_number"),
        ({"account_sid": TWILIO_SID, "auth_token": TWILIO_TOKEN, "extra": "x"}, "extra"),
    ],
)
async def test_each_credential_rule_is_enforced_and_names_the_field(
    client: AsyncClient, providers: FakeProviders, credentials: dict[str, str], field: str
) -> None:
    owner = await register(client, "Shop A")
    res = await client.put(f"{URL}whatsapp_twilio", json={"credentials": credentials}, headers=bearer(owner))
    assert res.status_code == 422 and res.json()["code"] == "validation_failed"
    assert field in {e["field"] for e in res.json()["errors"]}
    assert providers.requests == []  # nothing reaches the provider until the shape is right


async def test_a_provider_that_is_not_built_yet_and_an_unknown_one_are_refused(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    vapi = await client.put(f"{URL}vapi", json={"credentials": {"api_key": "x" * 20}}, headers=bearer(owner))
    assert vapi.status_code == 422 and vapi.json()["code"] == "provider_not_available"
    assert (await client.put(f"{URL}carrier_pigeon", json={"credentials": {}}, headers=bearer(owner))).status_code == 404


async def test_wrong_credentials_are_refused_and_nothing_is_saved(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    providers.on("twilio.account", httpx.Response(401, json=fixture_json("twilio_error_20003.json")))
    res = await client.put(f"{URL}whatsapp_twilio", json={"credentials": twilio_credentials()}, headers=bearer(owner))
    assert res.status_code == 422 and res.json()["code"] == "credentials_rejected"
    assert TWILIO_TOKEN not in res.text
    assert (await client.get(URL, headers=bearer(owner))).json()[0]["status"] == "not_connected"


async def test_a_provider_outage_while_connecting_is_a_502_with_a_plain_message(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    providers.on("twilio.account", httpx.ReadTimeout("slow"))
    res = await client.put(f"{URL}whatsapp_twilio", json={"credentials": twilio_credentials()}, headers=bearer(owner))
    assert res.status_code == 502 and res.json()["code"] == "provider_unavailable"
    assert len(providers.calls("twilio.account")) == 3  # tried three times before giving up


async def test_the_same_twilio_account_cannot_serve_two_shops(client: AsyncClient, providers: FakeProviders) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    await connect_twilio(client, a)
    res = await client.put(f"{URL}whatsapp_twilio", json={"credentials": twilio_credentials()}, headers=bearer(b))
    assert res.status_code == 409 and res.json()["code"] == "already_connected"


async def test_disconnecting_wipes_the_credentials_and_frees_the_account(
    client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection
) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    await connect_twilio(client, a)
    gone = (await client.delete(f"{URL}whatsapp_twilio", headers=bearer(a))).json()
    assert gone["status"] == "revoked" and gone["external_id"] is None and gone["token_hint"] is None
    row = await admin_conn.fetchrow("SELECT credentials_enc, external_id FROM tenant_integrations WHERE tenant_id = $1", uuid.UUID(a["tenant_id"]))
    assert row is not None and row["credentials_enc"] is None and row["external_id"] is None
    assert (await connect_twilio(client, b))["status"] == "connected"  # the account is free for another shop
    await client.delete(f"{URL}whatsapp_twilio", headers=bearer(b))
    assert (await connect_twilio(client, a))["status"] == "connected"  # and the first shop can reconnect later


async def test_a_refused_token_moves_the_integration_to_error_with_a_reconnect_path(
    client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection
) -> None:
    owner = await register(client, "Shop A")
    await connect_facebook(client, owner)
    tid = uuid.UUID(owner["tenant_id"])
    async with tenant_session(tid) as db:
        await integration_service.record_failure(db, tid, "facebook", ProviderError("facebook", "auth", "token expired", status=400, code="190"))
    row = (await client.get(URL, headers=bearer(owner))).json()[2]
    assert row["status"] == "error" and row["reconnect_required"] is True and "Paste a new one" in row["last_error"]

    async with tenant_session(tid) as db:
        with pytest.raises(Exception) as caught:  # noqa: PT011 (DomainError)
            await integration_service.adapter_for(db, tid, "facebook")
    assert "reconnected" in str(caught.value)  # sends and posts stop until the owner reconnects

    again = await client.put(
        f"{URL}facebook", json={"credentials": {"page_id": PAGE_ID, "access_token": PAGE_TOKEN}}, headers=bearer(owner)
    )
    assert again.status_code == 200 and again.json()["status"] == "connected" and again.json()["reconnect_required"] is False
    alerts = await admin_conn.fetch("SELECT after_json->>'kind' AS kind FROM audit_logs WHERE action = 'integration.degraded' AND tenant_id = $1", tid)
    assert [a["kind"] for a in alerts] == ["auth"]  # the alert left an audit row


async def test_an_outage_keeps_the_integration_connected_but_records_the_error_and_an_alert(
    client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection, caplog: pytest.LogCaptureFixture
) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    tid = uuid.UUID(owner["tenant_id"])
    logging.getLogger("bazaarflow.integrations").disabled = False  # the migration fixture's fileConfig switches loggers off
    with caplog.at_level("ERROR", logger="bazaarflow.integrations"):
        async with tenant_session(tid) as db:
            await integration_service.record_failure(db, tid, "whatsapp_twilio", ProviderError("twilio", "timeout", "slow"))
    row = (await client.get(URL, headers=bearer(owner))).json()[0]
    assert row["status"] == "connected" and "not answering" in row["last_error"] and row["reconnect_required"] is False
    assert any(r.message == "integration degraded" and r.provider == "whatsapp_twilio" and r.kind == "timeout" for r in caplog.records)  # type: ignore[attr-defined]
    assert TWILIO_TOKEN not in caplog.text
    assert await admin_conn.fetchval("SELECT count(*) FROM audit_logs WHERE action = 'integration.degraded' AND tenant_id = $1", tid) == 1
    async with tenant_session(tid) as db:  # the next success clears the message
        await integration_service.record_success(db, tid, "whatsapp_twilio")
    assert (await client.get(URL, headers=bearer(owner))).json()[0]["last_error"] is None


async def test_a_shop_never_sees_another_shops_integrations(client: AsyncClient, providers: FakeProviders) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    await connect_twilio(client, a)
    seen = (await client.get(URL, headers=bearer(b))).json()[0]
    assert seen["status"] == "not_connected" and seen["external_id"] is None
