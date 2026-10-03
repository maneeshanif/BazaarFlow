"""Task 26: the Twilio sandbox smoke check. It must prove credentials work, send only on request, and never print
or store a secret."""

from __future__ import annotations

import httpx
import pytest

from app.integrations.twilio_sandbox import (
    SANDBOX_NUMBER,
    SmokeResult,
    TwilioNotConfigured,
    check_account,
    mask,
    send_sandbox_message,
)

SID = "AC" + "a" * 32
TOKEN = "t" * 32


def _client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler, base_url="https://api.twilio.com")


async def test_check_account_succeeds_with_valid_credentials() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, json={"sid": SID, "status": "active", "friendly_name": "BazaarFlow"})

    async with _client(httpx.MockTransport(handler)) as client:
        result = await check_account(client, SID, TOKEN)
    assert result == SmokeResult(ok=True, detail="account active")
    assert seen["path"] == f"/2010-04-01/Accounts/{SID}.json"
    assert seen["auth"].startswith("Basic ")


async def test_check_account_reports_bad_credentials_without_leaking_them() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"code": 20003, "message": "Authenticate"})

    async with _client(httpx.MockTransport(handler)) as client:
        result = await check_account(client, SID, TOKEN)
    assert result.ok is False
    assert TOKEN not in result.detail and SID not in result.detail
    assert "401" in result.detail


async def test_a_suspended_account_is_not_ok() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "suspended"})

    async with _client(httpx.MockTransport(handler)) as client:
        assert (await check_account(client, SID, TOKEN)).ok is False


async def test_network_failure_is_a_result_not_a_crash() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    async with _client(httpx.MockTransport(handler)) as client:
        result = await check_account(client, SID, TOKEN)
    assert result.ok is False and "unreachable" in result.detail


async def test_sending_uses_the_sandbox_sender_and_whatsapp_prefixes() -> None:
    sent: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(dict(pair.split("=", 1) for pair in request.content.decode().split("&")))
        return httpx.Response(201, json={"sid": "SM" + "b" * 32, "status": "queued"})

    async with _client(httpx.MockTransport(handler)) as client:
        result = await send_sandbox_message(client, SID, TOKEN, to="+923001234567", body="hello")
    assert result.ok
    assert sent["From"] == f"whatsapp%3A{SANDBOX_NUMBER.replace('+', '%2B')}"
    assert sent["To"] == "whatsapp%3A%2B923001234567"


async def test_sending_to_a_number_that_has_not_joined_the_sandbox_explains_why() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"code": 63015, "message": "not joined"})

    async with _client(httpx.MockTransport(handler)) as client:
        result = await send_sandbox_message(client, SID, TOKEN, to="+923001234567", body="hello")
    assert not result.ok and "join" in result.detail.lower()


async def test_missing_credentials_are_reported_by_name_only() -> None:
    with pytest.raises(TwilioNotConfigured) as raised:
        await check_account(None, "", "")
    assert "TWILIO_ACCOUNT_SID" in str(raised.value) and "TWILIO_AUTH_TOKEN" in str(raised.value)


def test_mask_hides_all_but_the_edges() -> None:
    assert mask(TOKEN) == "tt…tt"
    assert mask("") == "(not set)"
    assert mask("abc") == "***"
