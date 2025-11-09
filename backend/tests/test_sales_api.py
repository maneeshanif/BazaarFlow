import sys
from pathlib import Path
import json

import pytest
from fastapi.testclient import TestClient


# Ensure backend package dir is importable
HERE = Path(__file__).resolve().parent
BACKEND_DIR = HERE.parent
sys.path.insert(0, str(BACKEND_DIR))

import app as app_module


class DummyResp:
    def __init__(self):
        self.id = "dummy-startup-id"


class DummyWA:
    async def send_message(self, *args, **kwargs):
        return DummyResp()


def clear_orders_file():
    orders_file = BACKEND_DIR / "data" / "sales_orders.json"
    if orders_file.exists():
        orders_file.unlink()


@pytest.fixture(autouse=True)
def cleanup_before_and_after():
    # Ensure a clean state for each test
    clear_orders_file()
    yield
    clear_orders_file()


def test_create_and_list_sales(monkeypatch):
    # Replace wa to avoid network calls during app startup
    monkeypatch.setattr(app_module, "wa", DummyWA())

    client = TestClient(app_module.fastapi_app)

    payload = {
        "customer_name": "Test User",
        "customer_phone": "+923001112233",
        "product_id": "sku-test-1",
        "product_name": "Test Product",
        "quantity": 2,
        "budget": "1000-2000",
        "payment_status": "pending",
        "delivery_address": "Lahore",
        "notes": "No rush"
    }

    # Create order
    res = client.post("/api/sales", json=payload)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body.get("ok") is True
    order = body.get("order")
    assert order is not None
    assert order["customer_name"] == payload["customer_name"]
    assert order["product_id"] == payload["product_id"]
    assert "id" in order

    # List orders
    res2 = client.get("/api/sales")
    assert res2.status_code == 200, res2.text
    body2 = res2.json()
    assert body2.get("ok") is True
    orders = body2.get("orders")
    assert isinstance(orders, list)
    assert any(o["id"] == order["id"] for o in orders)

    # Verify persistence file exists and contains the order
    orders_file = BACKEND_DIR / "data" / "sales_orders.json"
    assert orders_file.exists()
    with orders_file.open("r", encoding="utf-8") as f:
        saved = json.load(f)
    assert any(o["id"] == order["id"] for o in saved)
