"""The sales agent's tools on the shop's own data (PRD §36.4, §36.10; build-plan tasks 29, 37, 63).

Every tool takes the shop, the user and the role from the run context, never from the model, and every call passes the
permission gate (``authorize_call``) first. Reads answer straight away. A tool that changes money or stock is only ever
*proposed*: it files an approval for a manager or owner and returns, and nothing changes until it is approved (unless
the shop has set an auto-post limit above zero and the sale is under it; the default is zero, so always ask).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Awaitable, Callable
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from agents import RunContextWrapper, function_tool
from pydantic import BaseModel, ValidationError
from sqlalchemy import select

from app.agent_runtime.context import ProposedAction, RuntimeContext, TraceStep
from app.agents.tools import manifest as _manifest  # noqa: F401  (importing it registers every tool declaration)
from app.agents.tools.catalog import ApprovalRequired, UnknownToolError, authorize_call
from app.core.problems import DomainError
from app.core.settings import settings
from app.models.agent import ActionStatus, AgentAction
from app.schemas.order import SaleCreate, SaleLine, SalePreviewRequest
from app.services import approvals, customer_service, ledger_service, order_service, product_service, report_service

Ctx = RunContextWrapper[RuntimeContext]
Handler = Callable[[RuntimeContext, bool], Awaitable[str]]

# What was drafted in each conversation, so a sale can only be posted after the person has seen its summary.
_DRAFTS: dict[str, set[str]] = {}


def forget_drafts(session_id: str) -> None:
    _DRAFTS.pop(session_id, None)


def _rs(value: Decimal) -> str:
    return f"Rs {value:,.2f}"


def _finish(rc: RuntimeContext, name: str, args: dict[str, Any], result: str, *, ok: bool) -> str:
    rc.steps.append(TraceStep(tool=name, arguments=args, result=result, ok=ok))
    return result


async def _run(wrapper: Ctx, name: str, args: dict[str, Any], handler: Handler) -> str:
    """The permission gate, then the tool in its own savepoint so a failure leaves nothing half done."""
    rc = wrapper.context
    if len(rc.steps) >= settings.AGENT_MAX_TOOL_CALLS:  # PRD 36.18: a run may not loop on tools
        return _finish(rc, name, args, "Too many tool calls in one request. Stop and tell the user what is done so far.", ok=False)
    direct = True
    try:
        authorize_call(name, rc.tool_context())
    except ApprovalRequired:
        direct = False  # a write: the handler may only propose it
    except (PermissionError, UnknownToolError) as exc:
        return _finish(rc, name, args, f"Not allowed: {exc}. Tell the user you cannot do that for them.", ok=False)
    try:
        async with rc.db.begin_nested():
            result = await handler(rc, direct)
    except DomainError as exc:
        return _finish(rc, name, args, f"That did not work: {exc.detail}", ok=False)
    return _finish(rc, name, args, result, ok=True)


def _uuid(value: str, what: str) -> uuid.UUID:
    try:
        return uuid.UUID(value.strip())
    except (ValueError, AttributeError) as exc:
        raise DomainError(f"{what} must be the id returned by a search, not a name", code="bad_id") from exc


def _money(value: str | None, what: str) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except InvalidOperation as exc:
        raise DomainError(f"{what} must be an amount like 500 or 500.50", code="bad_amount") from exc


class OrderLine(BaseModel):
    product_id: str
    qty: int
    unit_price: str | None


def _sale(
    items: list[OrderLine], customer_id: str | None, payment_method: str, amount_paid: str | None, discount: str | None
) -> SaleCreate:
    try:
        return SaleCreate(
            customer_id=_uuid(customer_id, "customer_id") if customer_id else None,
            items=[
                SaleLine(product_id=_uuid(i.product_id, "product_id"), qty=i.qty, unit_price=_money(i.unit_price, "unit_price"))
                for i in items
            ],
            discount=_money(discount, "discount") or Decimal("0.00"),
            payment_method=payment_method,  # type: ignore[arg-type]
            amount_paid=_money(amount_paid, "amount_paid"),
        )
    except ValidationError as exc:
        first = exc.errors()[0]
        raise DomainError(f"{'.'.join(str(p) for p in first['loc'])}: {first['msg']}", code="bad_sale") from exc


def _hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


async def _propose(rc: RuntimeContext, tool: str, summary: str, payload: dict[str, Any]) -> str:
    """File an approval (or point at the identical one already waiting) and tell the model what happened."""
    tctx = rc.tool_context()
    digest = approvals.payload_hash(payload)
    existing = (
        await rc.db.execute(
            select(AgentAction).where(
                AgentAction.tenant_id == rc.principal.tenant_id,
                AgentAction.status == ActionStatus.pending.value,
                AgentAction.payload_hash == digest,
                AgentAction.requested_by == rc.principal.user_id,
            )
        )
    ).scalars().first()
    action = existing or await approvals.request_action(tctx, agent="sales", tool=tool, summary=summary, payload=payload)
    if existing is None:
        rc.actions.append(ProposedAction(id=action.id, tool=tool, summary=summary))
    return (
        f"Sent for approval: {summary}. Nothing has changed yet: a manager or the owner must approve it in the "
        "Approvals page. Tell the user exactly that."
    )


# -- reads ---------------------------------------------------------------------------------------------------------


@function_tool
async def find_product(wrapper: Ctx, query: str) -> str:
    """Search the shop's products by name or SKU. Returns up to 5 matches with id, price and stock."""

    async def handler(rc: RuntimeContext, _direct: bool) -> str:
        items, total = await product_service.list_products(
            rc.db, rc.principal, q=query, category=None, active=True, low_stock=None, sort="name", limit=5, offset=0
        )
        if not items:
            return f"No product matches '{query}'."
        lines = [f"id={p.id} | {p.name} | SKU {p.sku} | {_rs(p.price)} | {p.qty_on_hand} in stock" for p in items]
        more = f"\n({total - len(items)} more match; ask for a more specific name.)" if total > len(items) else ""
        return "\n".join(lines) + more

    return await _run(wrapper, "find_product", {"query": query}, handler)


@function_tool
async def find_customer(wrapper: Ctx, query: str) -> str:
    """Search the shop's customers by name or phone. Returns up to 5 matches with id (and balance for managers)."""

    async def handler(rc: RuntimeContext, _direct: bool) -> str:
        items, total = await customer_service.list_customers(
            rc.db, rc.principal, q=query, owing_only=False, sort="name", limit=5, offset=0
        )
        if not items:
            return f"No customer matches '{query}'."
        out = []
        for c in items:
            rc.redactor.learn(c.name, "customer")
            rc.redactor.learn(c.phone, "phone")
            rc.redactor.learn(c.email, "email")
            owes = f" | owes {_rs(c.balance)}" if c.balance is not None and c.balance > 0 else ""
            out.append(f"id={c.id} | {c.name or 'no name'} | {c.phone}{owes}")
        return "\n".join(out) + (f"\n({total - len(items)} more match.)" if total > len(items) else "")

    return await _run(wrapper, "find_customer", {"query": query}, handler)


@function_tool
async def get_balance(wrapper: Ctx, customer_id: str) -> str:
    """How much a customer owes the shop (udhaar). Managers and owners only."""

    async def handler(rc: RuntimeContext, _direct: bool) -> str:
        customer = await customer_service.get_live(rc.db, rc.principal.tenant_id, _uuid(customer_id, "customer_id"))
        rc.redactor.learn(customer.name, "customer")
        rc.redactor.learn(customer.phone, "phone")
        owed = await ledger_service.customer_balance(rc.db, rc.principal.tenant_id, customer.id)
        return f"{customer.name or customer.phone} owes {_rs(owed)}."

    return await _run(wrapper, "get_balance", {"customer_id": customer_id}, handler)


@function_tool
async def draft_order(
    wrapper: Ctx,
    items: list[OrderLine],
    customer_id: str | None,
    payment_method: Literal["cash", "card", "bank", "wallet", "udhaar"],
    amount_paid: str | None,
    discount: str | None,
) -> str:
    """Add up a sale WITHOUT recording it, so the user can check it. Always call this before post_order, show the
    summary, and wait for the user to confirm. Use ids from find_product and find_customer."""

    async def handler(rc: RuntimeContext, _direct: bool) -> str:
        sale = _sale(items, customer_id, payment_method, amount_paid, discount)
        preview = await order_service.preview_sale(
            rc.db,
            rc.principal,
            SalePreviewRequest(items=sale.items, discount=sale.discount, payment_method=sale.payment_method, amount_paid=sale.amount_paid),
        )
        owner = ""
        if sale.customer_id:
            customer = await customer_service.get_live(rc.db, rc.principal.tenant_id, sale.customer_id)
            rc.redactor.learn(customer.name, "customer")
            rc.redactor.learn(customer.phone, "phone")
            owner = f" for {customer.name or customer.phone}"
        lines = "; ".join(f"{ln.product_name} x {sum(i.qty for i in sale.items if i.product_id == ln.product_id)} = {_rs(ln.line_total)}" for ln in preview.lines)
        problems = f" Problems: {'; '.join(preview.warnings)}." if preview.warnings else ""
        if not preview.warnings:
            _DRAFTS.setdefault(rc.session_id, set()).add(_hash(sale.model_dump(mode="json")))
        return (
            f"Draft sale{owner}: {lines}. Items {_rs(preview.subtotal)}, discount {_rs(preview.discount)}, total {_rs(preview.total)}. "
            f"Paid now {_rs(preview.amount_paid)} by {payment_method}, on credit {_rs(preview.amount_due)}.{problems} "
            "Show this to the user and ask them to confirm before posting."
        )

    args = {"items": [i.model_dump() for i in items], "customer_id": customer_id, "payment_method": payment_method}
    return await _run(wrapper, "draft_order", args, handler)


@function_tool
async def get_sales_summary(wrapper: Ctx, period: Literal["today", "week", "month"]) -> str:
    """How many sales were posted and their total, for today, the last 7 days, or this month."""

    async def handler(rc: RuntimeContext, _direct: bool) -> str:
        start, end = report_service.period_bounds(period)
        s = await report_service.sales_summary(rc.db, rc.principal.tenant_id, start, end)
        return f"{period}: {s.orders} sales, total {_rs(s.total)}."

    return await _run(wrapper, "get_sales_summary", {"period": period}, handler)


@function_tool
async def get_profit(wrapper: Ctx, period: Literal["today", "week", "month"]) -> str:
    """Profit (sales minus the cost of what was sold) for a period. Managers and owners only."""

    async def handler(rc: RuntimeContext, _direct: bool) -> str:
        start, end = report_service.period_bounds(period)
        p = await report_service.profit(rc.db, rc.principal.tenant_id, start, end)
        note = f" {p.orders_without_cost} sales were left out because a product has no cost." if p.orders_without_cost else ""
        return f"{period}: profit {_rs(p.profit)} over {p.orders_counted} sales.{note}"

    return await _run(wrapper, "get_profit", {"period": period}, handler)


# -- writes: proposed, never run directly --------------------------------------------------------------------------


@function_tool
async def post_order(
    wrapper: Ctx,
    items: list[OrderLine],
    customer_id: str | None,
    payment_method: Literal["cash", "card", "bank", "wallet", "udhaar"],
    amount_paid: str | None,
    discount: str | None,
) -> str:
    """Record a sale. Only call this after draft_order was shown to the user and they confirmed it. It does not post
    the sale itself: it sends it for approval."""

    async def handler(rc: RuntimeContext, _direct: bool) -> str:
        sale = _sale(items, customer_id, payment_method, amount_paid, discount)
        payload = sale.model_dump(mode="json")
        if _hash(payload) not in _DRAFTS.get(rc.session_id, set()):
            raise DomainError(
                "Draft this exact sale with draft_order and get the user's confirmation first", code="draft_first"
            )
        preview = await order_service.preview_sale(
            rc.db,
            rc.principal,
            SalePreviewRequest(items=sale.items, discount=sale.discount, payment_method=sale.payment_method, amount_paid=sale.amount_paid),
        )
        if preview.warnings:
            raise DomainError("; ".join(preview.warnings), code="not_postable")
        if sale.customer_id is None and preview.amount_due > 0:
            raise DomainError("Choose the customer: part of this sale is on credit", code="customer_required_for_credit")
        summary = f"Post a sale of {_rs(preview.total)} ({len(sale.items)} item line{'s' if len(sale.items) != 1 else ''}, {payment_method})"
        limit = settings.AGENT_AUTO_POST_LIMIT
        if limit > 0 and preview.total <= limit:  # the shop allows small sales without asking
            from app.agent_runtime.executors import post_order_payload

            order = await post_order_payload(rc.db, rc.principal, payload, idempotency_key=f"agent-{_hash(payload)[:32]}")
            return f"Posted: {summary}. Order {str(order.id)[:8].upper()} is recorded."
        return await _propose(rc, "post_order", summary, payload)

    args = {"items": [i.model_dump() for i in items], "customer_id": customer_id, "payment_method": payment_method}
    return await _run(wrapper, "post_order", args, handler)


@function_tool
async def record_payment(
    wrapper: Ctx, customer_id: str, amount: str, method: Literal["cash", "card", "bank", "wallet"]
) -> str:
    """Record that a customer paid some of what they owe (udhaar). Sends it for approval. Managers and owners only."""

    async def handler(rc: RuntimeContext, _direct: bool) -> str:
        cid = _uuid(customer_id, "customer_id")
        value = _money(amount, "amount")
        if value is None or value <= 0:
            raise DomainError("amount must be above zero", code="bad_amount")
        customer = await customer_service.get_live(rc.db, rc.principal.tenant_id, cid)
        rc.redactor.learn(customer.name, "customer")
        rc.redactor.learn(customer.phone, "phone")
        owed = await ledger_service.customer_balance(rc.db, rc.principal.tenant_id, cid)
        if value > owed:
            raise DomainError(f"They only owe {_rs(owed)}", code="payment_exceeds_balance")
        summary = f"Record a payment of {_rs(value)} ({method}) from {customer.name or customer.phone}"
        return await _propose(rc, "record_payment", summary, {"customer_id": str(cid), "amount": str(value), "method": method})

    return await _run(wrapper, "record_payment", {"customer_id": customer_id, "amount": amount, "method": method}, handler)


@function_tool
async def adjust_stock(
    wrapper: Ctx, product_id: str, delta: int, reason: Literal["purchase", "adjustment", "return"], note: str | None
) -> str:
    """Change a product's stock count (positive adds, negative removes). Sends it for approval. Managers and owners only."""

    async def handler(rc: RuntimeContext, _direct: bool) -> str:
        pid = _uuid(product_id, "product_id")
        if delta == 0:
            raise DomainError("delta must not be zero", code="zero_movement")
        product = await product_service.get_product(rc.db, rc.principal, pid)
        if product.qty_on_hand + delta < 0:
            raise DomainError(f"Only {product.qty_on_hand} in stock", code="insufficient_stock")
        summary = f"Change stock of {product.name} by {delta:+d} ({reason})"
        payload = {"product_id": str(pid), "delta": delta, "reason": reason, "note": note}
        return await _propose(rc, "adjust_stock", summary, payload)

    return await _run(wrapper, "adjust_stock", {"product_id": product_id, "delta": delta, "reason": reason}, handler)


SHOP_TOOLS = [find_product, find_customer, get_balance, draft_order, get_sales_summary, get_profit, post_order, record_payment, adjust_stock]
