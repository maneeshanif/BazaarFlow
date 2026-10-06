"""Replay recorded VAPI call sequences through the real voice webhook and report task success (build-plan task 33).

Each case in ``voice_golden_set.json`` is a list of server messages (the shape docs.vapi.ai documents) plus what must be
true afterwards: the call's status, what the tools said to the caller, whether a ticket exists, whether the call was
escalated, and what must not survive in the stored transcript. The cases run through ``voice_webhook_service.handle``
against a real database, so the tools, the read-back rule and the redaction are the real ones. No network, no API key.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from app.core.tenancy import tenant_session
from app.integrations.vapi import ToolCall, VoiceEvent
from app.models.support import SupportTicket
from app.models.voice import VoiceCall
from app.services import voice_webhook_service

GOLDEN_PATH = Path(__file__).resolve().parent / "voice_golden_set.json"


@dataclass
class CaseResult:
    id: str
    passed: bool
    failures: list[str] = field(default_factory=list)


@dataclass
class Report:
    results: list[CaseResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def success_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def failures(self) -> list[str]:
        return [f"{r.id}: {f}" for r in self.results for f in r.failures]


def load_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))["cases"]
    return cases


def _event(message: dict[str, Any], call_id: str, assistant_id: str, caller: str) -> VoiceEvent:
    tools = [ToolCall(id=t["id"], name=t["name"], arguments=t.get("arguments", {})) for t in message.get("tools", [])]
    return VoiceEvent(
        type=message["type"],
        call_id=call_id,
        assistant_id=assistant_id,
        caller_number=caller,
        status=message.get("status"),
        ended_reason=message.get("endedReason"),
        transcript=message.get("transcript"),
        summary=message.get("summary"),
        cost_usd=message.get("cost"),
        duration_seconds=message.get("durationSeconds"),
        turn_latencies_ms=list(message.get("turnLatencies", [])),
        tool_calls=tools,
    )


async def run_case(tenant_id: uuid.UUID, assistant_id: str, case: dict[str, Any]) -> CaseResult:
    call_id = f"eval-{case['id']}-{uuid.uuid4().hex[:8]}"
    said: list[str] = []
    errors: list[str] = []
    for message in case["messages"]:
        answer = await voice_webhook_service.handle(tenant_id, _event(message, call_id, assistant_id, case["caller"]))
        for result in answer.get("results", []):
            (errors if "error" in result else said).append(str(result.get("result") or result.get("error")))
    expect = case["expect"]
    failures: list[str] = []
    async with tenant_session(tenant_id) as db:
        call = (await db.execute(select(VoiceCall).where(VoiceCall.tenant_id == tenant_id, VoiceCall.provider_call_id == call_id))).scalar_one_or_none()
        if call is None:
            return CaseResult(case["id"], False, ["no call was recorded"])
        if "status" in expect and call.status != expect["status"]:
            failures.append(f"status {call.status!r}, wanted {expect['status']!r}")
        if "escalated" in expect and call.escalated != expect["escalated"]:
            failures.append(f"escalated {call.escalated}, wanted {expect['escalated']}")
        if "turns" in expect and len(call.turns_json) != expect["turns"]:
            failures.append(f"{len(call.turns_json)} turns recorded, wanted {expect['turns']}")
        if "ticket" in expect and (call.ticket_id is not None) != expect["ticket"]:
            failures.append(f"ticket linked {call.ticket_id is not None}, wanted {expect['ticket']}")
        if "tickets" in expect:
            count = (await db.execute(select(func.count()).select_from(SupportTicket).where(SupportTicket.tenant_id == tenant_id, SupportTicket.contact.like("Imran%")))).scalar_one()
            if count != expect["tickets"]:
                failures.append(f"{count} tickets, wanted {expect['tickets']}")
        if "ticket_contact" in expect and call.ticket_id is not None:
            contact = (await db.execute(select(SupportTicket.contact).where(SupportTicket.id == call.ticket_id))).scalar_one()
            if contact != expect["ticket_contact"]:
                failures.append(f"ticket contact {contact!r}, wanted {expect['ticket_contact']!r}")
        if "handoff_note_contains" in expect and expect["handoff_note_contains"] not in (call.handoff_note or ""):
            failures.append("the handoff note does not carry the reason")
        for needle in expect.get("transcript_not_contains", []):
            if needle.lower() in (call.transcript or "").lower():
                failures.append(f"the stored transcript still contains {needle!r}")
        for needle in expect.get("summary_not_contains", []):
            if needle.lower() in (call.summary or "").lower():
                failures.append(f"the stored summary still contains {needle!r}")
    spoken = " | ".join(said)
    for needle in expect.get("tool_results_contain", []):
        if needle.lower() not in spoken.lower():
            failures.append(f"no tool answer contains {needle!r}")
    for needle in expect.get("tool_errors_contain", []):
        if not any(needle.lower() in e.lower() for e in errors):
            failures.append(f"no tool error contains {needle!r}")
    return CaseResult(case["id"], not failures, failures)


async def run_set(tenant_id: uuid.UUID, assistant_id: str, cases: list[dict[str, Any]] | None = None) -> Report:
    return Report([await run_case(tenant_id, assistant_id, c) for c in (cases if cases is not None else load_cases())])
