"""Twilio WhatsApp sandbox smoke check (build-plan task 26; skill: .claude/skills/integration-twilio-whatsapp).

Two things only: prove the credentials work (a free, read-only account lookup) and, on request, send one sandbox
message. Plain HTTPS calls: the production channel adapter (phase 2) is a separate piece. Secrets are never printed
or returned; errors name the variable, not the value.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

SANDBOX_NUMBER = "+14155238886"  # shared by every sandbox user (Twilio docs, read 2026-10-03)
BASE_URL = "https://api.twilio.com"
JOIN_HINT = "the recipient must first send 'join <your sandbox code>' to the sandbox number (Twilio error 63015)"


class TwilioNotConfigured(RuntimeError):
    """A required variable is empty. Names only, never values."""


@dataclass(frozen=True)
class SmokeResult:
    ok: bool
    detail: str


def mask(value: str) -> str:
    if not value:
        return "(not set)"
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:2]}…{value[-2:]}"


def _require(sid: str, token: str) -> None:
    missing = [name for name, value in (("TWILIO_ACCOUNT_SID", sid), ("TWILIO_AUTH_TOKEN", token)) if not value]
    if missing:
        raise TwilioNotConfigured(f"set {' and '.join(missing)} in your environment")


async def check_account(client: httpx.AsyncClient | None, sid: str, token: str) -> SmokeResult:
    _require(sid, token)
    assert client is not None
    try:
        response = await client.get(f"/2010-04-01/Accounts/{sid}.json", auth=(sid, token), timeout=15)
    except httpx.HTTPError:
        return SmokeResult(False, "Twilio is unreachable from here")
    if response.status_code != 200:
        return SmokeResult(False, f"Twilio rejected the credentials (HTTP {response.status_code})")
    status = response.json().get("status")
    return SmokeResult(status == "active", f"account {status}")


async def send_sandbox_message(client: httpx.AsyncClient, sid: str, token: str, *, to: str, body: str) -> SmokeResult:
    _require(sid, token)
    try:
        response = await client.post(
            f"/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, token),
            data={"From": f"whatsapp:{SANDBOX_NUMBER}", "To": f"whatsapp:{to}", "Body": body},
            timeout=15,
        )
    except httpx.HTTPError:
        return SmokeResult(False, "Twilio is unreachable from here")
    if response.status_code in (200, 201):
        return SmokeResult(True, f"message {response.json().get('status', 'sent')}")
    code = (
        response.json().get("code") if response.headers.get("content-type", "").startswith("application/json") else None
    )
    if code == 63015:
        return SmokeResult(False, f"not delivered: {JOIN_HINT}")
    return SmokeResult(False, f"Twilio refused the message (HTTP {response.status_code}, code {code})")
