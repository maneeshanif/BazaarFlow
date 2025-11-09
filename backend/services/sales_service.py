import json
from pathlib import Path
from typing import Dict, Any

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


def save_order(payload: Dict[str, Any]) -> Dict[str, Any]:
    items = _read_all()
    # add a simple incremental id
    next_id = (items[-1]["id"] + 1) if items else 1
    record = {"id": next_id, **payload}
    items.append(record)
    _write_all(items)
    return record


def list_orders() -> list:
    return _read_all()
