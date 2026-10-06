"""The onboarding wizard (PRD F-003, W-001): shop details, channels, products, a test message, live.

The state machine is the PRD's: ``created -> shop_set -> whatsapp_connected -> products_added -> live``, stored on
``tenants.onboarding_state``. Only the shop details are required: the channels, products and test steps can each be skipped
(the state still moves forward), and a step can be done again later from its own page. WhatsApp and Facebook share one
"channels" screen, so ``whatsapp_connected`` means "the channels step is finished" (connected or skipped).

A product import never fails as a whole: every valid CSV row is imported and each bad row is listed with its line number
and the reason. A test message that cannot be sent explains why and offers the sandbox, and does not block going live.
"""

from __future__ import annotations

import csv
import io
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.problems import Conflict, DomainError
from app.core.tenancy import Principal
from app.integrations.http import ProviderError
from app.models.product import Product
from app.models.tenant import Tenant, TenantIntegration
from app.schemas.onboarding import (
    ImportReport,
    OnboardingOut,
    RowError,
    ShopStep,
    State,
    Step,
    TestMessageResult,
)
from app.schemas.product import ProductCreate
from app.services import integration_service, product_service

ORDER: tuple[State, ...] = ("created", "shop_set", "whatsapp_connected", "products_added", "live")
MAX_ROWS = 500
ALIASES = {
    "sku": "sku",
    "name": "name",
    "product": "name",
    "price": "price",
    "cost": "cost",
    "qty": "qty_on_hand",
    "quantity": "qty_on_hand",
    "stock": "qty_on_hand",
    "qty_on_hand": "qty_on_hand",
    "category": "category",
    "reorder_level": "reorder_level",
    "reorder": "reorder_level",
}
TEST_TEXT = "Test message from BazaarFlow: your shop is connected to WhatsApp."


async def _tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    return (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()


async def _connected(db: AsyncSession, tenant_id: uuid.UUID, provider: str) -> bool:
    status = (
        await db.execute(
            select(TenantIntegration.status).where(TenantIntegration.tenant_id == tenant_id, TenantIntegration.provider == provider)
        )
    ).scalar_one_or_none()
    return status == "connected"


async def _product_count(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    return int(
        (await db.execute(select(func.count()).select_from(Product).where(Product.tenant_id == tenant_id, Product.deleted_at.is_(None)))).scalar_one()
    )


def _reached(state: str, target: State) -> bool:
    return ORDER.index(state) >= ORDER.index(target)


async def _advance(db: AsyncSession, principal: Principal, tenant: Tenant, target: State) -> None:
    """Move forward, never back: finishing an earlier step again does not undo a later one."""
    if _reached(tenant.onboarding_state, target):
        return
    before = tenant.onboarding_state
    tenant.onboarding_state = target
    await db.flush()
    record_audit(
        db,
        "onboarding.advanced",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="tenant",
        entity_id=principal.tenant_id,
        before={"state": before},
        after={"state": target},
    )


async def get_state(db: AsyncSession, principal: Principal) -> OnboardingOut:
    tenant = await _tenant(db, principal.tenant_id)
    state: State = tenant.onboarding_state  # type: ignore[assignment]
    done = {
        "shop": _reached(state, "shop_set"),
        "channels": _reached(state, "whatsapp_connected"),
        "products": _reached(state, "products_added"),
        "test": state == "live",
    }
    labels = {"shop": "Shop details", "channels": "Connect WhatsApp and Facebook", "products": "Add your products", "test": "Send a test message"}
    steps: list[Step] = []
    current_set = False
    for key in ("shop", "channels", "products", "test"):
        if done[key]:
            status = "done"
        elif not current_set:
            status, current_set = "current", True
        else:
            status = "pending"
        steps.append(Step(key=key, label=labels[key], status=status, required=key == "shop"))  # type: ignore[arg-type]
    return OnboardingOut(
        state=state,
        steps=steps,
        whatsapp_connected=await _connected(db, principal.tenant_id, "whatsapp_twilio"),
        facebook_connected=await _connected(db, principal.tenant_id, "facebook"),
        product_count=await _product_count(db, principal.tenant_id),
        owner_phone=tenant.owner_phone,
        shop_name=tenant.name,
    )


async def save_shop(db: AsyncSession, principal: Principal, body: ShopStep) -> OnboardingOut:
    tenant = await _tenant(db, principal.tenant_id)
    tenant.name, tenant.owner_phone, tenant.city = body.name, body.owner_phone, body.city or None
    await db.flush()
    record_audit(
        db,
        "shop.updated",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="tenant",
        entity_id=principal.tenant_id,
        after={"name": body.name, "owner_phone": body.owner_phone, "city": body.city, "via": "onboarding"},
    )
    await _advance(db, principal, tenant, "shop_set")
    return await get_state(db, principal)


async def _require(db: AsyncSession, principal: Principal, state: State, what: str) -> Tenant:
    tenant = await _tenant(db, principal.tenant_id)
    if not _reached(tenant.onboarding_state, state):
        raise Conflict(f"Finish the earlier step first ({what}).", code="step_order")
    return tenant


async def finish_channels(db: AsyncSession, principal: Principal) -> OnboardingOut:
    """The channels step is done once the owner moves on: connected, or skipped."""
    tenant = await _require(db, principal, "shop_set", "shop details")
    await _advance(db, principal, tenant, "whatsapp_connected")
    return await get_state(db, principal)


async def finish_products(db: AsyncSession, principal: Principal) -> OnboardingOut:
    tenant = await _require(db, principal, "whatsapp_connected", "channels")
    await _advance(db, principal, tenant, "products_added")
    return await get_state(db, principal)


def _decimal(value: str, field: str) -> Decimal:
    try:
        return Decimal(value.replace(",", "").strip())
    except InvalidOperation as exc:
        raise ValueError(f"{field} must be a number like 500 or 500.50") from exc


def _row_to_product(row: dict[str, str]) -> ProductCreate:
    values: dict[str, Any] = {}
    for key in ("sku", "name", "category"):
        if row.get(key, "").strip():
            values[key] = row[key].strip()
    if row.get("price", "").strip():
        values["price"] = _decimal(row["price"], "price")
    if row.get("cost", "").strip():
        values["cost"] = _decimal(row["cost"], "cost")
    for key in ("qty_on_hand", "reorder_level"):
        if row.get(key, "").strip():
            try:
                values[key] = int(Decimal(row[key].strip()))
            except (InvalidOperation, ValueError) as exc:
                raise ValueError(f"{key.replace('_', ' ')} must be a whole number") from exc
    return ProductCreate(**values)


def _explain(error: ValidationError) -> str:
    parts = []
    for item in error.errors()[:3]:
        field = ".".join(str(p) for p in item["loc"]) or "row"
        parts.append(f"{field}: {item['msg']}")
    return "; ".join(parts)


async def import_products(db: AsyncSession, principal: Principal, text: str) -> ImportReport:
    """Import every valid row; list each bad one. A file with no usable header is refused outright."""
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    headers = [ALIASES.get((h or "").strip().lower().replace(" ", "_")) for h in (reader.fieldnames or [])]
    if not {"sku", "name", "price"} <= {h for h in headers if h}:
        raise DomainError("The file needs a header row with at least these columns: sku, name, price.", code="bad_csv_header")
    reader.fieldnames = [h or f"_ignored{i}" for i, h in enumerate(headers)]
    imported = 0
    failed: list[RowError] = []
    for index, raw in enumerate(reader, start=2):  # the header is line 1
        if index - 1 > MAX_ROWS:
            raise DomainError(f"Import at most {MAX_ROWS} products at a time.", code="too_many_rows")
        row = {k: (v or "") for k, v in raw.items() if k and not k.startswith("_ignored")}
        if not any(v.strip() for v in row.values()):
            continue
        sku = row.get("sku", "").strip() or None
        try:
            body = _row_to_product(row)
            async with db.begin_nested():  # one bad row leaves nothing half done
                await product_service.create_product(db, principal, body)
        except ValidationError as exc:
            failed.append(RowError(row=index, sku=sku, error=_explain(exc)))
        except ValueError as exc:
            failed.append(RowError(row=index, sku=sku, error=str(exc)))
        except DomainError as exc:
            failed.append(RowError(row=index, sku=sku, error=exc.detail))
        else:
            imported += 1
    tenant = await _tenant(db, principal.tenant_id)
    if imported and _reached(tenant.onboarding_state, "whatsapp_connected"):
        await _advance(db, principal, tenant, "products_added")
    record_audit(
        db,
        "onboarding.products_imported",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="tenant",
        entity_id=principal.tenant_id,
        after={"imported": imported, "failed": len(failed)},
    )
    return ImportReport(imported=imported, failed=failed, state=tenant.onboarding_state)  # type: ignore[arg-type]


async def send_test_message(db: AsyncSession, principal: Principal) -> TestMessageResult:
    """Send the owner a WhatsApp test. Going live follows a successful test; a failure explains itself and blocks nothing."""
    tenant = await _require(db, principal, "products_added", "products")
    if not tenant.owner_phone:
        raise DomainError("Add your phone number in the shop details first.", code="no_owner_phone")
    try:
        adapter = await integration_service.adapter_for(db, principal.tenant_id, "whatsapp_twilio")
    except DomainError as exc:
        return TestMessageResult(
            sent=False,
            state=tenant.onboarding_state,  # type: ignore[arg-type]
            detail=f"{exc.detail} You can use the Twilio sandbox for a free test, or skip this step.",
        )
    try:
        result = await adapter.send(principal.tenant_id, tenant.owner_phone, TEST_TEXT, idempotency_key=f"onboarding-test-{uuid.uuid4().hex}")
    except ProviderError as error:
        await integration_service.record_failure(db, principal.tenant_id, "whatsapp_twilio", error)
        return TestMessageResult(
            sent=False,
            state=tenant.onboarding_state,  # type: ignore[arg-type]
            detail="WhatsApp could not send the message right now. Check the connection in Settings -> Integrations, or skip this step.",
        )
    finally:
        await adapter.aclose()
    if not result.ok:
        return TestMessageResult(sent=False, state=tenant.onboarding_state, detail=result.error or "WhatsApp did not deliver the message.")  # type: ignore[arg-type]
    await integration_service.record_success(db, principal.tenant_id, "whatsapp_twilio")
    await _advance(db, principal, tenant, "live")
    return TestMessageResult(sent=True, state="live", detail="Sent. Check your phone: your shop is live.")


async def go_live(db: AsyncSession, principal: Principal) -> OnboardingOut:
    """Finish without a test message."""
    tenant = await _require(db, principal, "products_added", "products")
    await _advance(db, principal, tenant, "live")
    return await get_state(db, principal)
