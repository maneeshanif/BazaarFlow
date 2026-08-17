import json
from pathlib import Path
from typing import Any, Dict

from .inventory_service import inventory_analytics_service

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ORDERS_FILE = DATA_DIR / "sales_orders.json"


def _read_all() -> list:
    if not ORDERS_FILE.exists():
        return []
    try:
        with ORDERS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _write_all(items: list) -> None:
    with ORDERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def _persist_order(payload: Dict[str, Any]) -> Dict[str, Any]:
    items = _read_all()
    next_id = (items[-1]["id"] + 1) if items else 1
    record = {"id": next_id, **payload}
    items.append(record)
    _write_all(items)
    return dict(record)


def save_order(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = {**payload}
    quantity = int(data.get("quantity", 0) or 0)
    if quantity <= 0:
        raise ValueError("Quantity must be at least 1")

    sku = data.get("product_id") or None
    product_name = data.get("product_name") or None

    reserved_item = inventory_analytics_service.reserve_stock(
        quantity=quantity,
        sku=sku,
        product_name=product_name,
    )

    if not sku:
        data["product_id"] = reserved_item.get("sku", "")
    if not data.get("product_name"):
        data["product_name"] = reserved_item.get("name")

    stored = _persist_order(data)
    return {
        **stored,
        "inventory_snapshot": {
            "sku": reserved_item.get("sku"),
            "name": reserved_item.get("name"),
            "remaining_stock": reserved_item.get("stock"),
        },
    }


def list_orders() -> list:
    return _read_all()
