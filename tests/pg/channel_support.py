"""Helpers for the channel tests: fake providers (no network), connected shops, and signed Twilio webhooks.

``FakeProviders`` answers every Twilio, Facebook and Pexels request from the recorded fixtures in
``tests/fixtures/providers`` and records what it was asked. A test overrides one endpoint with ``fake.on(key, *responses)``
(a response, or an exception to raise, per call; the last one repeats). The keys are:
twilio.account, twilio.send, fb.page, fb.feed, fb.photos, fb.comments, fb.reply, pexels.search.
"""

from __future__ import annotations

import re
import uuid
from typing import Any
from urllib.parse import parse_qsl, urlencode

import httpx
from httpx import AsyncClient
from twilio.request_validator import RequestValidator

from app.integrations import factory
from tests.pg.conftest import bearer
from tests.unit.provider_support import fixture_json

TWILIO_SID = "ACaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
TWILIO_TOKEN = "twilio-test-auth-token-0123456789"
PAGE_ID = "1234567890"
PAGE_TOKEN = "EAAB-test-page-access-token-for-shop"
WEBHOOK = "/api/v1/webhooks/twilio"
VAPI_ASSISTANT = "asst-0123456789abcdef"
VAPI_SECRET = "vapi-bearer-token-for-tests-0001"


class FakeProviders:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.overrides: dict[str, list[httpx.Response | Exception]] = {}

    def on(self, key: str, *responses: httpx.Response | Exception) -> None:
        self.overrides[key] = list(responses)

    def calls(self, key: str) -> list[httpx.Request]:
        return [r for r in self.requests if self._key(r) == key]

    @staticmethod
    def _key(request: httpx.Request) -> str:
        host, path, method = request.url.host, request.url.path, request.method
        if host == "api.twilio.com":
            return "twilio.send" if path.endswith("/Messages.json") else "twilio.account"
        if host == "graph.facebook.com":
            if path.endswith("/feed"):
                return "fb.feed"
            if path.endswith("/photos"):
                return "fb.photos"
            if path.endswith("/comments"):
                return "fb.reply" if method == "POST" else "fb.comments"
            return "fb.page"
        if host == "api.pexels.com":
            return "pexels.search"
        if host == "api.vapi.ai":
            return "vapi.assistant"
        return "unknown"

    def _default(self, key: str) -> httpx.Response:
        if key == "twilio.account":
            return httpx.Response(200, json=fixture_json("twilio_account_active.json"))
        if key == "twilio.send":
            return httpx.Response(201, json=fixture_json("twilio_message_created.json"))
        if key == "fb.page":
            return httpx.Response(200, json=fixture_json("fb_page.json"))
        if key == "fb.feed":
            return httpx.Response(200, json=fixture_json("fb_post_created.json"))
        if key == "fb.photos":
            return httpx.Response(200, json=fixture_json("fb_photo_created.json"))
        if key == "fb.comments":
            return httpx.Response(200, json=fixture_json("fb_comments.json"))
        if key == "fb.reply":
            return httpx.Response(200, json={"id": "2222222222_9999999999"})
        if key == "vapi.assistant":
            return httpx.Response(200, json={"id": VAPI_ASSISTANT, "name": "Shop phone assistant"})
        if key == "pexels.search":
            return httpx.Response(200, json=fixture_json("pexels_search.json"))
        return httpx.Response(404)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        key = self._key(request)
        queue = self.overrides.get(key)
        if not queue:
            return self._default(key)
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, Exception):
            raise item
        return item


def twilio_credentials(sid: str = TWILIO_SID, token: str = TWILIO_TOKEN) -> dict[str, str]:
    return {"account_sid": sid, "auth_token": token}


async def connect_twilio(client: AsyncClient, owner: dict[str, Any], sid: str = TWILIO_SID) -> dict[str, Any]:
    res = await client.put("/api/v1/integrations/whatsapp_twilio", json={"credentials": twilio_credentials(sid)}, headers=bearer(owner))
    assert res.status_code == 200, res.text
    body: dict[str, Any] = res.json()
    return body


async def connect_facebook(client: AsyncClient, owner: dict[str, Any]) -> dict[str, Any]:
    res = await client.put(
        "/api/v1/integrations/facebook", json={"credentials": {"page_id": PAGE_ID, "access_token": PAGE_TOKEN}}, headers=bearer(owner)
    )
    assert res.status_code == 200, res.text
    body: dict[str, Any] = res.json()
    return body


def twilio_form(sender: str = "+923001234567", text: str = "Do you have the blue shirt?", sid: str | None = None, account: str = TWILIO_SID) -> dict[str, str]:
    return {
        "SmsMessageSid": sid or f"SM{uuid.uuid4().hex}",
        "NumMedia": "0",
        "ProfileName": "Sara",
        "WaId": sender.lstrip("+"),
        "SmsStatus": "received",
        "Body": text,
        "To": "whatsapp:+14155238886",
        "AccountSid": account,
        "From": f"whatsapp:{sender}",
        "ApiVersion": "2010-04-01",
        **({"MessageSid": sid} if sid else {}),
    }


def signed_webhook(form: dict[str, str], token: str = TWILIO_TOKEN) -> tuple[bytes, dict[str, str]]:
    """The body and headers Twilio would send for ``form`` (the MessageSid is the SmsMessageSid unless given)."""
    form = {**form, "MessageSid": form.get("MessageSid", form["SmsMessageSid"])}
    url = factory.twilio_webhook_url()
    signature = RequestValidator(token).compute_signature(url, dict(parse_qsl(urlencode(form), keep_blank_values=True)))
    return urlencode(form).encode(), {"Content-Type": "application/x-www-form-urlencoded", "X-Twilio-Signature": signature}


async def post_webhook(client: AsyncClient, form: dict[str, str], token: str = TWILIO_TOKEN) -> httpx.Response:
    body, headers = signed_webhook(form, token)
    return await client.post(WEBHOOK, content=body, headers=headers)


def sid_of(form: dict[str, str]) -> str:
    return re.sub(r"\W", "", form["SmsMessageSid"])


async def connect_vapi(client: AsyncClient, owner: dict[str, Any], assistant: str = VAPI_ASSISTANT, secret: str = VAPI_SECRET) -> dict[str, Any]:
    res = await client.put(
        "/api/v1/integrations/vapi", json={"credentials": {"assistant_id": assistant, "webhook_secret": secret}}, headers=bearer(owner)
    )
    assert res.status_code == 200, res.text
    body: dict[str, Any] = res.json()
    return body
