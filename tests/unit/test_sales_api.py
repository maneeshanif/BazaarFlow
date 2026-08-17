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
import services.inventory_service as inventory_service
import services.sales_service as sales_service


class DummyResp:
    def __init__(self):
        self.id = "dummy-startup-id"


class DummyWA:
    async def send_message(self, *args, **kwargs):
        return DummyResp()


@pytest.fixture
def sales_test_env(tmp_path, monkeypatch):
    inventory_file = tmp_path / "inventory.json"
    inventory_payload = [
        {
            "sku": "sku-test-1",
            "name": "Test Product",
            "category": "test",
            "price": 1500,
            "stock": 5,
            "reorder_point": 1,
            "incoming": 0,
            "supplier": "Test Supplier",
            "last_restocked": "2024-01-01",
        }
    ]
    inventory_file.write_text(json.dumps(inventory_payload), encoding="utf-8")

    test_inventory = inventory_service.InventoryAnalyticsService(data_path=inventory_file)
    monkeypatch.setattr(inventory_service, "inventory_analytics_service", test_inventory)
    monkeypatch.setattr(sales_service, "inventory_analytics_service", test_inventory)

    orders_file = tmp_path / "sales_orders.json"
    monkeypatch.setattr(sales_service, "ORDERS_FILE", orders_file)

    return orders_file


def test_create_and_list_sales(monkeypatch, sales_test_env):
    # Replace wa to avoid network calls during app startup
    monkeypatch.setattr(app_module, "wa", DummyWA())

    client = TestClient(app_module.fastapi_app)

    payload = {
        "customer_name": "Test User",
        "customer_phone": "+923001112233",
        "product_id": "",  # sales service should resolve SKU
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
    assert order["product_id"] == "sku-test-1"
    snapshot = order.get("inventory_snapshot")
    assert snapshot["remaining_stock"] == 3
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
    orders_file = sales_test_env
    assert orders_file.exists()
    with orders_file.open("r", encoding="utf-8") as f:
        saved = json.load(f)
    assert any(o["id"] == order["id"] for o in saved)
