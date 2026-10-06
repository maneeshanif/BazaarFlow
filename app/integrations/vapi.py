"""VAPI voice adapter (PRD I-004, build-plan task 91): parse a VAPI server message and check who sent it.

One instance serves one shop's assistant. VAPI calls our server URL with ``{"message": {"type": ..., "call": {...}}}``
(types used here: ``assistant-request``, ``status-update``, ``tool-calls``, ``end-of-call-report``) and authenticates
with the credential configured for that server URL: ``Authorization: Bearer <token>`` or the legacy ``X-Vapi-Secret``
header. A tool call is answered with ``{"results": [{"toolCallId": ..., "result": "<string>"}]}`` (or ``"error"``), always
HTTP 200. Verified against docs.vapi.ai (server-url/events, server-authentication, tools/custom-tools) on 2026-10-07.

Not verified without a live call, and marked so in the tests: the exact fields of ``end-of-call-report`` for cost and
per-turn latency (``cost`` / ``costs`` and ``artifact.performanceMetrics.turnLatencies``). The parser tolerates their
absence, so a call with different fields is recorded without latency rather than rejected.
"""

from __future__ import annotations

import hmac
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.integrations.http import ProviderClient, ProviderError, Sleep

BASE_URL = "https://api.vapi.ai"
CHANNEL = "vapi"


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class VoiceEvent:
    type: str
    call_id: str
    assistant_id: str
    caller_number: str | None
    status: str | None = None
    ended_reason: str | None = None
    transcript: str | None = None
    summary: str | None = None
    cost_usd: float | None = None
    duration_seconds: int | None = None
    turn_latencies_ms: list[int] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)


def _d(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _assistant_id(message: dict[str, Any]) -> str:
    call = _d(message.get("call"))
    nested = _d(call.get("assistant")).get("id")
    other = _d(message.get("assistant")).get("id")
    return str(call.get("assistantId") or nested or other or "")


def parse(body: bytes) -> VoiceEvent | None:
    """A provider-neutral view of one server message, or None when it is not a JSON message we can read."""
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    message = payload.get("message") if isinstance(payload, dict) else None
    if not isinstance(message, dict) or not isinstance(message.get("type"), str):
        return None
    call = _d(message.get("call"))
    artifact = _d(message.get("artifact"))
    metrics = _d(artifact.get("performanceMetrics"))
    latencies = [int(t["turnLatency"]) for t in metrics.get("turnLatencies", []) if isinstance(t, dict) and isinstance(t.get("turnLatency"), (int, float))]
    calls: list[ToolCall] = []
    for item in message.get("toolCallList", []) or []:
        function = item.get("function") if isinstance(item, dict) else None
        if isinstance(function, dict) and item.get("id") and function.get("name"):
            raw = function.get("arguments")
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except ValueError:
                    raw = {}
            calls.append(ToolCall(id=str(item["id"]), name=str(function["name"]), arguments=raw if isinstance(raw, dict) else {}))
    customer = _d(call.get("customer"))
    cost = message.get("cost", call.get("cost"))
    duration = message.get("durationSeconds", call.get("durationSeconds"))
    return VoiceEvent(
        type=str(message["type"]),
        call_id=str(call.get("id") or ""),
        assistant_id=_assistant_id(message),
        caller_number=str(customer["number"]) if customer.get("number") else None,
        status=str(message["status"]) if message.get("status") else None,
        ended_reason=str(message["endedReason"]) if message.get("endedReason") else None,
        transcript=str(artifact["transcript"]) if artifact.get("transcript") else (str(message["transcript"]) if isinstance(message.get("transcript"), str) else None),
        summary=str(message["summary"]) if message.get("summary") else (str(artifact["summary"]) if artifact.get("summary") else None),
        cost_usd=float(cost) if isinstance(cost, (int, float)) else None,
        duration_seconds=int(duration) if isinstance(duration, (int, float)) else None,
        turn_latencies_ms=latencies,
        tool_calls=calls,
    )


class VapiAdapter:
    channel = CHANNEL

    def __init__(
        self,
        assistant_id: str,
        webhook_secret: str,
        api_key: str = "",
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep | None = None,
        retries: int = 3,
        timeout: float = 10.0,
    ) -> None:
        self._assistant_id = assistant_id
        self._secret = webhook_secret
        self._api_key = api_key
        self._http = ProviderClient("vapi", BASE_URL, transport=transport, sleep=sleep, retries=retries, timeout=timeout)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def connect(self, tenant_id: uuid.UUID, credentials: dict[str, Any]) -> str:
        """With an API key, check the assistant exists; without one the shop uses webhook mode only. Returns the assistant id."""
        if self._api_key:
            response = await self._http.request("GET", f"/assistant/{self._assistant_id}", headers={"Authorization": f"Bearer {self._api_key}"})
            if str(response.json().get("id")) != self._assistant_id:
                raise ProviderError("vapi", "auth", "the API key does not belong to this assistant")
        return self._assistant_id

    def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        """Constant-time check of the bearer token (or the legacy X-Vapi-Secret header) VAPI sends with every message."""
        lowered = {k.lower(): v for k, v in headers.items()}
        supplied = lowered.get("x-vapi-secret", "")
        auth = lowered.get("authorization", "")
        if auth.lower().startswith("bearer "):
            supplied = supplied or auth[7:].strip()
        if not supplied or not self._secret:
            return False
        return hmac.compare_digest(supplied.encode(), self._secret.encode())
