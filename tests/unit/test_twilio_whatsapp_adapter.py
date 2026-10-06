"""Task 83: the Twilio WhatsApp adapter against recorded responses (happy path, timeout, error, duplicate delivery)."""

from __future__ import annotations

import uuid
from urllib.parse import parse_qsl

import httpx
import pytest
from twilio.request_validator import RequestValidator

from app.integrations.channels import ChannelAdapter
from app.integrations.http import ProviderError
from app.integrations.twilio_whatsapp import SANDBOX_NUMBER, TwilioWhatsAppAdapter
from tests.unit.provider_support import Script, Sleeps, fixture_text, json_response

SID = "ACaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
TOKEN = "twilio-test-auth-token"
URL = "https://api.bazaarflow.test/api/v1/webhooks/twilio"
TENANT = uuid.uuid4()


def adapter(script: Script, sleeps: Sleeps | None = None) -> TwilioWhatsAppAdapter:
    return TwilioWhatsAppAdapter(SID, TOKEN, SANDBOX_NUMBER, webhook_url=URL, transport=script.transport, sleep=sleeps or Sleeps())


def signed(body: str) -> dict[str, str]:
    signature = RequestValidator(TOKEN).compute_signature(URL, dict(parse_qsl(body, keep_blank_values=True)))
    return {"X-Twilio-Signature": signature}


def test_it_implements_the_channel_adapter_interface() -> None:
    assert isinstance(adapter(Script()), ChannelAdapter)


async def test_connect_proves_the_credentials_and_returns_the_account_sid_as_the_routing_key() -> None:
    script = Script(json_response(200, "twilio_account_active.json"))
    assert await adapter(script).connect(TENANT, {}) == SID
    request = script.requests[0]
    assert request.method == "GET" and request.url.path == f"/2010-04-01/Accounts/{SID}.json"
    assert request.headers["authorization"].startswith("Basic ")


async def test_connect_refuses_a_suspended_account() -> None:
    with pytest.raises(ProviderError) as caught:
        await adapter(Script(json_response(200, "twilio_account_suspended.json"))).connect(TENANT, {})
    assert caught.value.kind == "auth" and "suspended" in caught.value.message


async def test_connect_with_a_wrong_token_is_an_auth_error_that_names_no_secret() -> None:
    with pytest.raises(ProviderError) as caught:
        await adapter(Script(json_response(401, "twilio_error_20003.json"))).connect(TENANT, {})
    assert caught.value.needs_reconnect and TOKEN not in str(caught.value)


async def test_send_posts_a_whatsapp_message_and_returns_twilios_message_id() -> None:
    script = Script(json_response(201, "twilio_message_created.json"))
    result = await adapter(script).send(TENANT, "+923001234567", "Your order is ready", idempotency_key="k1")
    assert result.ok and result.provider_message_id == "SM5ef8f4f1c0a14e5da0c8f3f8c3f1d3a1"
    request = script.requests[0]
    assert request.method == "POST" and request.url.path == f"/2010-04-01/Accounts/{SID}/Messages.json"
    form = dict(parse_qsl(request.content.decode()))
    assert form == {"From": f"whatsapp:{SANDBOX_NUMBER}", "To": "whatsapp:+923001234567", "Body": "Your order is ready"}


async def test_a_duplicate_send_with_the_same_key_reaches_the_provider_once() -> None:
    script = Script(json_response(201, "twilio_message_created.json"))
    wa = adapter(script)
    first = await wa.send(TENANT, "+923001234567", "Hello", idempotency_key="same")
    second = await wa.send(TENANT, "+923001234567", "Hello", idempotency_key="same")
    assert first == second and len(script.requests) == 1


async def test_a_timeout_is_retried_three_times_then_raised() -> None:
    script = Script(httpx.ReadTimeout("slow"))
    sleeps = Sleeps()
    with pytest.raises(ProviderError) as caught:
        await adapter(script, sleeps).send(TENANT, "+923001234567", "Hello", idempotency_key="k")
    assert caught.value.kind == "timeout" and len(script.requests) == 3 and len(sleeps.delays) == 2


async def test_a_429_and_a_5xx_are_retried_until_one_succeeds() -> None:
    script = Script(httpx.Response(429, headers={"Retry-After": "1"}), httpx.Response(503), json_response(201, "twilio_message_created.json"))
    result = await adapter(script).send(TENANT, "+923001234567", "Hello", idempotency_key="k")
    assert result.ok and len(script.requests) == 3


async def test_a_recipient_who_has_not_joined_the_sandbox_is_a_failed_result_not_an_exception() -> None:
    script = Script(json_response(400, "twilio_error_63015.json"))
    result = await adapter(script).send(TENANT, "+923001234567", "Hello", idempotency_key="k")
    assert result.ok is False and "join" in (result.error or "") and len(script.requests) == 1


async def test_a_refused_credential_on_send_raises_and_is_not_retried() -> None:
    script = Script(json_response(401, "twilio_error_20003.json"))
    with pytest.raises(ProviderError) as caught:
        await adapter(script).send(TENANT, "+923001234567", "Hello", idempotency_key="k")
    assert caught.value.needs_reconnect and len(script.requests) == 1


async def test_an_inbound_webhook_becomes_a_provider_neutral_message() -> None:
    body = fixture_text("twilio_inbound_webhook.txt")
    message = await adapter(Script()).receive(signed(body), body.encode())
    assert message is not None
    assert (message.channel, message.external_id, message.sender) == ("whatsapp_twilio", SID, "+923001234567")
    assert message.text == "Do you have the blue shirt?" and message.provider_message_id == "SM1111111111111111111111111111111"


async def test_a_status_callback_is_not_an_inbound_message() -> None:
    body = fixture_text("twilio_status_callback.txt")
    assert await adapter(Script()).receive(signed(body), body.encode()) is None


def test_a_good_signature_passes_and_a_bad_or_missing_one_is_rejected() -> None:
    wa = adapter(Script())
    body = fixture_text("twilio_inbound_webhook.txt").encode()
    assert wa.verify_webhook(signed(body.decode()), body) is True
    assert wa.verify_webhook({"X-Twilio-Signature": "AAAA"}, body) is False
    assert wa.verify_webhook({}, body) is False
    tampered = body.replace(b"blue", b"red")
    assert wa.verify_webhook(signed(body.decode()), tampered) is False


def test_a_signature_made_for_another_url_or_token_is_rejected() -> None:
    body = fixture_text("twilio_inbound_webhook.txt")
    params = dict(parse_qsl(body, keep_blank_values=True))
    other_url = RequestValidator(TOKEN).compute_signature("https://evil.test/webhook", params)
    other_token = RequestValidator("another-token").compute_signature(URL, params)
    wa = adapter(Script())
    assert wa.verify_webhook({"X-Twilio-Signature": other_url}, body.encode()) is False
    assert wa.verify_webhook({"X-Twilio-Signature": other_token}, body.encode()) is False
