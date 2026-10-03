"""Products and their stock level (PRD F-010). Controllers stay thin and call this module.

Rules enforced here: sku unique per tenant among live products, vendor must belong to the tenant, quantity changes only
through ``stock_service`` (opening stock on create is a movement too), soft delete, cost hidden from staff, every
change audited (PRD §14.1).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.audit import record_audit
from app.core.problems import Conflict, DomainError, NotFound
from app.core.tenancy import Principal
from app.models.inventory import InventoryItem
from app.models.product import Product
from app.models.tenant import TenantRole
from app.models.vendor import Vendor
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.services import stock_service

SORTS: dict[str, Any] = {
    "name": Product.name,
    "sku": Product.sku,
    "price": Product.price,
    "created_at": Product.created_at,
    "qty": InventoryItem.qty_on_hand,
}


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def to_out(product: Product, inventory: InventoryItem, role: TenantRole) -> ProductOut:
    return ProductOut(
        id=product.id,
        tenant_id=product.tenant_id,
        sku=product.sku,
        name=product.name,
        category=product.category,
        price=product.price,
        cost=product.cost if role != TenantRole.staff else None,
        vendor_id=product.vendor_id,
        image_url=product.image_url,
        active=product.active,
        qty_on_hand=inventory.qty_on_hand,
        reorder_level=inventory.reorder_level,
        low_stock=inventory.reorder_level > 0 and inventory.qty_on_hand <= inventory.reorder_level,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _live_filters(tenant_id: uuid.UUID) -> list[ColumnElement[bool]]:
    return [Product.tenant_id == tenant_id, Product.deleted_at.is_(None), InventoryItem.tenant_id == tenant_id]


async def list_products(
    db: AsyncSession,
    principal: Principal,
    *,
    q: str | None,
    category: str | None,
    active: bool | None,
    low_stock: bool | None,
    sort: str,
    limit: int,
    offset: int,
) -> tuple[list[ProductOut], int]:
    descending = sort.startswith("-")
    key = sort.lstrip("-")
    if key not in SORTS:
        raise DomainError(
            f"Cannot sort by '{key}'. Use one of: {', '.join(sorted(SORTS))}", code="invalid_sort", status_code=400
        )
    conditions = _live_filters(principal.tenant_id)
    if q:
        like = f"%{_escape_like(q.strip())}%"
        conditions.append(or_(Product.name.ilike(like, escape="\\"), Product.sku.ilike(like, escape="\\")))
    if category:
        conditions.append(Product.category == category)
    if active is not None:
        conditions.append(Product.active.is_(active))
    if low_stock:
        conditions.append(
            and_(InventoryItem.reorder_level > 0, InventoryItem.qty_on_hand <= InventoryItem.reorder_level)
        )
    base = select(Product, InventoryItem).join(InventoryItem, InventoryItem.product_id == Product.id).where(*conditions)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    column = SORTS[key]
    order = (column.desc() if descending else column.asc(), Product.id.asc())
    rows = (await db.execute(base.order_by(*order).limit(limit).offset(offset))).all()
    return [to_out(p, i, principal.role) for p, i in rows], int(total)


async def _get_pair(db: AsyncSession, tenant_id: uuid.UUID, product_id: uuid.UUID) -> tuple[Product, InventoryItem]:
    row = (
        await db.execute(
            select(Product, InventoryItem)
            .join(InventoryItem, InventoryItem.product_id == Product.id)
            .where(Product.id == product_id, *_live_filters(tenant_id))
        )
    ).first()
    if row is None:
        raise NotFound("Product")
    return row[0], row[1]


async def get_product(db: AsyncSession, principal: Principal, product_id: uuid.UUID) -> ProductOut:
    product, inventory = await _get_pair(db, principal.tenant_id, product_id)
    return to_out(product, inventory, principal.role)


async def _check_vendor(db: AsyncSession, tenant_id: uuid.UUID, vendor_id: uuid.UUID | None) -> None:
    if vendor_id is None:
        return
    found = (
        await db.execute(
            select(Vendor.id).where(Vendor.id == vendor_id, Vendor.tenant_id == tenant_id, Vendor.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if found is None:
        raise DomainError("That vendor does not belong to this shop", code="unknown_vendor")


async def create_product(db: AsyncSession, principal: Principal, body: ProductCreate) -> ProductOut:
    await _check_vendor(db, principal.tenant_id, body.vendor_id)
    product = Product(
        tenant_id=principal.tenant_id,
        sku=body.sku,
        name=body.name,
        category=body.category,
        price=body.price,
        cost=body.cost,
        vendor_id=body.vendor_id,
        active=body.active,
    )
    try:
        async with db.begin_nested():  # a savepoint: a duplicate sku must not poison the whole request transaction
            db.add(product)
            await db.flush()
    except IntegrityError as exc:
        raise Conflict(f"A product with SKU {body.sku} already exists", code="duplicate_sku") from exc
    inventory = InventoryItem(
        tenant_id=principal.tenant_id, product_id=product.id, qty_on_hand=0, reorder_level=body.reorder_level or 0
    )
    db.add(inventory)
    await db.flush()
    if body.qty_on_hand > 0:
        await stock_service.record_movement(
            db,
            tenant_id=principal.tenant_id,
            product_id=product.id,
            delta=body.qty_on_hand,
            reason="opening",
            actor_id=principal.user_id,
            product_name=product.name,
            note="Opening stock",
        )
        await db.refresh(inventory)
    record_audit(
        db,
        "product.created",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="product",
        entity_id=product.id,
        after={"sku": product.sku, "name": product.name, "price": str(product.price), "qty_on_hand": body.qty_on_hand},
    )
    await db.refresh(product)
    return to_out(product, inventory, principal.role)


async def update_product(
    db: AsyncSession, principal: Principal, product_id: uuid.UUID, body: ProductUpdate
) -> ProductOut:
    product, inventory = await _get_pair(db, principal.tenant_id, product_id)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise DomainError("Nothing to update", code="empty_update")
    if "vendor_id" in changes:
        await _check_vendor(db, principal.tenant_id, changes["vendor_id"])
    before = {k: str(getattr(product, k, None)) for k in changes if k != "reorder_level"}
    if "reorder_level" in changes:
        before["reorder_level"] = str(inventory.reorder_level)
        inventory.reorder_level = changes.pop("reorder_level") or 0
    for field, value in changes.items():
        setattr(product, field, value)
    try:
        async with db.begin_nested():
            await db.flush()
    except IntegrityError as exc:
        raise Conflict(f"A product with SKU {changes.get('sku')} already exists", code="duplicate_sku") from exc
    record_audit(
        db,
        "product.updated",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="product",
        entity_id=product.id,
        before=before,
        after={k: str(v) for k, v in body.model_dump(exclude_unset=True).items()},
    )
    await db.refresh(product)
    await db.refresh(inventory)
    return to_out(product, inventory, principal.role)


async def delete_product(db: AsyncSession, principal: Principal, product_id: uuid.UUID) -> None:
    product, _inventory = await _get_pair(db, principal.tenant_id, product_id)
    product.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    record_audit(
        db,
        "product.deleted",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="product",
        entity_id=product.id,
        before={"sku": product.sku, "name": product.name},
    )


async def add_manual_movement(
    db: AsyncSession, principal: Principal, product_id: uuid.UUID, *, delta: int, reason: str, note: str | None
) -> ProductOut:
    product, _inventory = await _get_pair(db, principal.tenant_id, product_id)
    await stock_service.record_movement(
        db,
        tenant_id=principal.tenant_id,
        product_id=product.id,
        delta=delta,
        reason=reason,
        actor_id=principal.user_id,
        product_name=product.name,
        note=note,
    )
    return await get_product(db, principal, product_id)
