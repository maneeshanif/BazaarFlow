"""Database seeding CLI command.

Migrates data from legacy JSON files (backend/db/, backend/data/) or seeds sample data
into the configured SQLAlchemy database.

Usage:
    python -m app.cli.seed
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List
import uuid

from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.models.vendor import Vendor
from app.models.customer import Customer
from app.models.inventory import InventoryItem
from app.models.order import Order
from app.models.support import SupportTicket
from app.core.security import hash_password

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("bazaarflow.seed")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DB_DIR = ROOT_DIR / "backend" / "db"
BACKEND_DATA_DIR = ROOT_DIR / "backend" / "data"


def load_json(filepath: Path) -> List[Dict[str, Any]]:
    if filepath.exists():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else [data]
        except Exception as e:
            logger.warning("Could not read %s: %s", filepath, e)
    return []


async def seed_database() -> None:
    """Run the database seeding process."""
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # 1. Seed Users
        existing_user = await session.execute(select(User))
        user = existing_user.scalars().first()
        if not user:
            logger.info("Seeding users...")
            users_data = load_json(BACKEND_DB_DIR / "users.json")
            if not users_data:
                users_data = [
                    {"email": "admin@bazaarflow.com", "password": "adminpassword123"}
                ]
            for u in users_data:
                user = User(
                    email=u.get("email", "admin@bazaarflow.com"),
                    hashed_password=hash_password(u.get("password", "adminpassword123")),
                )
                session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info("Users seeded.")

        user_id = str(user.id) if user else str(uuid.uuid4())

        # 2. Seed Vendors
        existing_vendor = await session.execute(select(Vendor))
        vendor = existing_vendor.scalars().first()
        if not vendor:
            logger.info("Seeding vendors...")
            vendors_data = load_json(BACKEND_DB_DIR / "vendors.json")
            if not vendors_data:
                vendors_data = [
                    {
                        "name": "BazaarFlow Demo Store",
                        "phone_number_id": "100234567890",
                        "settings": {"currency": "PKR", "auto_reply": True},
                    }
                ]
            for v in vendors_data:
                vendor = Vendor(
                    user_id=user_id,
                    name=v.get("name", "Demo Vendor"),
                    phone_number_id=v.get("phone_number_id", v.get("phone_number", "100234567890")),
                    settings=v.get("settings", {}),
                )
                session.add(vendor)
            await session.commit()
            await session.refresh(vendor)
            logger.info("Vendors seeded.")

        vendor_id = str(vendor.id) if vendor else str(uuid.uuid4())

        # 3. Seed Inventory
        existing_inv = await session.execute(select(InventoryItem))
        if not existing_inv.scalars().first():
            logger.info("Seeding inventory items...")
            inv_data = load_json(BACKEND_DATA_DIR / "inventory_items.json")
            if not inv_data:
                inv_data = [
                    {"sku": "SHIRT-001", "name": "Classic Oxford Shirt", "price": "2500 PKR", "stock_count": 50, "category": "Apparel"},
                    {"sku": "JEANS-002", "name": "Slim Fit Denim", "price": "3800 PKR", "stock_count": 30, "category": "Apparel"},
                    {"sku": "SHOES-003", "name": "Leather Loafers", "price": "5500 PKR", "stock_count": 15, "category": "Footwear"},
                ]
            for item in inv_data:
                inv_obj = InventoryItem(
                    vendor_id=vendor_id,
                    sku=item.get("sku", f"SKU-{uuid.uuid4().hex[:6].upper()}"),
                    name=item.get("name", "Sample Product"),
                    price=str(item.get("price", "0")),
                    stock_count=int(item.get("stock_count", item.get("stock_level", 0))),
                    category=item.get("category", "General"),
                )
                session.add(inv_obj)
            await session.commit()
            logger.info("Inventory items seeded.")

        logger.info("Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_database())