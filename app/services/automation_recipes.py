"""The six launch recipes (PRD W-008). Each one is a function that finds its own work, does it once, and says what it did.

Every recipe is safe to run again and again: a message carries an idempotency key built from what it is about (an order, a
day, a customer's last message), an approval is not filed twice for the same thing, and a weekly post is only drafted once a
week. That is what lets the scheduler call them on every pass without thinking about timing, and lets a person press
"Run now" without sending anything twice.

Nothing here changes money or stock. A recipe either sends a plain notification (an order confirmation, the daily brief, an
alert to the owner) or files an approval (a vendor message, a payment reminder, a post) for a person to accept.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_runtime.marketing_writer import write_draft
from app.agents.context import ToolContext
from app.core.problems import DomainError
from app.core.tenancy import Principal
from app.integrations.http import ProviderError
from app.models.agent import ActionStatus, AgentAction
from app.models.automation import Automation
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.inventory import InventoryItem
from app.models.marketing import MarketingPost
from app.models.message import Message, MessageDirection
from app.models.order import Order, OrderItem
from app.models.payment import LedgerEntry
from app.models.product import Product
from app.models.tenant import Tenant, TenantRole
from app.models.vendor import Vendor
from app.schemas.marketing_studio import DraftRequest
from app.services import approvals, dashboard_service, integration_service
from app.services.report_service import SHOP_TZ

AUTOMATION_ACTOR = uuid.UUID("00000000-0000-0000-0000-00000000a3a3")
OVERDUE_DAYS = 14
UNANSWERED_MINUTES = 15
REMINDER_COOLDOWN = timedelta(days=7)
MAX_PER_RUN = 50


class RecipeError(Exception):
    """The recipe cannot do its job (a missing phone number, WhatsApp not connected). The message is shown to the owner."""


@dataclass
class Outcome:
    summary: str
    count: int  # things done; 0 means there was nothing to do and the run is not recorded


@dataclass(frozen=True)
class Recipe:
    key: str
    label: str
    description: str
    trigger: str
    requires: tuple[str, ...]  # integrations that must be connected before it can be switched on
    run: Callable[[AsyncSession, uuid.UUID, datetime], Awaitable[Outcome]]
    due: Callable[[datetime, datetime | None], bool]  # (now, last_run_at) -> should the scheduler call it now


def _local(now: datetime) -> datetime:
    return now.astimezone(SHOP_TZ)


def _principal(tenant_id: uuid.UUID, role: TenantRole) -> Principal:
    return Principal(user_id=AUTOMATION_ACTOR, tenant_id=tenant_id, role=role)


def _rs(value: Decimal) -> str:
    return f"Rs {value:,.0f}"


async def send_whatsapp(db: AsyncSession, tenant_id: uuid.UUID, phone: str, text: str, key: str) -> bool:
    """Send one WhatsApp message once. Returns False when this key was already sent; raises RecipeError when it cannot be."""
    existing = (await db.execute(select(Message).where(Message.tenant_id == tenant_id, Message.idempotency_key == key))).scalar_one_or_none()
    if existing is not None and existing.status in {"sent", "delivered"}:
        return False
    try:
        adapter = await integration_service.adapter_for(db, tenant_id, "whatsapp_twilio")
    except DomainError as error:
        raise RecipeError(error.detail) from error
    message = existing or Message(
        tenant_id=tenant_id,
        phone=phone,
        direction=MessageDirection.outbound,
        text=text,
        status="queued",
        sender="ai",
        idempotency_key=key,
    )
    if existing is None:
        db.add(message)
        await db.flush()
    try:
        result = await adapter.send(tenant_id, phone, text, idempotency_key=key)
    except ProviderError as error:
        message.status, message.error = "send_failed", "WhatsApp did not accept the message."
        await integration_service.record_failure(db, tenant_id, "whatsapp_twilio", error)
        await db.flush()
        raise RecipeError("WhatsApp did not accept the message. It will be tried again.") from error
    finally:
        await adapter.aclose()
    if not result.ok:
        message.status, message.error = "send_failed", (result.error or "Not delivered")[:200]
        await db.flush()
        raise RecipeError(message.error)
    message.status, message.error = "sent", None
    if result.provider_message_id:
        message.wa_message_id = result.provider_message_id
    await db.flush()
    return True


async def _owner_phone(db: AsyncSession, tenant_id: uuid.UUID) -> tuple[str, str]:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    if not tenant.owner_phone:
        raise RecipeError("Add your phone number in Settings -> Shop profile so alerts can reach you.")
    return tenant.owner_phone, tenant.name


async def _file_approval(db: AsyncSession, tenant_id: uuid.UUID, *, agent: str, tool: str, summary: str, payload: dict[str, Any]) -> bool:
    """File an approval unless an identical one is already waiting. Returns whether a new one was filed."""
    digest = approvals.payload_hash(payload)
    waiting = (
        await db.execute(
            select(AgentAction.id).where(
                AgentAction.tenant_id == tenant_id, AgentAction.status == ActionStatus.pending.value, AgentAction.payload_hash == digest
            )
        )
    ).first()
    if waiting is not None:
        return False
    await approvals.request_action(
        ToolContext(tenant_id=tenant_id, user_id=AUTOMATION_ACTOR, role=TenantRole.manager, session=db),
        agent=agent,
        tool=tool,
        summary=summary,
        payload=payload,
    )
    return True


# -- 1. low stock -> a drafted vendor message --------------------------------------------------------------------


async def low_stock_vendor_draft(db: AsyncSession, tenant_id: uuid.UUID, now: datetime) -> Outcome:
    rows = (
        await db.execute(
            select(Product, InventoryItem, Vendor)
            .join(InventoryItem, InventoryItem.product_id == Product.id)
            .outerjoin(Vendor, (Vendor.id == Product.vendor_id) & (Vendor.deleted_at.is_(None)))
            .where(
                Product.tenant_id == tenant_id,
                Product.deleted_at.is_(None),
                Product.active.is_(True),
                InventoryItem.reorder_level > 0,
                InventoryItem.qty_on_hand <= InventoryItem.reorder_level,
            )
            .order_by(Product.name)
        )
    ).all()
    by_vendor: dict[uuid.UUID, tuple[Vendor, list[tuple[Product, InventoryItem]]]] = {}
    no_phone = 0
    for product, inventory, vendor in rows:
        if vendor is None or not vendor.phone:
            no_phone += 1
            continue
        by_vendor.setdefault(vendor.id, (vendor, []))[1].append((product, inventory))
    filed = 0
    shop = (await db.execute(select(Tenant.name).where(Tenant.id == tenant_id))).scalar_one()
    for vendor, items in by_vendor.values():
        lines = [f"- {p.name}: {max(i.reorder_level * 2 - i.qty_on_hand, 1)} (we have {i.qty_on_hand})" for p, i in items]
        text = f"Hello {vendor.name}, this is {shop}. We are running low and would like to order:\n" + "\n".join(lines) + "\nPlease confirm availability and price."
        payload = {"phone": vendor.phone, "text": text, "vendor_id": str(vendor.id), "purpose": "reorder"}
        if await _file_approval(db, tenant_id, agent="automation", tool="send_whatsapp_message", summary=f"Send a reorder message to {vendor.name} ({len(items)} items)", payload=payload):
            filed += 1
    warning = f" {no_phone} low item(s) have no vendor phone number, so no message was drafted for them." if no_phone else ""
    return Outcome(f"Drafted {filed} vendor message(s) for approval.{warning}" if (filed or no_phone) else "Nothing is low on stock.", filed + no_phone)


# -- 2. new order -> WhatsApp confirmation ------------------------------------------------------------------------


async def new_order_confirmation(db: AsyncSession, tenant_id: uuid.UUID, now: datetime) -> Outcome:
    last = (await db.execute(select(Automation.last_run_at).where(Automation.tenant_id == tenant_id, Automation.key == "new_order_confirmation"))).scalar_one_or_none()
    # from where the last pass got to (with a little overlap; the message key makes a repeat harmless), never older than a day:
    # switching the recipe on does not message people about old orders
    since = max(last - timedelta(minutes=5), now - timedelta(hours=24)) if last else now
    rows = (
        await db.execute(
            select(Order, Customer)
            .join(Customer, Customer.id == Order.customer_id)
            .where(Order.tenant_id == tenant_id, Order.status == "posted", Order.created_at >= since, Customer.deleted_at.is_(None))
            .order_by(Order.created_at)
            .limit(MAX_PER_RUN)
        )
    ).all()
    sent = 0
    for order, customer in rows:
        name = f" {customer.name}" if customer.name else ""
        text = f"Thank you{name}! Your order of {_rs(order.total)} is confirmed."
        if await send_whatsapp(db, tenant_id, customer.phone, text, f"auto-order-{order.id}"):
            sent += 1
    return Outcome(f"Sent {sent} order confirmation(s).", sent)


# -- 3. daily 09:00 brief to the owner ----------------------------------------------------------------------------


async def daily_brief(db: AsyncSession, tenant_id: uuid.UUID, now: datetime) -> Outcome:
    local = _local(now)
    if local.hour < 9:
        return Outcome("Too early for the brief.", 0)
    phone, _shop = await _owner_phone(db, tenant_id)
    summary = await dashboard_service.summary(db, _principal(tenant_id, TenantRole.owner), "today", now=now)
    text = f"Good morning! Your business brief: {summary.briefing}" if summary.briefing else "Good morning!"
    sent = await send_whatsapp(db, tenant_id, phone, text, f"auto-brief-{local.date().isoformat()}")
    return Outcome("Sent today's brief to the owner." if sent else "Today's brief was already sent.", 1 if sent else 0)


# -- 4. weekly post from slow-moving stock ------------------------------------------------------------------------


async def weekly_slow_stock_post(db: AsyncSession, tenant_id: uuid.UUID, now: datetime) -> Outcome:
    local = _local(now)
    if local.weekday() != 0 or local.hour < 10:  # Monday morning
        return Outcome("Not Monday morning yet.", 0)
    week_start = datetime.combine(local.date(), datetime.min.time(), tzinfo=SHOP_TZ).astimezone(timezone.utc)
    done = (
        await db.execute(
            select(func.count()).select_from(MarketingPost).where(MarketingPost.tenant_id == tenant_id, MarketingPost.source == "automation", MarketingPost.created_at >= week_start)
        )
    ).scalar_one()
    if done:
        return Outcome("This week's post is already drafted.", 0)
    sold_recently = select(OrderItem.product_id).join(Order, Order.id == OrderItem.order_id).where(
        Order.tenant_id == tenant_id, Order.status == "posted", Order.created_at >= now - timedelta(days=30)
    )
    product = (
        await db.execute(
            select(Product)
            .join(InventoryItem, InventoryItem.product_id == Product.id)
            .where(Product.tenant_id == tenant_id, Product.deleted_at.is_(None), Product.active.is_(True), InventoryItem.qty_on_hand > 0, Product.id.not_in(sold_recently))
            .order_by(InventoryItem.qty_on_hand.desc(), Product.name)
            .limit(1)
        )
    ).scalar_one_or_none()
    if product is None:
        return Outcome("No slow-moving product this week.", 0)
    shop = (await db.execute(select(Tenant.name).where(Tenant.id == tenant_id))).scalar_one()
    principal = _principal(tenant_id, TenantRole.manager)
    draft = await write_draft(db, principal, shop=shop, brief=DraftRequest(goal="promote_product", product_id=product.id, tone="friendly"), product=product.name)
    post = MarketingPost(tenant_id=tenant_id, title=draft.title, message=draft.message, hashtags=draft.hashtags, status="pending_approval", source="automation")
    db.add(post)
    await db.flush()
    await approvals.request_action(
        ToolContext(tenant_id=tenant_id, user_id=AUTOMATION_ACTOR, role=TenantRole.manager, session=db),
        agent="automation",
        tool="approve_post",
        summary=f"Approve the weekly post about {product.name}",
        payload={"post_id": str(post.id), "title": post.title, "message": post.message, "hashtags": post.hashtags},
    )
    return Outcome(f"Drafted a post about {product.name} for approval.", 1)


# -- 5. overdue udhaar -> a polite reminder draft -----------------------------------------------------------------


async def overdue_udhaar_reminder(db: AsyncSession, tenant_id: uuid.UUID, now: datetime) -> Outcome:
    credits: dict[uuid.UUID, Decimal] = {
        party: Decimal(total)
        for party, total in (
            await db.execute(
                select(LedgerEntry.party_id, func.sum(LedgerEntry.amount))
                .where(LedgerEntry.tenant_id == tenant_id, LedgerEntry.party_type == "customer", LedgerEntry.direction == "credit")
                .group_by(LedgerEntry.party_id)
            )
        ).all()
    }
    debits = (
        await db.execute(
            select(LedgerEntry.party_id, LedgerEntry.amount, LedgerEntry.created_at)
            .where(LedgerEntry.tenant_id == tenant_id, LedgerEntry.party_type == "customer", LedgerEntry.direction == "debit")
            .order_by(LedgerEntry.created_at, LedgerEntry.id)
        )
    ).all()
    owed: dict[uuid.UUID, Decimal] = {}
    for party, amount, created_at in debits:  # payments clear the oldest credit first
        pay_down = min(Decimal(amount), credits.get(party, Decimal(0)))
        credits[party] = credits.get(party, Decimal(0)) - pay_down
        unpaid = Decimal(amount) - pay_down
        if unpaid > 0 and (now - created_at).days >= OVERDUE_DAYS:
            owed[party] = owed.get(party, Decimal(0)) + unpaid
    if not owed:
        return Outcome("Nobody is overdue.", 0)
    recent = (
        await db.execute(
            select(AgentAction.payload_json).where(
                AgentAction.tenant_id == tenant_id, AgentAction.tool == "send_whatsapp_message", AgentAction.created_at >= now - REMINDER_COOLDOWN
            )
        )
    ).scalars().all()
    reminded = {str(p.get("customer_id")) for p in recent if p.get("purpose") == "udhaar_reminder"}
    shop = (await db.execute(select(Tenant.name).where(Tenant.id == tenant_id))).scalar_one()
    customers = (
        await db.execute(select(Customer).where(Customer.tenant_id == tenant_id, Customer.id.in_(list(owed)), Customer.deleted_at.is_(None)).limit(MAX_PER_RUN))
    ).scalars().all()
    filed = 0
    for customer in customers:
        if str(customer.id) in reminded or not customer.phone:
            continue
        name = customer.name or "there"
        text = f"Assalam o Alaikum {name}, a gentle reminder from {shop}: {_rs(owed[customer.id])} is pending on your account. Thank you for your trust!"
        payload = {"phone": customer.phone, "text": text, "customer_id": str(customer.id), "purpose": "udhaar_reminder"}
        if await _file_approval(db, tenant_id, agent="automation", tool="send_whatsapp_message", summary=f"Send a payment reminder to {name} ({_rs(owed[customer.id])})", payload=payload):
            filed += 1
    return Outcome(f"Drafted {filed} payment reminder(s) for approval.", filed)


# -- 6. a customer message unanswered for 15 minutes -> alert the owner -------------------------------------------


async def unanswered_message_alert(db: AsyncSession, tenant_id: uuid.UUID, now: datetime) -> Outcome:
    cutoff = now - timedelta(minutes=UNANSWERED_MINUTES)
    waiting = (
        await db.execute(
            select(Conversation)
            .where(Conversation.tenant_id == tenant_id, Conversation.status != "resolved", Conversation.last_message_at <= cutoff, Conversation.last_message_at >= now - timedelta(days=2))
            .order_by(Conversation.last_message_at)
            .limit(MAX_PER_RUN)
        )
    ).scalars().all()
    to_alert: list[tuple[Conversation, Message]] = []
    for conversation in waiting:
        last = (
            await db.execute(
                select(Message).where(Message.tenant_id == tenant_id, Message.conversation_id == conversation.id).order_by(Message.created_at.desc(), Message.id.desc()).limit(1)
            )
        ).scalar_one_or_none()
        if last is not None and last.direction == MessageDirection.inbound:
            to_alert.append((conversation, last))
    if not to_alert:
        return Outcome("No customer is waiting.", 0)
    phone, _shop = await _owner_phone(db, tenant_id)
    sent = 0
    for conversation, last in to_alert:
        who = conversation.contact_name or conversation.phone
        text = f"A customer message has waited more than {UNANSWERED_MINUTES} minutes: {who}. Open the inbox to reply."
        if await send_whatsapp(db, tenant_id, phone, text, f"auto-alert-{last.id}"):
            sent += 1
    return Outcome(f"Alerted the owner about {sent} waiting message(s).", sent)


# -- the catalogue ------------------------------------------------------------------------------------------------


def _always(_now: datetime, _last: datetime | None) -> bool:
    return True


def _daily_at(hour: int) -> Callable[[datetime, datetime | None], bool]:
    def due(now: datetime, last: datetime | None) -> bool:
        local = _local(now)
        return local.hour >= hour and (last is None or _local(last).date() != local.date())

    return due


RECIPES: dict[str, Recipe] = {
    r.key: r
    for r in (
        Recipe("low_stock_vendor_draft", "Low stock: draft a vendor message", "Every night, drafts a reorder message to the vendor of each item that is running low. You approve it before anything is sent.", "nightly", (), low_stock_vendor_draft, _daily_at(2)),
        Recipe("new_order_confirmation", "New order: confirm on WhatsApp", "When a sale is posted for a customer with a phone number, sends them a confirmation.", "order_posted", ("whatsapp_twilio",), new_order_confirmation, _always),
        Recipe("daily_brief", "Daily 9 am business brief", "Sends you a short summary of yesterday and today on WhatsApp every morning.", "daily_09_00", ("whatsapp_twilio",), daily_brief, _daily_at(9)),
        Recipe("weekly_slow_stock_post", "Weekly post from slow-moving stock", "Every Monday, drafts a Facebook post about a product that has not sold for a month. You approve it first.", "weekly_monday", (), weekly_slow_stock_post, _always),
        Recipe("overdue_udhaar_reminder", "Overdue udhaar: payment reminder", "Drafts a polite reminder for each customer whose credit is over 14 days old. You approve each one; no customer is reminded twice in a week.", "daily_10_00", (), overdue_udhaar_reminder, _daily_at(10)),
        Recipe("unanswered_message_alert", "Unanswered message: alert me", "Tells you on WhatsApp when a customer message has waited more than 15 minutes.", "message_waiting", ("whatsapp_twilio",), unanswered_message_alert, _always),
    )
}
