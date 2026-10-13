"""Draft purchase orders (PRD W-006 step 3): drafted by the low-stock recipe, read and cancelled by the owner.

An order is a plan, not a movement: nothing here changes stock, the ledger or a vendor balance. The order is linked to
the approval that sends the reorder message; when that message is sent the order becomes ``sent``. A vendor without a
phone number leaves the order ``drafted`` (the recipe reports the warning), as the W-006 failure path says.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.problems import Conflict, NotFound
from app.core.tenancy import Principal
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.vendor import Vendor
from app.schemas.purchase_orders import PurchaseOrderDetail, PurchaseOrderItemOut, PurchaseOrderOut

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class DraftLine:
    product_id: uuid.UUID | None
    name: str
    qty: int
    unit_cost: Decimal | None


def estimate(lines: list[DraftLine]) -> Decimal:
    """The sum of the lines whose cost is known. A product without a cost counts for nothing, so this is a floor."""
    return sum((line.unit_cost * line.qty for line in lines if line.unit_cost is not None), ZERO)


async def create_draft(
    db: AsyncSession, tenant_id: uuid.UUID, *, vendor_id: uuid.UUID, lines: list[DraftLine], action_id: uuid.UUID | None
) -> PurchaseOrder:
    order = PurchaseOrder(tenant_id=tenant_id, vendor_id=vendor_id, status="drafted", total=estimate(lines), action_id=action_id)
    db.add(order)
    await db.flush()
    for line in lines:
        db.add(
            PurchaseOrderItem(
                tenant_id=tenant_id, purchase_order_id=order.id, product_id=line.product_id, name=line.name, qty=line.qty, unit_cost=line.unit_cost
            )
        )
    await db.flush()
    record_audit(
        db,
        "purchase_order.drafted",
        tenant_id=tenant_id,
        actor_type="system",
        entity="purchase_order",
        entity_id=order.id,
        after={"vendor_id": str(vendor_id), "items": len(lines), "total": str(order.total)},
    )
    return order


async def mark_sent_for_action(db: AsyncSession, tenant_id: uuid.UUID, action_id: uuid.UUID) -> uuid.UUID | None:
    """The reorder message behind ``action_id`` went out: the order it belongs to is now ``sent``. Returns its id."""
    order = (
        await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.tenant_id == tenant_id, PurchaseOrder.action_id == action_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if order is None or order.status not in {"drafted", "approved"}:
        return None
    order.status, order.sent_at = "sent", datetime.now(timezone.utc)
    await db.flush()
    record_audit(
        db,
        "purchase_order.sent",
        tenant_id=tenant_id,
        actor_type="system",
        entity="purchase_order",
        entity_id=order.id,
        after={"action_id": str(action_id)},
    )
    return order.id


async def _item_counts(db: AsyncSession, tenant_id: uuid.UUID, order_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not order_ids:
        return {}
    rows = (
        await db.execute(
            select(PurchaseOrderItem.purchase_order_id, func.count())
            .where(PurchaseOrderItem.tenant_id == tenant_id, PurchaseOrderItem.purchase_order_id.in_(order_ids))
            .group_by(PurchaseOrderItem.purchase_order_id)
        )
    ).all()
    return {order_id: int(n) for order_id, n in rows}


def _out(order: PurchaseOrder, vendor: Vendor, item_count: int) -> PurchaseOrderOut:
    return PurchaseOrderOut(
        id=order.id,
        vendor_id=order.vendor_id,
        vendor_name=vendor.name,
        vendor_has_phone=bool(vendor.phone),
        status=order.status,  # type: ignore[arg-type]
        total=order.total,
        item_count=item_count,
        action_id=order.action_id,
        created_at=order.created_at,
        sent_at=order.sent_at,
    )


async def list_orders(
    db: AsyncSession, principal: Principal, *, status: str | None, limit: int, offset: int
) -> tuple[list[PurchaseOrderOut], int]:
    conditions = [PurchaseOrder.tenant_id == principal.tenant_id]
    if status:
        conditions.append(PurchaseOrder.status == status)
    total = (await db.execute(select(func.count()).select_from(PurchaseOrder).where(*conditions))).scalar_one()
    rows = (
        await db.execute(
            select(PurchaseOrder, Vendor)
            .join(Vendor, Vendor.id == PurchaseOrder.vendor_id)
            .where(*conditions)
            .order_by(PurchaseOrder.created_at.desc(), PurchaseOrder.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    counts = await _item_counts(db, principal.tenant_id, [o.id for o, _ in rows])
    return [_out(o, v, counts.get(o.id, 0)) for o, v in rows], int(total)


async def _get(db: AsyncSession, tenant_id: uuid.UUID, order_id: uuid.UUID, *, lock: bool = False) -> tuple[PurchaseOrder, Vendor]:
    stmt = (
        select(PurchaseOrder, Vendor)
        .join(Vendor, Vendor.id == PurchaseOrder.vendor_id)
        .where(PurchaseOrder.id == order_id, PurchaseOrder.tenant_id == tenant_id)
    )
    if lock:
        stmt = stmt.with_for_update(of=PurchaseOrder)
    row = (await db.execute(stmt)).first()
    if row is None:
        raise NotFound("Purchase order")
    return row[0], row[1]


async def get_order(db: AsyncSession, principal: Principal, order_id: uuid.UUID) -> PurchaseOrderDetail:
    order, vendor = await _get(db, principal.tenant_id, order_id)
    items = (
        await db.execute(
            select(PurchaseOrderItem)
            .where(PurchaseOrderItem.tenant_id == principal.tenant_id, PurchaseOrderItem.purchase_order_id == order.id)
            .order_by(PurchaseOrderItem.name)
        )
    ).scalars().all()
    base = _out(order, vendor, len(items))
    return PurchaseOrderDetail(**base.model_dump(), items=[PurchaseOrderItemOut.model_validate(i) for i in items], note=order.note)


async def cancel(db: AsyncSession, principal: Principal, order_id: uuid.UUID) -> PurchaseOrderDetail:
    order, _vendor = await _get(db, principal.tenant_id, order_id, lock=True)
    if order.status != "drafted":
        raise Conflict("Only a draft order can be cancelled.", code="not_a_draft")
    order.status = "cancelled"
    await db.flush()
    record_audit(
        db,
        "purchase_order.cancelled",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="purchase_order",
        entity_id=order.id,
        after={"vendor_id": str(order.vendor_id)},
    )
    return await get_order(db, principal, order_id)
