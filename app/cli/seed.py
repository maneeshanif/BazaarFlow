"""Database seeding CLI: one demo tenant with an owner, inventory and customers.

Loads the v1 sample inventory from ``app/data/inventory_items.json`` into the demo tenant (the
"demo tenant" backfill of PRD §12.4). Idempotent: running it twice does nothing the second time.

Usage:
    DEMO_USER_PASSWORD=... python -m app.cli.seed      # password is generated and printed once if unset
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import secrets
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.security import hash_password
from app.core.tenancy import tenant_session
from app.models.customer import Customer
from app.models.inventory import InventoryItem
from app.models.tenant import AuditLog, Membership, Tenant, TenantRole
from app.models.user import User

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("bazaarflow.seed")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEMO_SLUG = "demo-retail"
DEMO_EMAIL = "demo@bazaarflow.app"


def _money(value: Any) -> Decimal | None:
    """'2500 PKR' / 2500 / '1,299.50' -> Decimal; None when there is no number."""
    match = re.search(r"\d[\d,]*(?:\.\d+)?", str(value))
    return Decimal(match.group(0).replace(",", "")).quantize(Decimal("0.01")) if match else None


def _load_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, list) else []


_FALLBACK_INVENTORY: list[dict[str, Any]] = [
    {"sku": "SHIRT-001", "name": "Classic Oxford Shirt", "price": "2500 PKR", "stock_count": 50, "category": "Apparel"},
    {"sku": "JEANS-002", "name": "Slim Fit Denim", "price": "3800 PKR", "stock_count": 30, "category": "Apparel"},
    {"sku": "SHOES-003", "name": "Leather Loafers", "price": "5500 PKR", "stock_count": 15, "category": "Footwear"},
]


async def seed_database() -> None:
    from app.core import database

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Idempotency check needs the user's own context: a tenantless session sees no tenant rows.
    async with database.AsyncSessionLocal() as probe:
        existing_user = (await probe.execute(select(User).where(User.email == DEMO_EMAIL))).scalar_one_or_none()
    if existing_user is not None:
        logger.info("Demo data already present; nothing to do.")
        return

    password = os.environ.get("DEMO_USER_PASSWORD") or secrets.token_urlsafe(12)
    async with tenant_session(tenant_id, user_id) as session:
        session.add(User(id=user_id, email=DEMO_EMAIL, hashed_password=hash_password(password), name="Demo Owner"))
        session.add(Tenant(id=tenant_id, name="Demo Retail", slug=DEMO_SLUG, plan="demo", owner_phone="+920000000000"))
        await session.flush()
        session.add(Membership(tenant_id=tenant_id, user_id=user_id, role=TenantRole.owner.value))

        inventory = _load_json(DATA_DIR / "inventory_items.json") or _FALLBACK_INVENTORY
        for item in inventory:
            session.add(
                InventoryItem(
                    tenant_id=tenant_id,
                    sku=item.get("sku", f"SKU-{uuid.uuid4().hex[:6].upper()}"),
                    name=item.get("name", "Sample Product"),
                    price=_money(item.get("price", "0")),
                    stock_count=int(item.get("stock_count", item.get("stock_level", 0))),
                    category=item.get("category", "General"),
                )
            )
        for phone, name in (("+923001000001", "Ali Raza"), ("+923001000002", "Sara Khan")):
            session.add(Customer(tenant_id=tenant_id, phone=phone, name=name))
        session.add(
            AuditLog(
                tenant_id=tenant_id,
                actor_type="system",
                action="seed.demo_tenant",
                entity="tenant",
                entity_id=str(tenant_id),
            )
        )

    logger.info("Seeded demo tenant %s (%s items).", DEMO_SLUG, len(inventory))
    logger.info("Demo login: %s / %s", DEMO_EMAIL, password)


if __name__ == "__main__":
    asyncio.run(seed_database())
