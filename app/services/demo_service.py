"""The public live demo (PRD F-027): every visitor gets their own temporary shop, already full of believable data.

A demo shop is a normal shop: its own tenant, its own owner, the same row level security, the same rules. It differs in
two columns: ``demo_expires_at`` (``app.cli.purge_demos`` deletes it after DEMO_HOURS) and ``agent_cap_usd`` (a few cents
of AI, so a visitor cannot spend the real allowance). The owner is a throwaway account nobody has the password for.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text

from app.core.audit import record_audit
from app.core.security import ahash_password
from app.core.settings import settings
from app.core.tenancy import Principal, anonymous_session, apply_context, tenant_session
from app.models.tenant import Membership, Tenant, TenantRole
from app.models.user import User
from app.schemas.customer import CustomerCreate
from app.schemas.order import SaleCreate, SaleLine
from app.schemas.product import ProductCreate
from app.schemas.user import TokenOut
from app.services import customer_service, order_service, product_service, session_service

DEMO_EMAIL_DOMAIN = "demo.bazaarflow.invalid"

# (sku, name, category, price, cost, stock, reorder level)
PRODUCTS = [
    ("SHIRT", "Cotton Shirt", "Menswear", "2500.00", "1800.00", 12, 4),
    ("JEANS", "Denim Jeans", "Menswear", "3800.00", "2700.00", 8, 3),
    ("LAWN", "Lawn Suit (3 piece)", "Womenswear", "4200.00", "3100.00", 6, 6),
    ("DUPATTA", "Chiffon Dupatta", "Womenswear", "900.00", "600.00", 25, 8),
    ("KURTA", "Kids Kurta", "Kidswear", "1500.00", "1000.00", 15, 5),
    ("BELT", "Leather Belt", "Accessories", "700.00", "400.00", 3, 5),
    ("CAP", "Summer Cap", "Accessories", "500.00", None, 20, 0),
    ("SOCKS", "Cotton Socks (pair)", "Accessories", "250.00", "150.00", 40, 10),
]
CUSTOMERS = [("+923001110001", "Ali Raza"), ("+923001110002", "Sana Malik"), ("+923001110003", "Bilal Ahmed")]

# (days ago, [(sku, qty)], customer index or None, payment, amount paid or None)
SALES = [
    (6, [("SHIRT", 1), ("SOCKS", 2)], None, "cash", None),
    (4, [("LAWN", 1)], 1, "card", None),
    (3, [("JEANS", 1), ("BELT", 1)], None, "wallet", None),
    (1, [("SHIRT", 2), ("CAP", 1)], 0, "cash", "1000.00"),
    (0, [("KURTA", 1), ("SOCKS", 3)], None, "cash", None),
]


async def start(*, now: datetime | None = None) -> TokenOut:
    """Create the shop, seed it, and return the owner's session."""
    tenant_id, user_id = uuid.uuid4(), uuid.uuid4()
    expires = (now or datetime.now(timezone.utc)) + timedelta(hours=settings.DEMO_HOURS)
    password_hash = await ahash_password(secrets.token_urlsafe(24))  # nobody ever signs in with a password

    async with anonymous_session() as session:
        await apply_context(session, tenant_id=tenant_id, user_id=user_id)
        user = User(
            id=user_id,
            email=f"demo-{secrets.token_hex(6)}@{DEMO_EMAIL_DOMAIN}",
            hashed_password=password_hash,
            name="Demo owner",
        )
        session.add(user)
        session.add(
            Tenant(
                id=tenant_id,
                name="Demo Shop",
                slug=f"demo-{secrets.token_hex(4)}",
                city="Karachi",
                demo_expires_at=expires,
                agent_cap_usd=Decimal(str(settings.DEMO_AGENT_CAP_USD)),
            )
        )
        await session.flush()
        session.add(Membership(tenant_id=tenant_id, user_id=user_id, role=TenantRole.owner.value))
        record_audit(
            session, "demo.started", tenant_id=tenant_id, actor_id=user_id, entity="tenant", entity_id=tenant_id
        )
        tokens = await session_service.issue_tokens(session, user, tenant_id, TenantRole.owner)

    await _seed(Principal(user_id=user_id, tenant_id=tenant_id, role=TenantRole.owner), now=now)
    return tokens


async def _seed(principal: Principal, *, now: datetime | None) -> None:
    async with tenant_session(principal.tenant_id, principal.user_id) as db:
        products = {}
        for sku, name, category, price, cost, stock, reorder in PRODUCTS:
            made = await product_service.create_product(
                db,
                principal,
                ProductCreate(
                    sku=sku,
                    name=name,
                    category=category,
                    price=Decimal(price),
                    cost=Decimal(cost) if cost else None,
                    qty_on_hand=stock,
                    reorder_level=reorder,
                ),
            )
            products[sku] = made.id
        customers = [
            (await customer_service.create_customer(db, principal, CustomerCreate(phone=phone, name=name))).id
            for phone, name in CUSTOMERS
        ]
        for days_ago, lines, who, method, paid in SALES:
            body = SaleCreate(
                items=[SaleLine(product_id=products[sku], qty=qty) for sku, qty in lines],
                customer_id=customers[who] if who is not None else None,
                payment_method=method,  # type: ignore[arg-type]
                amount_paid=Decimal(paid) if paid else None,
            )
            order, _ = await order_service.post_sale(db, principal, body, idempotency_key=None)
            if days_ago:
                await db.execute(
                    text("UPDATE orders SET created_at = created_at - make_interval(days => :d) WHERE id = :id"),
                    {"d": days_ago, "id": order.id},
                )
