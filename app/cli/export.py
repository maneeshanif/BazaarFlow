"""Data export CLI command.

Exports one tenant's data (Orders, Inventory, Customers) to CSV or JSON. The tenant id is required
because row-level security hides every other tenant's rows (PRD §3.5).

Usage:
    python -m app.cli.export --tenant-id <uuid> --table inventory --format csv
    python -m app.cli.export --tenant-id <uuid> --table orders --format json
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import uuid
from pathlib import Path
from typing import Any, List

from sqlalchemy import select

from app.core.tenancy import tenant_session
from app.crud.soft_delete import live
from app.models.customer import Customer
from app.models.inventory import InventoryItem
from app.models.order import Order

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("bazaarflow.export")


async def export_data(
    tenant_id: uuid.UUID, table_name: str, export_format: str, output_path: str | None = None
) -> None:
    async with tenant_session(tenant_id) as session:
        records: List[dict[str, Any]] = []

        if table_name == "inventory":
            result = await session.execute(select(InventoryItem).where(InventoryItem.tenant_id == tenant_id, live(InventoryItem)))
            items = result.scalars().all()
            records = [
                {
                    "sku": item.sku,
                    "name": item.name,
                    "price": item.price,
                    "stock_count": item.stock_count,
                    "category": item.category,
                }
                for item in items
            ]
        elif table_name == "orders":
            result = await session.execute(select(Order).where(Order.tenant_id == tenant_id))
            orders = result.scalars().all()
            records = [
                {
                    "id": str(order.id),
                    "tenant_id": str(order.tenant_id),
                    "product_name": order.product_name,
                    "quantity": order.quantity,
                    "payment_status": order.payment_status,
                    "created_at": order.created_at.isoformat() if order.created_at else None,
                }
                for order in orders
            ]
        elif table_name == "customers":
            result = await session.execute(select(Customer).where(Customer.tenant_id == tenant_id, live(Customer)))
            customers = result.scalars().all()
            records = [
                {
                    "id": str(c.id),
                    "tenant_id": str(c.tenant_id),
                    "name": c.name,
                    "phone": c.phone,
                }
                for c in customers
            ]
        else:
            logger.error("Unknown table: %s. Options: inventory, orders, customers", table_name)
            return

        if not records:
            logger.warning("No records found to export for table '%s'.", table_name)
            return

        filename = output_path or f"{table_name}_export.{export_format}"
        file_path = Path(filename)

        if export_format == "json":
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, default=str)
            logger.info("Exported %d records to %s", len(records), file_path)
        elif export_format == "csv":
            keys = records[0].keys()
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(records)
            logger.info("Exported %d records to %s", len(records), file_path)


def main():
    parser = argparse.ArgumentParser(description="Export BazaarFlow database data")
    parser.add_argument("--tenant-id", type=uuid.UUID, required=True, help="Tenant whose data to export")
    parser.add_argument("--table", choices=["inventory", "orders", "customers"], required=True, help="Table to export")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Export format (default: csv)")
    parser.add_argument("--output", default=None, help="Output file path")
    args = parser.parse_args()

    asyncio.run(export_data(args.tenant_id, args.table, args.format, args.output))


if __name__ == "__main__":
    main()