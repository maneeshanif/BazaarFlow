"""Inventory analytics utilities used by the inventory agent."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime

from .notification_service import notification_service

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = BASE_DIR / "data" / "inventory_items.json"


@dataclass(frozen=True)
class StockBucket:
    count: int
    total_units: int

    def as_dict(self) -> Dict[str, int]:
        return {"count": self.count, "total_units": self.total_units}


class InventoryAnalyticsService:
    """Provide derived metrics for inventory planning."""

    def __init__(self, data_path: Optional[Path] = None) -> None:
        self._data_path = Path(data_path) if data_path else DEFAULT_DATASET
        self._cache: Optional[List[dict]] = None

    def _ensure_cache(self) -> List[dict]:
        if self._cache is None:
            with self._data_path.open("r", encoding="utf-8") as handle:
                self._cache = json.load(handle)
        return self._cache

    def refresh(self) -> None:
        self._cache = None

    def _classify_bucket(self, stock: int, reorder_point: int) -> str:
        if stock <= 0:
            return "out_of_stock"
        if stock <= reorder_point:
            return "low_stock"
        return "in_stock"

    def get_stock_health(self) -> Dict[str, Dict[str, int]]:
        buckets: Dict[str, Dict[str, int]] = {
            "in_stock": {"count": 0, "total_units": 0},
            "low_stock": {"count": 0, "total_units": 0},
            "out_of_stock": {"count": 0, "total_units": 0},
        }

        for item in self._ensure_cache():
            stock = int(item.get("stock", 0))
            reorder_point = int(item.get("reorder_point", 0))
            key = self._classify_bucket(stock, reorder_point)
            bucket = buckets[key]
            bucket["count"] += 1
            bucket["total_units"] += max(stock, 0)

        return buckets

    def get_stock_health_detail(self) -> Dict[str, Dict[str, object]]:
        detail: Dict[str, Dict[str, object]] = {
            "in_stock": {"count": 0, "total_units": 0, "items": []},
            "low_stock": {"count": 0, "total_units": 0, "items": []},
            "out_of_stock": {"count": 0, "total_units": 0, "items": []},
        }

        for item in self._ensure_cache():
            stock = int(item.get("stock", 0))
            reorder_point = int(item.get("reorder_point", 0))
            key = self._classify_bucket(stock, reorder_point)

            bucket = detail[key]
            bucket["count"] += 1
            bucket["total_units"] += max(stock, 0)
            bucket["items"].append(
                {
                    "name": item.get("name", "Unknown"),
                    "stock": stock,
                    "incoming": int(item.get("incoming", 0)),
                }
            )

        return detail

    def get_category_breakdown(self) -> Dict[str, Dict[str, int]]:
        totals: Dict[str, StockBucket] = {}

        for item in self._ensure_cache():
            category = item.get("category", "uncategorized")
            stock = int(item.get("stock", 0))

            bucket = totals.get(category)
            if bucket is None:
                totals[category] = StockBucket(1, stock)
            else:
                totals[category] = StockBucket(bucket.count + 1, bucket.total_units + stock)

        return {key: bucket.as_dict() for key, bucket in totals.items()}

    def get_restock_queue(self, *, limit: int = 5) -> List[dict]:
        if limit <= 0:
            return []

        candidates = [
            item
            for item in self._ensure_cache()
            if int(item.get("stock", 0)) <= int(item.get("reorder_point", 0))
        ]

        candidates.sort(
            key=lambda item: (
                int(item.get("stock", 0)),
                int(item.get("reorder_point", 0)),
                item.get("sku", ""),
            )
        )
        return candidates[:limit]

    def get_items_by_category(self, category: str) -> List[dict]:
        category_lower = category.lower()
        return [
            item
            for item in self._ensure_cache()
            if item.get("category", "").lower() == category_lower
        ]

    def get_all_items(self, *, limit: Optional[int] = None) -> List[dict]:
        items = list(self._ensure_cache())
        if limit is not None and limit >= 0:
            return items[:limit]
        return items

    def get_incoming_summary(self, *, limit: int = 3) -> List[dict]:
        if limit <= 0:
            return []

        items = sorted(
            self._ensure_cache(),
            key=lambda item: int(item.get("incoming", 0)),
            reverse=True,
        )
        return items[:limit]

    def get_last_restocked(self, *, limit: int = 5) -> List[dict]:
        if limit <= 0:
            return []

        def parse_date(value: str) -> datetime:
            try:
                return datetime.fromisoformat(value)
            except Exception:
                return datetime.min

        items = sorted(
            self._ensure_cache(),
            key=lambda item: parse_date(item.get("last_restocked", "")),
        )
        return items[:limit]

    def search_items(self, query: str, *, limit: int = 10) -> List[dict]:
        if not query:
            return []

        query_lower = query.strip().lower()
        matches = [
            item
            for item in self._ensure_cache()
            if query_lower in item.get("name", "").lower()
        ]
        return matches[:limit]

    def _locate_item(
        self,
        *,
        sku: Optional[str] = None,
        product_name: Optional[str] = None,
    ) -> Tuple[int, dict]:
        """Return (index, item) for the first match by SKU or product name."""

        items = list(self._ensure_cache())

        if sku:
            for index, item in enumerate(items):
                if item.get("sku", "").lower() == sku.lower():
                    return index, dict(item)

        if product_name:
            target = product_name.lower()
            for index, item in enumerate(items):
                if item.get("name", "").lower() == target:
                    return index, dict(item)

        identifier = sku or product_name or "product"
        raise ValueError(f"{identifier} is not available in inventory")

    def reserve_stock(
        self,
        *,
        quantity: int,
        sku: Optional[str] = None,
        product_name: Optional[str] = None,
    ) -> dict:
        """Decrease on-hand stock for a product while preventing negative counts."""

        if quantity <= 0:
            raise ValueError("Quantity must be at least 1")

        items = [dict(item) for item in self._ensure_cache()]
        index, item = self._locate_item(sku=sku, product_name=product_name)

        # Keep a copy for threshold comparison
        previous_item = dict(item)

        current_stock = int(item.get("stock", 0))
        if quantity > current_stock:
            product_label = item.get("name") or sku or product_name or "product"
            raise ValueError(
                f"Only {current_stock} unit(s) of {product_label} available in stock"
            )

        updated_item = {**item, "stock": current_stock - quantity}
        items[index] = updated_item
        self._write_all(items)

        # Emit notifications if thresholds were crossed
        self._emit_threshold_notifications(previous_item, updated_item)

        return updated_item

    def _write_all(self, items: List[dict]) -> None:
        """Write all items back to the JSON file."""
        with self._data_path.open("w", encoding="utf-8") as handle:
            json.dump(items, handle, ensure_ascii=False, indent=2)
        self._cache = None  # Clear cache to force reload

    def create_item(self, item_data: dict) -> dict:
        """Create a new inventory item."""
        items = self._ensure_cache().copy()
        
        # Check if SKU already exists
        sku = item_data.get("sku")
        if any(item.get("sku") == sku for item in items):
            raise ValueError(f"Item with SKU {sku} already exists")
        
        # Add last_restocked if not provided
        if "last_restocked" not in item_data:
            item_data["last_restocked"] = datetime.now().isoformat()
        
        items.append(item_data)
        self._write_all(items)
        return item_data

    def update_item(self, sku: str, item_data: dict) -> Optional[dict]:
        """Update an existing inventory item."""
        items = self._ensure_cache().copy()

        for i, item in enumerate(items):
            if item.get("sku") == sku:
                previous_item = dict(item)
                # Update fields but keep SKU
                updated_item = {**item, **item_data, "sku": sku}
                items[i] = updated_item
                self._write_all(items)

                # Emit notifications when stock/reorder thresholds change
                self._emit_threshold_notifications(previous_item, updated_item)

                return updated_item
        
        return None

    def add_stock(self, sku: str, quantity: int) -> Optional[dict]:
        """Increase stock for an item and emit threshold notifications if needed."""

        if quantity <= 0:
            raise ValueError("Quantity must be at least 1")

        items = self._ensure_cache().copy()

        for i, item in enumerate(items):
            if item.get("sku") == sku:
                previous_item = dict(item)
                current_stock = int(item.get("stock", 0))
                updated_item = {**item, "stock": current_stock + quantity}
                items[i] = updated_item
                self._write_all(items)

                # Adding stock might move an item out of a low/out-of-stock state.
                # We currently only emit notifications when entering low/out-of-stock,
                # so no notification is required here, but we keep the hook for
                # symmetry or future use.
                self._emit_threshold_notifications(previous_item, updated_item)

                return updated_item

        return None

    def delete_item(self, sku: str) -> Optional[dict]:
        """Delete an item from inventory dataset."""

        items = self._ensure_cache().copy()
        deleted: Optional[dict] = None
        remaining: List[dict] = []
        for item in items:
            if item.get("sku") == sku and deleted is None:
                deleted = dict(item)
                continue
            remaining.append(item)

        if deleted is None:
            return None

        self._write_all(remaining)
        return deleted

    def get_item_by_sku(self, sku: str) -> Optional[dict]:
        """Fetch a single inventory item by SKU."""

        for item in self._ensure_cache():
            if item.get("sku") == sku:
                return dict(item)
        return None

    def _emit_threshold_notifications(self, previous: dict, updated: dict) -> None:
        """Compare previous vs updated and create notifications on threshold crossings.

        Rules:
        - When an item moves from in_stock -> low_stock: create a low-stock warning.
        - When an item moves into out_of_stock from any other bucket: create an
          out-of-stock error notification.
        """

        try:
            prev_stock = int(previous.get("stock", 0))
            prev_reorder = int(previous.get("reorder_point", 0))
            new_stock = int(updated.get("stock", 0))
            new_reorder = int(updated.get("reorder_point", 0))

            prev_bucket = self._classify_bucket(prev_stock, prev_reorder)
            new_bucket = self._classify_bucket(new_stock, new_reorder)

            if prev_bucket == new_bucket:
                return

            name = updated.get("name") or previous.get("name") or "Unknown item"
            sku = updated.get("sku") or previous.get("sku")

            metadata = {
                "sku": sku,
                "name": name,
                "previous_stock": prev_stock,
                "new_stock": new_stock,
                "reorder_point": new_reorder,
                "bucket_from": prev_bucket,
                "bucket_to": new_bucket,
            }

            if new_bucket == "low_stock" and prev_bucket == "in_stock":
                title = f"Low stock: {name}"
                message = f"Only {new_stock} unit(s) left. Reorder point: {new_reorder}."
                notification_service.create_notification(
                    type="inventory_low_stock",
                    title=title,
                    message=message,
                    severity="warning",
                    metadata=metadata,
                )
            elif new_bucket == "out_of_stock" and prev_bucket != "out_of_stock":
                title = f"Out of stock: {name}"
                message = "This item has run out of stock. Consider updating incoming shipments."
                notification_service.create_notification(
                    type="inventory_out_of_stock",
                    title=title,
                    message=message,
                    severity="error",
                    metadata=metadata,
                )
        except Exception:
            # Notifications must never break core inventory flows.
            return

    def add_stock(self, sku: str, quantity: int) -> Optional[dict]:
        """Add stock to an existing item."""
        items = self._ensure_cache().copy()
        
        for i, item in enumerate(items):
            if item.get("sku") == sku:
                item["stock"] = int(item.get("stock", 0)) + quantity
                item["last_restocked"] = datetime.now().isoformat()
                
                items[i] = item
                self._write_all(items)
                return item
        
        return None

    def get_item_by_sku(self, sku: str) -> Optional[dict]:
        """Get a specific item by SKU."""
        for item in self._ensure_cache():
            if item.get("sku") == sku:
                return item
        return None

    def delete_item(self, sku: str) -> Optional[dict]:
        """Remove an inventory item by SKU."""
        items = self._ensure_cache().copy()

        for index, item in enumerate(items):
            if item.get("sku") == sku:
                removed = items.pop(index)
                self._write_all(items)
                return removed

        return None


inventory_analytics_service = InventoryAnalyticsService()
