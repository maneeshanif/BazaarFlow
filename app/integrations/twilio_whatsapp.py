"""Twilio WhatsApp channel adapter (PRD I-001, build-plan task 83; skill: integration-twilio-whatsapp).

One instance serves one shop: it holds that shop's Account SID, auth token and sender number, and the public URL of the
webhook Twilio calls (the signature covers that exact URL). All HTTP goes through ``ProviderClient`` (timeout, retries,
typed errors). Twilio has no idempotency key, so a send with a key this instance has already seen returns the first
result; the inbox also records the key in the database before calling, which covers a restart between retries.

Verified against Twilio's documentation on 2026-10-06: messages are created with ``POST /2010-04-01/Accounts/{sid}/Messages.json``
(form fields From, To, Body; 201 with ``sid`` and ``status``), WhatsApp addresses are ``whatsapp:+<number>``, and a
webhook carries ``X-Twilio-Signature``, which Twilio's own ``RequestValidator`` checks (the project skill forbids a
hand-written check). Error 63015 means the recipient has not joined the sandbox.

Tenant routing: every webhook carries ``AccountSid``, so a shop's ``external_id`` is its Account SID (a sandbox number is
shared by every tester, so it cannot route). The shop points its own Twilio sandbox at our webhook URL.
"""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import parse_qsl

import httpx
from twilio.request_validator import RequestValidator

from app.integrations.channels import InboundMessage, SendResult
from app.integrations.http import ProviderClient, ProviderError, Sleep

BASE_URL = "https://api.twilio.com"
SANDBOX_NUMBER = "+14155238886"
CHANNEL = "whatsapp_twilio"
SANDBOX_JOIN_ERROR = "63015"


def _wa(number: str) -> str:
    return number if number.startswith("whatsapp:") else f"whatsapp:{number}"


def _strip_wa(address: str) -> str:
    return address.removeprefix("whatsapp:")


class TwilioWhatsAppAdapter:
    channel = CHANNEL

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str = SANDBOX_NUMBER,
        *,
        webhook_url: str = "",
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep | None = None,
        retries: int = 3,
        timeout: float = 10.0,
    ) -> None:
        self._sid = account_sid
        self._token = auth_token
        self._from = from_number
        self._webhook_url = webhook_url
        self._http = ProviderClient("twilio", BASE_URL, transport=transport, sleep=sleep, retries=retries, timeout=timeout)
        self._sent: dict[str, SendResult] = {}

    async def aclose(self) -> None:
        await self._http.aclose()

    async def connect(self, tenant_id: uuid.UUID, credentials: dict[str, Any]) -> str:
        """Prove the credentials work (a free, read-only account lookup). Returns the Account SID, the webhook routing key."""
        response = await self._http.request("GET", f"/2010-04-01/Accounts/{self._sid}.json", auth=(self._sid, self._token))
        status = response.json().get("status")
        if status != "active":
            raise ProviderError("twilio", "auth", f"the Twilio account is {status or 'not active'}")
        return self._sid

    async def send(self, tenant_id: uuid.UUID, to: str, text: str, *, idempotency_key: str) -> SendResult:
        if idempotency_key in self._sent:
            return self._sent[idempotency_key]
        try:
            response = await self._http.request(
                "POST",
                f"/2010-04-01/Accounts/{self._sid}/Messages.json",
                auth=(self._sid, self._token),
                data={"From": _wa(self._from), "To": _wa(to), "Body": text},
            )
        except ProviderError as error:
            if error.code == SANDBOX_JOIN_ERROR:
                result = SendResult(
                    provider_message_id="",
                    ok=False,
                    error="not delivered: the recipient must first send the sandbox join code to the Twilio sandbox number",
                )
                self._sent[idempotency_key] = result
                return result
            raise
        result = SendResult(provider_message_id=str(response.json().get("sid", "")))
        self._sent[idempotency_key] = result
        return result

    async def receive(self, headers: dict[str, str], body: bytes) -> InboundMessage | None:
        """Parse Twilio's form-encoded webhook. Status callbacks (no Body) and empty messages are not inbound messages."""
        fields = dict(parse_qsl(body.decode("utf-8", errors="replace"), keep_blank_values=True))
        text = fields.get("Body", "").strip()
        if not fields.get("MessageSid") or not text or not fields.get("From", "").startswith("whatsapp:"):
            return None
        return InboundMessage(
            channel=CHANNEL,
            external_id=fields.get("AccountSid", ""),
            sender=_strip_wa(fields["From"]),
            text=text,
            provider_message_id=fields["MessageSid"],
        )

    def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        signature = {k.lower(): v for k, v in headers.items()}.get("x-twilio-signature", "")
        if not signature or not self._token or not self._webhook_url:
            return False
        params = dict(parse_qsl(body.decode("utf-8", errors="replace"), keep_blank_values=True))
        return bool(RequestValidator(self._token).validate(self._webhook_url, params, signature))
