"""Stock changes (PRD F-010, §12.3): the only code allowed to change ``inventory_items.qty_on_hand``.

Every change writes a ``stock_movements`` row and an audit row in the caller's transaction. The inventory row is locked
(``FOR UPDATE``) so two concurrent sales of the last unit cannot both succeed, and the ``version`` column backs that up
(optimistic concurrency, PRD §12.2).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.problems import DomainError, NotFound
from app.models.inventory import InventoryItem
from app.models.stock import StockMovement


class InsufficientStock(DomainError):
    def __init__(self, product_name: str, available: int, wanted: int) -> None:
        super().__init__(
            f"Not enough stock for {product_name}: {available} on hand, {wanted} needed",
            code="insufficient_stock",
        )
        self.available = available
        self.wanted = wanted


async def lock_inventory(db: AsyncSession, tenant_id: uuid.UUID, product_id: uuid.UUID) -> InventoryItem:
    row = (
        await db.execute(
            select(InventoryItem)
            .where(InventoryItem.tenant_id == tenant_id, InventoryItem.product_id == product_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFound("Product")
    return row


async def record_movement(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    delta: int,
    reason: str,
    actor_id: uuid.UUID | str | None,
    actor_type: str = "user",
    ref_type: str | None = None,
    ref_id: uuid.UUID | None = None,
    note: str | None = None,
    product_name: str = "this product",
    allow_negative: bool = False,
) -> StockMovement:
    """Apply ``delta`` to a product's stock and record why. Raises ``InsufficientStock`` below zero."""
    if delta == 0:
        raise DomainError("A stock movement must change the quantity", code="zero_movement")
    inventory = await lock_inventory(db, tenant_id, product_id)
    new_qty = inventory.qty_on_hand + delta
    if new_qty < 0 and not allow_negative:
        raise InsufficientStock(product_name, inventory.qty_on_hand, -delta)
    before = inventory.qty_on_hand
    inventory.qty_on_hand = new_qty
    movement = StockMovement(
        tenant_id=tenant_id,
        product_id=product_id,
        delta=delta,
        reason=reason,
        ref_type=ref_type,
        ref_id=ref_id,
        actor_type=actor_type,
        actor_id=str(actor_id) if actor_id is not None else None,
        note=note,
    )
    db.add(movement)
    await db.flush()
    record_audit(
        db,
        "stock.moved",
        tenant_id=tenant_id,
        actor_type=actor_type,
        actor_id=actor_id,
        entity="product",
        entity_id=product_id,
        before={"qty_on_hand": before},
        after={
            "qty_on_hand": new_qty,
            "delta": delta,
            "reason": reason,
            "ref_type": ref_type,
            "ref_id": str(ref_id) if ref_id else None,
        },
    )
    return movement


async def list_movements(
    db: AsyncSession, tenant_id: uuid.UUID, product_id: uuid.UUID, *, limit: int, offset: int
) -> tuple[list[StockMovement], int]:
    from sqlalchemy import func

    base = select(StockMovement).where(StockMovement.tenant_id == tenant_id, StockMovement.product_id == product_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        await db.execute(
            base.order_by(StockMovement.created_at.desc(), StockMovement.id.desc()).limit(limit).offset(offset)
        )
    ).scalars()
    return list(rows), int(total)
