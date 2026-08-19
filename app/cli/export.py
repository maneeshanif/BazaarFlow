"""Data export CLI command.

Exports database tables (Orders, Inventory, Customers) to CSV or JSON.

Usage:
    python -m app.cli.export --table inventory --format csv
    python -m app.cli.export --table orders --format json
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
from pathlib import Path
from typing import Any, List

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.inventory import InventoryItem
from app.models.order import Order
from app.models.customer import Customer
from app.models.vendor import Vendor

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("bazaarflow.export")


async def export_data(table_name: str, export_format: str, output_path: str | None = None) -> None:
    async with AsyncSessionLocal() as session:
        records: List[dict[str, Any]] = []

        if table_name == "inventory":
            result = await session.execute(select(InventoryItem))
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
            result = await session.execute(select(Order))
            orders = result.scalars().all()
            records = [
                {
                    "id": str(order.id),
                    "vendor_id": str(order.vendor_id),
                    "product_name": order.product_name,
                    "quantity": order.quantity,
                    "payment_status": order.payment_status,
                    "created_at": order.created_at.isoformat() if order.created_at else None,
                }
                for order in orders
            ]
        elif table_name == "customers":
            result = await session.execute(select(Customer))
            customers = result.scalars().all()
            records = [
                {
                    "id": str(c.id),
                    "vendor_id": str(c.vendor_id),
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
                json.dump(records, f, indent=2)
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
    parser.add_argument("--table", choices=["inventory", "orders", "customers"], required=True, help="Table to export")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Export format (default: csv)")
    parser.add_argument("--output", default=None, help="Output file path")
    args = parser.parse_args()

    asyncio.run(export_data(args.table, args.format, args.output))


if __name__ == "__main__":
    main()