"""The unified inbox (PRD F-005, W-003): customer conversations on WhatsApp, the AI's replies, and a person taking over.

A customer is identified by their phone number on a channel. An inbound message finds or opens the conversation, is stored
once (the webhook has already dropped replays), and, while the conversation is in AI mode, is answered by the customer
agent. The agent answers prices and stock only; anything else is a handover: the conversation moves to ``human`` /
``needs_human`` and the customer gets a holding line. A person replying from the inbox takes the conversation over, and
from that moment the AI stays silent for it. A reply that cannot be sent is kept as ``send_failed`` with the reason and can be
retried; a provider that refuses the saved credential pauses sending and shows a banner until the owner reconnects.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_runtime import customer_agent
from app.core.audit import record_audit
from app.core.problems import DomainError, NotFound
from app.core.search import escape_like
from app.core.tenancy import Principal
from app.integrations.channels import InboundMessage
from app.integrations.http import ProviderError
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.message import Message, MessageDirection
from app.models.order import Order
from app.models.tenant import Membership, TenantIntegration, TenantRole
from app.schemas.inbox import (
    ContextPanel,
    ConversationDetail,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
    RecentOrder,
)
from app.services import integration_service, ledger_service

logger = logging.getLogger("bazaarflow.inbox")

CHANNEL = "whatsapp"
PROVIDER = "whatsapp_twilio"
PREVIEW = 160
THREAD_LIMIT = 200


def _digits(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit())


def _preview(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= PREVIEW else flat[: PREVIEW - 1] + "…"


async def _get(db: AsyncSession, tenant_id: uuid.UUID, conversation_id: uuid.UUID, *, lock: bool = False) -> Conversation:
    stmt = select(Conversation).where(Conversation.id == conversation_id, Conversation.tenant_id == tenant_id)
    if lock:
        stmt = stmt.with_for_update()
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise NotFound("Conversation")
    return row


async def _customer_by_phone(db: AsyncSession, tenant_id: uuid.UUID, phone: str) -> Customer | None:
    return (
        await db.execute(
            select(Customer)
            .where(
                Customer.tenant_id == tenant_id,
                Customer.deleted_at.is_(None),
                func.replace(Customer.phone, "+", "") == _digits(phone),
            )
            .limit(1)
        )
    ).scalar_one_or_none()


def _touch(conversation: Conversation, text: str, at: datetime | None = None) -> None:
    conversation.last_message_at = at or datetime.now(timezone.utc)
    conversation.last_message_text = _preview(text)


async def _deliver(db: AsyncSession, tenant_id: uuid.UUID, conversation: Conversation, message: Message, adapter: Any) -> None:
    """Send ``message`` and record what happened on it. A failure never raises: it becomes ``send_failed`` with the reason."""
    try:
        result = await adapter.send(
            tenant_id, conversation.phone, message.text or "", idempotency_key=message.idempotency_key or str(message.id)
        )
    except ProviderError as error:
        message.status = "send_failed"
        message.error = (
            "WhatsApp rejected the saved credential. Ask the owner to reconnect it."
            if error.needs_reconnect
            else "WhatsApp is not answering right now. You can retry this message."
        )
        await integration_service.record_failure(db, tenant_id, PROVIDER, error)
    else:
        if result.ok:
            message.status = "sent"
            if result.provider_message_id:
                message.wa_message_id = result.provider_message_id
            message.error = None
            await integration_service.record_success(db, tenant_id, PROVIDER)
        else:
            message.status = "send_failed"
            message.error = result.error or "WhatsApp did not deliver this message."
    await db.flush()


async def receive_inbound(
    db: AsyncSession, tenant_id: uuid.UUID, inbound: InboundMessage, *, contact_name: str | None = None
) -> tuple[Conversation, Message]:
    """Store one customer message, open or reopen its conversation. (The caller has already rejected a replayed event.)"""
    conversation = (
        await db.execute(
            select(Conversation)
            .where(Conversation.tenant_id == tenant_id, Conversation.channel == CHANNEL, Conversation.phone == inbound.sender)
            .with_for_update()
        )
    ).scalar_one_or_none()
    customer = await _customer_by_phone(db, tenant_id, inbound.sender)
    if conversation is None:
        conversation = Conversation(
            tenant_id=tenant_id, channel=CHANNEL, phone=inbound.sender, status="open", mode="ai", last_message_at=datetime.now(timezone.utc)
        )
        db.add(conversation)
    if contact_name and not conversation.contact_name:
        conversation.contact_name = contact_name[:120]
    if customer is not None:
        conversation.customer_id = customer.id
    await db.flush()  # a new conversation gets its id here
    message = Message(
        tenant_id=tenant_id,
        customer_id=customer.id if customer else None,
        conversation_id=conversation.id,
        phone=inbound.sender,
        direction=MessageDirection.inbound,
        text=inbound.text,
        status="received",
        wa_message_id=inbound.provider_message_id,
        sender="customer",
    )
    db.add(message)
    _touch(conversation, inbound.text)
    conversation.status = "ai_handling" if conversation.mode == "ai" else "needs_human"
    await db.flush()
    return conversation, message


async def answer_with_ai(db: AsyncSession, tenant_id: uuid.UUID, conversation: Conversation, inbound: Message) -> None:
    """While the thread is in AI mode, let the customer agent answer; hand over to a person when it cannot."""
    if conversation.mode != "ai":
        return
    reply = await customer_agent.run_customer_reply(
        db,
        tenant_id,
        conversation.id,
        inbound.text or "",
        contact_phone=conversation.phone,
        contact_name=conversation.contact_name,
    )
    adapter: Any = None
    try:
        adapter = await integration_service.adapter_for(db, tenant_id, PROVIDER)
    except DomainError:
        adapter = None  # cannot send at all: the thread still needs a person, and the inbox banner says why

    if reply.text and not reply.handover:
        out = Message(
            tenant_id=tenant_id,
            customer_id=conversation.customer_id,
            conversation_id=conversation.id,
            phone=conversation.phone,
            direction=MessageDirection.outbound,
            text=reply.text,
            status="queued",
            sender="ai",
            idempotency_key=f"ai-{inbound.id}",
        )
        db.add(out)
        await db.flush()
        if adapter is not None:
            try:
                await _deliver(db, tenant_id, conversation, out, adapter)
            finally:
                await adapter.aclose()
        else:
            out.status = "send_failed"
            out.error = "WhatsApp is not connected, so this reply was not sent."
        _touch(conversation, reply.text)
        if out.status == "send_failed":
            await _hand_to_person(db, tenant_id, conversation, "The AI's reply could not be sent.")
        record_audit(
            db,
            "inbox.ai_replied",
            tenant_id=tenant_id,
            actor_type="agent",
            actor_id=customer_agent.AI_ACTOR,
            entity="conversation",
            entity_id=conversation.id,
            after={"message_id": str(out.id), "status": out.status},
        )
        return

    # handover: stop the AI for this thread and tell the customer a person will reply
    why = {
        "paused": "The AI assistant is switched off for this shop.",
        "spend_limit": "The shop has used up its AI allowance for the month.",
        "failed": "The AI could not answer.",
        "step_limit": "The AI could not answer.",
        "no_model": "No AI model is configured.",
    }.get(reply.outcome, "The customer needs a person.")
    await _hand_to_person(db, tenant_id, conversation, why)
    holding = Message(
        tenant_id=tenant_id,
        customer_id=conversation.customer_id,
        conversation_id=conversation.id,
        phone=conversation.phone,
        direction=MessageDirection.outbound,
        text=customer_agent.HOLDING_MESSAGE,
        status="queued",
        sender="ai",
        idempotency_key=f"ai-holding-{inbound.id}",
    )
    db.add(holding)
    await db.flush()
    if adapter is not None:
        try:
            await _deliver(db, tenant_id, conversation, holding, adapter)
        finally:
            await adapter.aclose()
    else:
        holding.status = "send_failed"
        holding.error = "WhatsApp is not connected, so this message was not sent."
    _touch(conversation, customer_agent.HOLDING_MESSAGE)
    record_audit(
        db,
        "inbox.handover",
        tenant_id=tenant_id,
        actor_type="agent",
        actor_id=customer_agent.AI_ACTOR,
        entity="conversation",
        entity_id=conversation.id,
        after={"reason": why, "outcome": reply.outcome},
    )


async def _hand_to_person(db: AsyncSession, tenant_id: uuid.UUID, conversation: Conversation, note: str) -> None:
    conversation.mode = "human"
    conversation.status = "needs_human"
    conversation.handoff_note = note[:500]
    await db.flush()


# -- reads ---------------------------------------------------------------------------------------------------------


async def list_conversations(
    db: AsyncSession, principal: Principal, *, status: str | None, q: str | None, limit: int, offset: int
) -> tuple[list[ConversationOut], int]:
    conditions: list[Any] = [Conversation.tenant_id == principal.tenant_id]
    if status:
        conditions.append(Conversation.status == status)
    if q:
        like = f"%{escape_like(q.strip())}%"
        conditions.append(or_(Conversation.phone.ilike(like, escape="\\"), Conversation.contact_name.ilike(like, escape="\\")))
    total = (await db.execute(select(func.count()).select_from(Conversation).where(*conditions))).scalar_one()
    rows = (
        await db.execute(
            select(Conversation).where(*conditions).order_by(Conversation.last_message_at.desc(), Conversation.id).limit(limit).offset(offset)
        )
    ).scalars().all()
    return [ConversationOut.model_validate(r) for r in rows], int(total)


async def _notice(db: AsyncSession, tenant_id: uuid.UUID) -> str | None:
    row = (
        await db.execute(
            select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id, TenantIntegration.provider == PROVIDER)
        )
    ).scalar_one_or_none()
    if row is None or row.status in {"pending", "revoked"}:
        return "WhatsApp is not connected, so replies cannot be sent. Connect it in Settings -> Integrations."
    if row.status == "error":
        return "WhatsApp needs to be reconnected before replies can be sent. Open Settings -> Integrations."
    return row.last_error


async def get_conversation(db: AsyncSession, principal: Principal, conversation_id: uuid.UUID) -> ConversationDetail:
    conversation = await _get(db, principal.tenant_id, conversation_id)
    messages = (
        await db.execute(
            select(Message)
            .where(Message.tenant_id == principal.tenant_id, Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(THREAD_LIMIT)
        )
    ).scalars().all()
    customer = (
        await db.execute(select(Customer).where(Customer.id == conversation.customer_id, Customer.tenant_id == principal.tenant_id))
    ).scalar_one_or_none() if conversation.customer_id else None
    orders: list[RecentOrder] = []
    balance = None
    if customer is not None:
        found = (
            await db.execute(
                select(Order)
                .where(Order.tenant_id == principal.tenant_id, Order.customer_id == customer.id, Order.status.in_(("posted", "reversed")))
                .order_by(Order.created_at.desc())
                .limit(5)
            )
        ).scalars().all()
        orders = [RecentOrder(id=o.id, total=o.total, status=o.status, created_at=o.created_at) for o in found]
        if principal.role != TenantRole.staff:
            balance = await ledger_service.customer_balance(db, principal.tenant_id, customer.id)
    actions = ["Reply to the customer"]
    if conversation.mode == "ai":
        actions.insert(0, "Take over from the AI")
    if customer is None:
        actions.append("Add them as a customer")
    else:
        actions.append("Record a sale")
    if conversation.status != "resolved":
        actions.append("Mark as resolved")
    return ConversationDetail(
        conversation=ConversationOut.model_validate(conversation),
        messages=[_message_out(m) for m in reversed(messages)],
        context=ContextPanel(
            customer_name=customer.name if customer else conversation.contact_name,
            customer_phone=conversation.phone,
            balance=balance,
            recent_orders=orders,
            suggested_actions=actions,
        ),
        provider_notice=await _notice(db, principal.tenant_id),
    )


# -- writes --------------------------------------------------------------------------------------------------------


async def send_reply(
    db: AsyncSession, principal: Principal, conversation_id: uuid.UUID, text: str, idempotency_key: str | None
) -> MessageOut:
    """A person answers the customer. This takes the conversation over: the AI stays silent for it from now on."""
    conversation = await _get(db, principal.tenant_id, conversation_id, lock=True)
    key = idempotency_key or f"staff-{uuid.uuid4().hex}"
    existing = (
        await db.execute(select(Message).where(Message.tenant_id == principal.tenant_id, Message.idempotency_key == key))
    ).scalar_one_or_none()
    if existing is not None:  # the same click twice, or a retried request: return what was already done
        return _message_out(existing)
    adapter = await integration_service.adapter_for(db, principal.tenant_id, PROVIDER)  # refuses with a plain reason
    message = Message(
        tenant_id=principal.tenant_id,
        customer_id=conversation.customer_id,
        conversation_id=conversation.id,
        phone=conversation.phone,
        direction=MessageDirection.outbound,
        text=text,
        status="queued",
        sender="staff",
        sent_by=principal.user_id,
        idempotency_key=key,
    )
    try:
        async with db.begin_nested():
            db.add(message)
            await db.flush()
    except IntegrityError:
        existing = (
            await db.execute(select(Message).where(Message.tenant_id == principal.tenant_id, Message.idempotency_key == key))
        ).scalar_one()
        await adapter.aclose()
        return _message_out(existing)
    try:
        await _deliver(db, principal.tenant_id, conversation, message, adapter)
    finally:
        await adapter.aclose()
    conversation.mode = "human"
    conversation.status = "open"
    conversation.assigned_to = conversation.assigned_to or principal.user_id
    _touch(conversation, text)
    await db.flush()
    record_audit(
        db,
        "inbox.staff_replied",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="conversation",
        entity_id=conversation.id,
        after={"message_id": str(message.id), "status": message.status},
    )
    return _message_out(message)


def _message_out(m: Message) -> MessageOut:
    return MessageOut(
        id=m.id,
        direction=m.direction.value,
        sender=m.sender,  # type: ignore[arg-type]
        text=m.text,
        status=m.status or "delivered",
        error=m.error,
        created_at=m.created_at,
    )


async def retry_message(db: AsyncSession, principal: Principal, conversation_id: uuid.UUID, message_id: uuid.UUID) -> MessageOut:
    conversation = await _get(db, principal.tenant_id, conversation_id, lock=True)
    message = (
        await db.execute(
            select(Message).where(
                Message.id == message_id, Message.tenant_id == principal.tenant_id, Message.conversation_id == conversation.id
            )
        )
    ).scalar_one_or_none()
    if message is None:
        raise NotFound("Message")
    if message.status != "send_failed" or message.direction != MessageDirection.outbound:
        raise DomainError("Only a message that failed to send can be retried.", code="not_retryable")
    adapter = await integration_service.adapter_for(db, principal.tenant_id, PROVIDER)
    message.idempotency_key = f"{message.idempotency_key or message.id}-retry-{uuid.uuid4().hex[:8]}"
    try:
        await _deliver(db, principal.tenant_id, conversation, message, adapter)
    finally:
        await adapter.aclose()
    record_audit(
        db,
        "inbox.message_retried",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="conversation",
        entity_id=conversation.id,
        after={"message_id": str(message.id), "status": message.status},
    )
    return _message_out(message)


async def update_conversation(
    db: AsyncSession, principal: Principal, conversation_id: uuid.UUID, body: ConversationUpdate
) -> ConversationOut:
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise DomainError("Nothing to update", code="empty_update")
    conversation = await _get(db, principal.tenant_id, conversation_id, lock=True)
    before = {"mode": conversation.mode, "status": conversation.status, "assigned_to": str(conversation.assigned_to) if conversation.assigned_to else None}
    if body.mode is not None:
        conversation.mode = body.mode
        if body.mode == "human":  # switching to a person stops the AI at once
            conversation.status = "open" if conversation.status in {"ai_handling", "open"} else conversation.status
        else:
            conversation.status = "ai_handling"
            conversation.handoff_note = None
    if body.status is not None:
        conversation.status = body.status if body.status == "resolved" else ("ai_handling" if conversation.mode == "ai" else "open")
    if body.unassign:
        conversation.assigned_to = None
    elif body.assigned_to is not None:
        member = (
            await db.execute(
                select(Membership.id).where(Membership.tenant_id == principal.tenant_id, Membership.user_id == body.assigned_to)
            )
        ).first()
        if member is None:
            raise DomainError("That person is not part of your shop", code="not_a_member")
        conversation.assigned_to = body.assigned_to
    await db.flush()
    record_audit(
        db,
        "inbox.conversation_updated",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="conversation",
        entity_id=conversation.id,
        before=before,
        after={"mode": conversation.mode, "status": conversation.status, "assigned_to": str(conversation.assigned_to) if conversation.assigned_to else None},
    )
    return ConversationOut.model_validate(conversation)
