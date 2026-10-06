"""The shared provider client (tasks 59-62): timeouts, retries, error kinds, nothing secret in a message."""

from __future__ import annotations

import httpx
import pytest

from app.integrations.http import ProviderClient, ProviderError
from tests.unit.provider_support import Script, Sleeps, fixture_json, json_response


def client(script: Script, sleeps: Sleeps, retries: int = 3) -> ProviderClient:
    return ProviderClient("demo", "https://provider.test", transport=script.transport, sleep=sleeps, retries=retries)


async def test_a_success_returns_the_response_with_one_call() -> None:
    script = Script(httpx.Response(200, json={"ok": True}))
    async with client(script, Sleeps()) as http:
        response = await http.request("GET", "/ping")
    assert response.json() == {"ok": True} and len(script.requests) == 1


async def test_a_timeout_is_retried_then_reported_as_a_timeout() -> None:
    script = Script(httpx.ReadTimeout("slow"))
    sleeps = Sleeps()
    async with client(script, sleeps) as http:
        with pytest.raises(ProviderError) as caught:
            await http.request("GET", "/ping")
    assert caught.value.kind == "timeout" and len(script.requests) == 3 and len(sleeps.delays) == 2


async def test_a_server_error_is_retried_and_a_later_success_wins() -> None:
    script = Script(httpx.Response(503), httpx.Response(502), httpx.Response(200, json={"ok": True}))
    async with client(script, Sleeps()) as http:
        assert (await http.request("GET", "/ping")).json() == {"ok": True}
    assert len(script.requests) == 3


async def test_a_server_error_that_never_clears_is_a_server_error() -> None:
    script = Script(httpx.Response(500, json={"message": "boom"}))
    async with client(script, Sleeps()) as http:
        with pytest.raises(ProviderError) as caught:
            await http.request("GET", "/ping")
    assert caught.value.kind == "server" and caught.value.status == 500 and len(script.requests) == 3


async def test_a_refused_credential_is_not_retried_and_needs_a_reconnect() -> None:
    script = Script(json_response(401, "twilio_error_20003.json"))
    sleeps = Sleeps()
    async with client(script, sleeps) as http:
        with pytest.raises(ProviderError) as caught:
            await http.request("GET", "/ping")
    assert caught.value.kind == "auth" and caught.value.needs_reconnect and caught.value.code == "20003"
    assert len(script.requests) == 1 and sleeps.delays == []


async def test_facebook_token_code_190_is_auth_and_code_4_is_rate_limited() -> None:
    expired = Script(json_response(400, "fb_error_190.json"))
    async with client(expired, Sleeps()) as http:
        with pytest.raises(ProviderError) as caught:
            await http.request("GET", "/me")
    assert caught.value.kind == "auth" and len(expired.requests) == 1
    throttled = Script(json_response(400, "fb_error_rate_4.json"), httpx.Response(200, json={"ok": True}))
    async with client(throttled, Sleeps()) as http:
        assert (await http.request("GET", "/me")).json() == {"ok": True}
    assert len(throttled.requests) == 2


async def test_a_429_waits_for_retry_after_and_then_succeeds() -> None:
    script = Script(httpx.Response(429, headers={"Retry-After": "2"}), httpx.Response(200, json={"ok": True}))
    sleeps = Sleeps()
    async with client(script, sleeps) as http:
        assert (await http.request("GET", "/ping")).json() == {"ok": True}
    assert sleeps.delays == [2.0]


async def test_retry_after_is_capped_so_a_provider_cannot_stall_a_request_for_minutes() -> None:
    script = Script(httpx.Response(429, headers={"Retry-After": "3600"}), httpx.Response(200, json={}))
    sleeps = Sleeps()
    async with client(script, sleeps) as http:
        await http.request("GET", "/ping")
    assert sleeps.delays == [30.0]


async def test_a_plain_client_error_is_reported_without_a_retry() -> None:
    script = Script(httpx.Response(400, json={"message": "bad number", "code": 21211}))
    async with client(script, Sleeps()) as http:
        with pytest.raises(ProviderError) as caught:
            await http.request("POST", "/send")
    assert caught.value.kind == "client" and caught.value.code == "21211" and len(script.requests) == 1


async def test_an_unreachable_provider_is_a_network_error() -> None:
    script = Script(httpx.ConnectError("down"))
    async with client(script, Sleeps(), retries=2) as http:
        with pytest.raises(ProviderError) as caught:
            await http.request("GET", "/ping")
    assert caught.value.kind == "network" and len(script.requests) == 2


async def test_an_error_message_never_contains_the_secret_that_was_sent() -> None:
    script = Script(httpx.Response(401, json=fixture_json("twilio_error_20003.json")))
    async with client(script, Sleeps()) as http:
        with pytest.raises(ProviderError) as caught:
            await http.request("GET", "/ping", auth=("ACaaaa", "super-secret-token"))
    assert "super-secret-token" not in str(caught.value) and "super-secret-token" not in caught.value.message
