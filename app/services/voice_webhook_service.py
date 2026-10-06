"""What the shop's voice agent does when VAPI calls our server (PRD W-007, build-plan tasks 66-69, 91).

The caller and the shop come from the call itself, never from what the model says. The agent can read (a product's price
and stock, the caller's own latest orders) and take a message (a support ticket); it cannot change money or stock. A
support ticket is only created after the details have been read back and the caller agreed (``confirmed``): the first
call answers with the exact read-back (names, the number digit by digit, any date), a correction is just another
unconfirmed call with the new details, and the last call, with ``confirmed`` true, creates the ticket. A request to talk to
a person marks the call escalated with a note carrying the context, and either hands over (a handoff number is set) or
leaves a callback ticket. Each message is recorded by its provider id first, so a retry is answered without doing the work
twice. The stored transcript and summary are redacted before they are written.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.tenancy import Principal, tenant_session
from app.integrations.vapi import ToolCall, VoiceEvent
from app.models.conversation import WebhookEvent
from app.models.order import Order
from app.models.support import SupportTicket
from app.models.tenant import TenantRole
from app.models.voice import VoiceCall
from app.services import product_service, voice_service
from app.services.inbox_service import _customer_by_phone  # same phone matching as the inbox

logger = logging.getLogger("bazaarflow.voice")
VOICE_ACTOR = uuid.UUID("00000000-0000-0000-0000-00000000a4a4")
PROVIDER = "vapi"
_ERROR_WORDS = ("error", "failed", "fault")


def _hint(number: str | None) -> str | None:
    digits = "".join(ch for ch in (number or "") if ch.isdigit())
    return f"…{digits[-4:]}" if len(digits) >= 4 else None


def _spoken(text: str) -> str:
    """Read digits one by one ("0300" becomes "0 3 0 0") so a number is read back clearly."""
    return re.sub(r"\d+", lambda m: " ".join(m.group(0)), text)


def _truthy(value: Any) -> bool:
    return value is True or (isinstance(value, str) and value.strip().lower() in {"true", "yes", "1"})


async def _first_time(db: AsyncSession, tenant_id: uuid.UUID, event_id: str) -> bool:
    try:
        async with db.begin_nested():
            db.add(WebhookEvent(tenant_id=tenant_id, provider=PROVIDER, event_id=event_id[:120]))
            await db.flush()
    except IntegrityError:
        return False
    return True


async def _call(db: AsyncSession, tenant_id: uuid.UUID, event: VoiceEvent, status: str = "ringing") -> VoiceCall:
    call = (
        await db.execute(select(VoiceCall).where(VoiceCall.tenant_id == tenant_id, VoiceCall.provider_call_id == event.call_id).with_for_update())
    ).scalar_one_or_none()
    if call is None:
        row = await voice_service.get_row(db, tenant_id)
        call = VoiceCall(
            tenant_id=tenant_id,
            provider_call_id=event.call_id[:80],
            status=status,
            caller_hint=_hint(event.caller_number),
            started_at=datetime.now(timezone.utc),
            consent_notice=row.consent_notice if row else None,
            turns_json=[],
        )
        db.add(call)
        await db.flush()
    return call


# -- the tools ----------------------------------------------------------------------------------------------------


async def _lookup_product(db: AsyncSession, tenant_id: uuid.UUID, args: dict[str, Any]) -> str:
    query = str(args.get("query") or "").strip()[:80]
    if not query:
        return "Which product do you mean?"
    principal = Principal(user_id=VOICE_ACTOR, tenant_id=tenant_id, role=TenantRole.staff)  # staff view: no cost, no credit
    items, _total = await product_service.list_products(db, principal, q=query, category=None, active=True, low_stock=None, sort="name", limit=3, offset=0)
    if not items:
        return "I could not find that product."
    return " ".join(f"{p.name} is Rs {p.price:,.0f} and {p.qty_on_hand} in stock." if p.qty_on_hand > 0 else f"{p.name} is Rs {p.price:,.0f} but out of stock." for p in items)


async def _order_status(db: AsyncSession, tenant_id: uuid.UUID, event: VoiceEvent) -> str:
    if not event.caller_number:
        return "I cannot tell which number you are calling from, so I cannot look up an order."
    customer = await _customer_by_phone(db, tenant_id, event.caller_number)
    if customer is None:
        return "I could not find an order for this phone number."
    orders = (
        await db.execute(
            select(Order).where(Order.tenant_id == tenant_id, Order.customer_id == customer.id, Order.status.in_(("posted", "reversed"))).order_by(Order.created_at.desc()).limit(3)
        )
    ).scalars().all()
    if not orders:
        return "I could not find an order for this phone number."
    return " ".join(f"Your order of Rs {Decimal(o.total):,.0f} on {o.created_at.date().isoformat()} is {o.status}." for o in orders)


def _readback(args: dict[str, Any]) -> str:
    parts = [f"Contact: {_spoken(str(args.get('contact') or '').strip())}.", f"About: {str(args.get('issue_summary') or '').strip()}."]
    if str(args.get("details") or "").strip():
        parts.append(f"Details: {_spoken(str(args['details']).strip())}.")
    parts.append(f"Preferred way to reach them: {args.get('preferred_channel') or 'whatsapp'}.")
    return " ".join(parts)


async def _support_ticket(db: AsyncSession, tenant_id: uuid.UUID, call: VoiceCall, args: dict[str, Any]) -> str:
    contact = str(args.get("contact") or "").strip()
    summary = str(args.get("issue_summary") or "").strip()
    if len(contact) < 3 or len(summary) < 3:
        return "I still need the caller's name and number and what it is about. Ask for them."
    if not _truthy(args.get("confirmed")):
        return (
            "Read this back to the caller exactly, then ask 'Is that right?'. If anything is wrong, call this tool again with the corrected details and "
            f"confirmed false. Only after they say yes call it with confirmed true. {_readback(args)}"
        )
    channel = str(args.get("preferred_channel") or "whatsapp")
    ticket = SupportTicket(
        tenant_id=tenant_id,
        contact=contact[:255],
        issue_summary=summary[:500],
        details=str(args.get("details") or "").strip() or None,
        preferred_channel=channel if channel in {"whatsapp", "phone", "email"} else "whatsapp",
        status="open",
    )
    db.add(ticket)
    await db.flush()
    call.ticket_id = ticket.id
    record_audit(db, "voice.ticket_created", tenant_id=tenant_id, actor_type="agent", actor_id=VOICE_ACTOR, entity="support_ticket", entity_id=ticket.id, after={"call": str(call.id)})
    return f"Done. I have noted it for the shop. Your reference is {str(ticket.id)[:8].upper()}."


async def _transfer(db: AsyncSession, tenant_id: uuid.UUID, call: VoiceCall, event: VoiceEvent, args: dict[str, Any]) -> str:
    reason = str(args.get("reason") or "The caller asked for a person.").strip()[:300]
    call.escalated, call.status = True, "escalated"
    call.handoff_note = reason
    row = await voice_service.get_row(db, tenant_id)
    record_audit(db, "voice.escalated", tenant_id=tenant_id, actor_type="agent", actor_id=VOICE_ACTOR, entity="voice_call", entity_id=call.id, after={"reason": reason})
    if row is not None and row.handoff_phone:
        return "Tell the caller you are passing them to a person now, then transfer the call."
    ticket = SupportTicket(
        tenant_id=tenant_id,
        contact=(event.caller_number or "unknown caller")[:255],
        issue_summary=f"Callback requested: {reason}"[:500],
        details="The caller asked for a person and no handoff number is set.",
        preferred_channel="phone",
        status="open",
    )
    db.add(ticket)
    await db.flush()
    call.ticket_id = call.ticket_id or ticket.id
    return "No one can take the call right now. Tell the caller you have left a callback request and the shop will call them back."


async def _run_tool(db: AsyncSession, tenant_id: uuid.UUID, call: VoiceCall, event: VoiceEvent, tool: ToolCall) -> dict[str, str]:
    if not await _first_time(db, tenant_id, f"{event.call_id}:tool:{tool.id}"):
        return {"toolCallId": tool.id, "result": "That was already done."}
    try:
        if tool.name == "lookup_product":
            text = await _lookup_product(db, tenant_id, tool.arguments)
        elif tool.name == "order_status":
            text = await _order_status(db, tenant_id, event)
        elif tool.name == "create_support_ticket":
            text = await _support_ticket(db, tenant_id, call, tool.arguments)
        elif tool.name == "transfer_to_human":
            text = await _transfer(db, tenant_id, call, event, tool.arguments)
        else:
            return {"toolCallId": tool.id, "error": "I cannot do that."}
    except Exception:  # a tool failure is spoken as an apology, never a stack trace
        logger.exception("voice tool failed", extra={"tool": tool.name, "tenant_id": str(tenant_id)})
        return {"toolCallId": tool.id, "error": "Something went wrong. Offer to take a message."}
    return {"toolCallId": tool.id, "result": text}


# -- the messages -------------------------------------------------------------------------------------------------


async def assistant_request(tenant_id: uuid.UUID, assistant_id: str) -> dict[str, Any]:
    """Accept the call, or refuse it with a sentence the caller hears (the shop's voice agent is off, or its month's allowance is used)."""
    async with tenant_session(tenant_id) as db:
        row = await voice_service.get_row(db, tenant_id)
        if row is None or not row.enabled:
            return {"error": "Sorry, this line is not taking calls right now. Please message the shop on WhatsApp."}
        spent = await voice_service.month_spend_micros(db, tenant_id)
        if Decimal(spent) >= Decimal(row.monthly_cap_usd) * Decimal(1_000_000):
            return {"error": "Sorry, we cannot take calls on this line right now. Please message the shop on WhatsApp."}
    return {"assistantId": assistant_id}


_STATUS = {"ringing": "ringing", "queued": "ringing", "in-progress": "in_progress", "forwarding": "escalated"}


async def handle(tenant_id: uuid.UUID, event: VoiceEvent) -> dict[str, Any]:
    if event.type == "assistant-request":
        return await assistant_request(tenant_id, event.assistant_id)
    if not event.call_id:
        return {}
    async with tenant_session(tenant_id) as db:
        if event.type == "status-update":
            if not await _first_time(db, tenant_id, f"{event.call_id}:status:{event.status}"):
                return {}
            call = await _call(db, tenant_id, event, _STATUS.get(event.status or "", "ringing"))
            if event.status in _STATUS:
                if call.status not in {"escalated", "failed", "completed"} or event.status == "forwarding":
                    call.status = _STATUS[event.status]
                call.escalated = call.escalated or event.status == "forwarding"
            return {}
        if event.type == "tool-calls":
            call = await _call(db, tenant_id, event, "in_progress")
            if call.status == "ringing":
                call.status = "in_progress"
            results = [await _run_tool(db, tenant_id, call, event, t) for t in event.tool_calls]
            return {"results": results}
        if event.type == "end-of-call-report":
            if not await _first_time(db, tenant_id, f"{event.call_id}:report"):
                return {}
            call = await _call(db, tenant_id, event, "in_progress")
            now = datetime.now(timezone.utc)
            redactor = await voice_service.redactor_for(db, tenant_id, event.caller_number)
            call.ended_at = now
            call.duration_seconds = event.duration_seconds if event.duration_seconds is not None else max(int((now - call.started_at).total_seconds()), 0)
            call.ended_reason = (event.ended_reason or "")[:80] or None
            call.spend_micros = int(round((event.cost_usd or 0) * 1_000_000))
            call.turns_json = [{"latency_ms": v} for v in event.turn_latencies_ms]
            call.transcript = redactor.text(event.transcript) if event.transcript else None
            call.summary = redactor.text(event.summary) if event.summary else None
            if call.escalated:
                call.status = "escalated"
            elif any(w in (event.ended_reason or "").lower() for w in _ERROR_WORDS):
                call.status = "failed"
            else:
                call.status = "completed"
            record_audit(db, "voice.call_ended", tenant_id=tenant_id, actor_type="system", entity="voice_call", entity_id=call.id, after={"status": call.status, "seconds": call.duration_seconds})
            return {}
    return {}  # the other message types (transcripts, speech updates) are acknowledged and not stored
