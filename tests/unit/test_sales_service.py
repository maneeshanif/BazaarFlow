import json

import pytest

from services import sales_service
from services.inventory_service import InventoryAnalyticsService


@pytest.fixture
def configured_sales_service(tmp_path, monkeypatch):
    inventory_file = tmp_path / "inventory.json"
    inventory_data = [
        {
            "sku": "SKU-TEST-123",
            "name": "Demo Item",
            "category": "demo",
            "price": 9999,
            "stock": 4,
            "reorder_point": 1,
            "incoming": 0,
            "supplier": "Demo",
            "last_restocked": "2024-01-01",
        }
    ]
    inventory_file.write_text(json.dumps(inventory_data), encoding="utf-8")

    inventory_instance = InventoryAnalyticsService(data_path=inventory_file)
    monkeypatch.setattr(sales_service, "inventory_analytics_service", inventory_instance)

    orders_file = tmp_path / "orders.json"
    monkeypatch.setattr(sales_service, "ORDERS_FILE", orders_file)

    return orders_file


def test_save_order_reserves_stock(configured_sales_service):
    result = sales_service.save_order(
        {
            "customer_name": "Customer",
            "customer_phone": "+920000000000",
            "product_name": "Demo Item",
            "quantity": 2,
            "delivery_address": "Karachi",
        }
    )

    snapshot = result["inventory_snapshot"]
    assert snapshot["remaining_stock"] == 2
    assert snapshot["sku"] == "SKU-TEST-123"

    stored = json.loads(configured_sales_service.read_text(encoding="utf-8"))
    assert stored[0]["product_id"] == "SKU-TEST-123"
    assert stored[0]["quantity"] == 2


def test_save_order_prevents_over_selling(configured_sales_service):
    with pytest.raises(ValueError) as excinfo:
        sales_service.save_order(
            {
                "customer_name": "Customer",
                "customer_phone": "+920000000000",
                "product_name": "Demo Item",
                "quantity": 10,
            }
        )

    assert "Only" in str(excinfo.value)
