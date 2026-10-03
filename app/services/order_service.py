"""Sales and orders (PRD F-007, F-008, §12.3): the only code that posts a sale.

Posting is one transaction: the order and its lines, a stock movement per line, the payment actually received, and a
ledger debit for whatever the customer has not paid (udhaar), plus the audit row. Either all of it happens or none.
Prices, costs and names are copied onto the lines so a later change to the product never rewrites history.
"""

from __future__ import annotations

import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.problems import DomainError, NotFound
from app.core.search import escape_like
from app.core.tenancy import Principal
from app.models.customer import Customer
from app.models.inventory import InventoryItem
from app.models.order import Order, OrderItem
from app.models.payment import LedgerEntry, Payment
from app.models.product import Product
from app.models.tenant import TenantRole
from app.schemas.order import (
    OrderDetail,
    OrderItemOut,
    OrderPaymentOut,
    OrderSummary,
    ReverseRequest,
    SaleCreate,
    SalePreview,
    SalePreviewLine,
    SalePreviewRequest,
)
from app.services import customer_service, ledger_service, stock_service

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


async def _summaries(db: AsyncSession, tenant_id: uuid.UUID, orders: list[Order]) -> list[OrderSummary]:
    if not orders:
        return []
    ids = [o.id for o in orders]
    paid: dict[uuid.UUID | None, Decimal] = {
        order_id: Decimal(total)
        for order_id, total in (
            await db.execute(
                select(Payment.order_id, func.coalesce(func.sum(Payment.amount), 0))
                .where(Payment.tenant_id == tenant_id, Payment.order_id.in_(ids), Payment.status == "completed")
                .group_by(Payment.order_id)
            )
        ).all()
    }
    counts: dict[uuid.UUID, int] = {
        order_id: int(n)
        for order_id, n in (
            await db.execute(
                select(OrderItem.order_id, func.count())
                .where(OrderItem.tenant_id == tenant_id, OrderItem.order_id.in_(ids))
                .group_by(OrderItem.order_id)
            )
        ).all()
    }
    customer_ids = {o.customer_id for o in orders if o.customer_id}
    names: dict[uuid.UUID, str | None] = {}
    if customer_ids:
        rows = (await db.execute(select(Customer.id, Customer.name, Customer.phone).where(Customer.id.in_(customer_ids)))).all()
        names = {cid: (name or phone) for cid, name, phone in rows}
    out: list[OrderSummary] = []
    for o in orders:
        received = money(paid.get(o.id, ZERO))
        out.append(
            OrderSummary(
                id=o.id,
                status=o.status,
                channel=o.channel,
                customer_id=o.customer_id,
                customer_name=names.get(o.customer_id) if o.customer_id else None,
                subtotal=o.subtotal,
                discount=o.discount,
                total=o.total,
                amount_paid=received,
                amount_due=max(o.total - received, ZERO) if o.status == "posted" else ZERO,
                item_count=int(counts.get(o.id, 0)),
                created_at=o.created_at,
            )
        )
    return out


async def get_order(db: AsyncSession, principal: Principal, order_id: uuid.UUID) -> OrderDetail:
    order = (
        await db.execute(select(Order).where(Order.id == order_id, Order.tenant_id == principal.tenant_id))
    ).scalar_one_or_none()
    if order is None:
        raise NotFound("Order")
    summary = (await _summaries(db, principal.tenant_id, [order]))[0]
    items = (
        await db.execute(
            select(OrderItem).where(OrderItem.order_id == order.id, OrderItem.tenant_id == principal.tenant_id).order_by(OrderItem.created_at, OrderItem.id)
        )
    ).scalars()
    payments = (
        await db.execute(
            select(Payment).where(Payment.order_id == order.id, Payment.tenant_id == principal.tenant_id).order_by(Payment.created_at, Payment.id)
        )
    ).scalars()
    hide_cost = principal.role == TenantRole.staff
    return OrderDetail(
        **summary.model_dump(),
        note=order.note,
        created_by=order.created_by,
        updated_at=order.updated_at,
        items=[
            OrderItemOut(
                id=i.id,
                product_id=i.product_id,
                product_name=i.product_name,
                qty=i.qty,
                unit_price=i.unit_price,
                unit_cost=None if hide_cost else i.unit_cost,
                line_total=money(i.unit_price * i.qty),
            )
            for i in items
        ],
        payments=[
            OrderPaymentOut(id=p.id, amount=p.amount, method=p.method, status=p.status, created_at=p.created_at)
            for p in payments
        ],
    )


async def preview_sale(db: AsyncSession, principal: Principal, body: SalePreviewRequest) -> SalePreview:
    """Add up a sale without writing anything. Unknown or unavailable products are warnings here, errors when posting."""
    tenant_id = principal.tenant_id
    ids = sorted({line.product_id for line in body.items})
    rows = (
        await db.execute(
            select(Product, InventoryItem.qty_on_hand)
            .join(InventoryItem, InventoryItem.product_id == Product.id)
            .where(Product.id.in_(ids), Product.tenant_id == tenant_id, Product.deleted_at.is_(None))
        )
    ).all()
    found = {p.id: (p, on_hand) for p, on_hand in rows}
    wanted: dict[uuid.UUID, int] = {}
    for line in body.items:
        wanted[line.product_id] = wanted.get(line.product_id, 0) + line.qty
    warnings: list[str] = []
    lines: list[SalePreviewLine] = []
    subtotal = ZERO
    for line in body.items:
        entry = found.get(line.product_id)
        if entry is None:
            warnings.append("One of the products is not in your shop")
            continue
        product, on_hand = entry
        price = money(line.unit_price if line.unit_price is not None else product.price)
        line_total = money(price * line.qty)
        subtotal += line_total
        enough = wanted[product.id] <= on_hand
        if not product.active:
            warnings.append(f"{product.name} is not available for sale")
        elif not enough:
            warnings.append(f"Not enough stock for {product.name}: {on_hand} on hand, {wanted[product.id]} needed")
        lines.append(
            SalePreviewLine(
                product_id=product.id,
                product_name=product.name,
                unit_price=price,
                line_total=line_total,
                available=on_hand,
                enough_stock=enough,
            )
        )
    subtotal = money(subtotal)
    discount = money(body.discount)
    if discount > subtotal:
        warnings.append(f"The discount cannot be more than the items total ({subtotal})")
    total = money(subtotal - discount) if discount <= subtotal else subtotal
    if body.payment_method == "udhaar":
        paid = ZERO
    else:
        paid = money(body.amount_paid) if body.amount_paid is not None else total
    if paid > total:
        warnings.append(f"The amount paid cannot be more than the total ({total})")
        paid = total
    warnings = list(dict.fromkeys(warnings))  # one message per problem, not one per line
    return SalePreview(
        lines=lines,
        subtotal=subtotal,
        discount=discount,
        total=total,
        amount_paid=paid,
        amount_due=total - paid,
        warnings=warnings,
    )


async def _existing_by_key(db: AsyncSession, tenant_id: uuid.UUID, key: str) -> Order | None:
    return (
        await db.execute(select(Order).where(Order.tenant_id == tenant_id, Order.idempotency_key == key))
    ).scalar_one_or_none()


async def post_sale(
    db: AsyncSession, principal: Principal, body: SaleCreate, *, idempotency_key: str | None, channel: str = "pos"
) -> tuple[OrderDetail, bool]:
    """Post a sale. Returns the order and whether it was created now (False: an earlier retry already did)."""
    tenant_id = principal.tenant_id
    if idempotency_key:
        earlier = await _existing_by_key(db, tenant_id, idempotency_key)
        if earlier is not None:
            return await get_order(db, principal, earlier.id), False
    if body.stock_override and principal.role == TenantRole.staff:
        raise DomainError("Selling more than is in stock needs a manager", code="override_needs_manager", status_code=403)

    # -- the products: all live, in this shop, and for sale
    product_ids = sorted({line.product_id for line in body.items})
    found = {
        p.id: p
        for p in (
            await db.execute(select(Product).where(Product.id.in_(product_ids), Product.tenant_id == tenant_id, Product.deleted_at.is_(None)))
        ).scalars()
    }
    for line in body.items:
        product = found.get(line.product_id)
        if product is None:
            raise DomainError("One of the products is not in your shop", code="unknown_product")
        if not product.active:
            raise DomainError(f"{product.name} is not available for sale", code="product_inactive")

    # -- money
    priced = [(line, money(line.unit_price if line.unit_price is not None else found[line.product_id].price)) for line in body.items]
    subtotal = money(sum((price * line.qty for line, price in priced), ZERO))
    discount = money(body.discount)
    if discount > subtotal:
        raise DomainError(f"The discount cannot be more than the items total ({subtotal})", code="discount_exceeds_subtotal")
    total = subtotal - discount
    if body.payment_method == "udhaar":
        paid = ZERO
    else:
        paid = money(body.amount_paid) if body.amount_paid is not None else total
    if paid > total:
        raise DomainError(f"The amount paid cannot be more than the total ({total})", code="paid_exceeds_total")
    due = total - paid

    # -- the customer, needed for credit
    customer: Customer | None = None
    if body.customer_id is not None:
        try:
            customer = await customer_service.lock_customer(db, tenant_id, body.customer_id) if due > 0 else await customer_service.get_live(db, tenant_id, body.customer_id)
        except NotFound as exc:
            raise DomainError("That customer is not in your shop", code="unknown_customer") from exc
    if due > 0 and customer is None:
        raise DomainError("Choose the customer: part of this sale is on credit (udhaar)", code="customer_required_for_credit")

    # -- stock: lock every inventory row in a fixed order (no deadlocks), then check what is on the shelf
    wanted: dict[uuid.UUID, int] = {}
    for line in body.items:
        wanted[line.product_id] = wanted.get(line.product_id, 0) + line.qty
    locked: dict[uuid.UUID, InventoryItem] = {}
    for pid in product_ids:
        locked[pid] = await stock_service.lock_inventory(db, tenant_id, pid)
    shortfalls = {pid: qty - locked[pid].qty_on_hand for pid, qty in wanted.items() if qty > locked[pid].qty_on_hand}
    if shortfalls and not body.stock_override:
        pid = next(iter(shortfalls))
        raise stock_service.InsufficientStock(found[pid].name, locked[pid].qty_on_hand, wanted[pid])

    # -- write everything
    order = Order(
        tenant_id=tenant_id,
        customer_id=customer.id if customer else None,
        status="posted",
        subtotal=subtotal,
        discount=discount,
        total=total,
        channel=channel,
        idempotency_key=idempotency_key,
        created_by=principal.user_id,
        note=body.note,
    )
    try:
        async with db.begin_nested():
            db.add(order)
            await db.flush()
    except IntegrityError:
        if idempotency_key:  # a concurrent retry with the same key won the race: return its order
            winner = await _existing_by_key(db, tenant_id, idempotency_key)
            if winner is not None:
                return await get_order(db, principal, winner.id), False
        raise

    for line, price in priced:
        product = found[line.product_id]
        db.add(
            OrderItem(
                tenant_id=tenant_id,
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                qty=line.qty,
                unit_price=price,
                unit_cost=product.cost,
            )
        )
    await db.flush()

    for pid, short in shortfalls.items():  # the shelf count was wrong: correct it first, on the record
        await stock_service.record_movement(
            db,
            tenant_id=tenant_id,
            product_id=pid,
            delta=short,
            reason="adjustment",
            actor_id=principal.user_id,
            ref_type="order",
            ref_id=order.id,
            note="Stock override on sale: the shelf count was lower than the sale",
            product_name=found[pid].name,
        )
        record_audit(
            db,
            "order.stock_override",
            tenant_id=tenant_id,
            actor_id=principal.user_id,
            entity="order",
            entity_id=order.id,
            after={"product_id": str(pid), "shortfall": short},
        )
    for pid in product_ids:
        await stock_service.record_movement(
            db,
            tenant_id=tenant_id,
            product_id=pid,
            delta=-wanted[pid],
            reason="sale",
            actor_id=principal.user_id,
            ref_type="order",
            ref_id=order.id,
            product_name=found[pid].name,
        )

    if paid > 0:
        db.add(
            Payment(
                tenant_id=tenant_id,
                order_id=order.id,
                customer_id=customer.id if customer else None,
                amount=paid,
                method=body.payment_method,
                created_by=principal.user_id,
            )
        )
    if due > 0 and customer is not None:
        await ledger_service.add_entry(
            db,
            tenant_id=tenant_id,
            party_type="customer",
            party_id=customer.id,
            amount=due,
            direction="debit",
            ref_type="order",
            ref_id=order.id,
            created_by=principal.user_id,
        )
    await db.flush()
    record_audit(
        db,
        "order.posted",
        tenant_id=tenant_id,
        actor_id=principal.user_id,
        entity="order",
        entity_id=order.id,
        after={
            "total": str(total),
            "paid": str(paid),
            "on_credit": str(due),
            "channel": channel,
            "lines": [{"product_id": str(line.product_id), "qty": line.qty} for line in body.items],
        },
    )
    return await get_order(db, principal, order.id), True


def _list_conditions(
    tenant_id: uuid.UUID,
    *,
    status: str | None,
    channel: str | None,
    customer_id: uuid.UUID | None,
    q: str | None,
) -> list[Any]:
    conditions: list[Any] = [Order.tenant_id == tenant_id]
    if status:
        conditions.append(Order.status == status)
    if channel:
        conditions.append(Order.channel == channel)
    if customer_id:
        conditions.append(Order.customer_id == customer_id)
    if q:
        like = f"%{escape_like(q.strip())}%"
        by_customer = select(Customer.id).where(
            Customer.tenant_id == tenant_id, or_(Customer.name.ilike(like, escape="\\"), Customer.phone.ilike(like, escape="\\"))
        )
        by_product = select(OrderItem.order_id).where(OrderItem.tenant_id == tenant_id, OrderItem.product_name.ilike(like, escape="\\"))
        conditions.append(or_(Order.customer_id.in_(by_customer), Order.id.in_(by_product), Order.note.ilike(like, escape="\\")))
    return conditions


async def list_orders(
    db: AsyncSession,
    principal: Principal,
    *,
    status: str | None,
    channel: str | None,
    customer_id: uuid.UUID | None,
    q: str | None,
    sort: str,
    limit: int,
    offset: int,
) -> tuple[list[OrderSummary], int]:
    descending = sort.startswith("-")
    key = sort.lstrip("-")
    columns = {"created_at": Order.created_at, "total": Order.total}
    if key not in columns:
        raise DomainError(f"Cannot sort by '{key}'. Use one of: {', '.join(sorted(columns))}", code="invalid_sort", status_code=400)
    conditions = _list_conditions(principal.tenant_id, status=status, channel=channel, customer_id=customer_id, q=q)
    total = (await db.execute(select(func.count()).select_from(select(Order.id).where(*conditions).subquery()))).scalar_one()
    column = columns[key]
    rows = (
        await db.execute(
            select(Order).where(*conditions).order_by(column.desc() if descending else column.asc(), Order.id.desc()).limit(limit).offset(offset)
        )
    ).scalars()
    return await _summaries(db, principal.tenant_id, list(rows)), int(total)



async def reverse_order(db: AsyncSession, principal: Principal, order_id: uuid.UUID, body: ReverseRequest) -> OrderDetail:
    """Undo a posted sale (managers and owners): the stock goes back, the payments are marked reversed and what was put on
    the customer's udhaar is credited back. History is kept: nothing is deleted, every step is a new row."""
    tenant_id = principal.tenant_id
    order = (
        await db.execute(select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id).with_for_update())
    ).scalar_one_or_none()
    if order is None:
        raise NotFound("Order")
    if order.status != "posted":
        raise DomainError(f"This sale is already {order.status}, so it cannot be reversed", code="order_not_posted")

    items = list((await db.execute(select(OrderItem).where(OrderItem.order_id == order.id, OrderItem.tenant_id == tenant_id))).scalars())
    for pid in sorted({i.product_id for i in items}):  # fixed order: no deadlocks between two reversals
        await stock_service.lock_inventory(db, tenant_id, pid)
    returned: dict[uuid.UUID, int] = {}
    names: dict[uuid.UUID, str] = {}
    for item in items:
        returned[item.product_id] = returned.get(item.product_id, 0) + item.qty
        names[item.product_id] = item.product_name
    for pid, count in returned.items():
        await stock_service.record_movement(
            db,
            tenant_id=tenant_id,
            product_id=pid,
            delta=count,
            reason="reversal",
            actor_id=principal.user_id,
            ref_type="order",
            ref_id=order.id,
            note=f"Sale reversed: {body.reason}"[:255],
            product_name=names[pid],
        )

    payments = list(
        (await db.execute(select(Payment).where(Payment.order_id == order.id, Payment.tenant_id == tenant_id, Payment.status == "completed"))).scalars()
    )
    for payment in payments:
        payment.status = "reversed"

    debited = (
        await db.execute(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                LedgerEntry.tenant_id == tenant_id,
                LedgerEntry.ref_type == "order",
                LedgerEntry.ref_id == order.id,
                LedgerEntry.direction == "debit",
            )
        )
    ).scalar_one()
    credited_back = money(Decimal(debited))
    if credited_back > 0 and order.customer_id is not None:
        await customer_service.lock_customer(db, tenant_id, order.customer_id)
        await ledger_service.add_entry(
            db,
            tenant_id=tenant_id,
            party_type="customer",
            party_id=order.customer_id,
            amount=credited_back,
            direction="credit",
            ref_type="order",
            ref_id=order.id,
            created_by=principal.user_id,
        )

    order.status = "reversed"
    order.note = f"{order.note} | Reversed: {body.reason}" if order.note else f"Reversed: {body.reason}"
    await db.flush()
    record_audit(
        db,
        "order.reversed",
        tenant_id=tenant_id,
        actor_id=principal.user_id,
        entity="order",
        entity_id=order.id,
        before={"status": "posted"},
        after={"status": "reversed", "reason": body.reason, "credited_back": str(credited_back), "payments_reversed": len(payments)},
    )
    return await get_order(db, principal, order.id)
