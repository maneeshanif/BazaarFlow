"""Inventory analytics over a small, explicit dataset (tests/data/inventory_items.json).

The expected numbers can be derived by hand from the fixture:

* in stock (stock > reorder point): iPhone 15 (9), Pixel 8 (12), AirPods Pro (18), iPad (7)  -> 4 items, 46 units
* low stock (0 < stock <= reorder point): MacBook Air (5), Surface (4), Logitech MX (3)       -> 3 items, 12 units
* out of stock: Galaxy S24 (0)                                                               -> 1 item, 0 units
* categories: mobile 3 items / 21 units, computer 2 / 9, audio 1 / 18, accessory 1 / 3, tablet 1 / 7
* restock queue = items at or under their reorder point, lowest stock first (ties by reorder point, then sku)
"""
import shutil
from pathlib import Path
from typing import Any

import pytest

from app.services.inventory_service import InventoryAnalyticsService

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "inventory_items.json"


@pytest.fixture
def inventory_service(tmp_path: Any) -> Any:
    data_path = tmp_path / "inventory_items.json"
    shutil.copy(FIXTURE, data_path)  # never read or write the shared fixture in place
    return InventoryAnalyticsService(data_path=data_path)


def test_stock_health(inventory_service: Any) -> None:
    overview = inventory_service.get_stock_health()

    assert overview["in_stock"]["count"] == 4
    assert overview["in_stock"]["total_units"] == 46

    assert overview["low_stock"]["count"] == 3
    assert overview["low_stock"]["total_units"] == 12

    assert overview["out_of_stock"]["count"] == 1
    assert overview["out_of_stock"]["total_units"] == 0


def test_stock_health_detail(inventory_service: Any) -> None:
    detail = inventory_service.get_stock_health_detail()
    in_stock_names = {item["name"] for item in detail["in_stock"]["items"]}
    assert "iPhone 15" in in_stock_names


def test_category_breakdown(inventory_service: Any) -> None:
    breakdown = inventory_service.get_category_breakdown()

    assert breakdown["mobile"]["count"] == 3
    assert breakdown["mobile"]["total_units"] == 21

    assert breakdown["computer"]["count"] == 2
    assert breakdown["computer"]["total_units"] == 9

    assert breakdown["audio"]["count"] == 1
    assert breakdown["audio"]["total_units"] == 18


def test_restock_queue(inventory_service: Any) -> None:
    queue = inventory_service.get_restock_queue(limit=3)

    assert [item["sku"] for item in queue] == [
        "SKU-GALAXY-S24",
        "SKU-LOGI-MX4",
        "SKU-SURFACE-10",
    ]

    assert queue[0]["stock"] == 0
    assert queue[0]["incoming"] == 18


def test_search_items_case_insensitive(inventory_service: Any) -> None:
    results = inventory_service.search_items("IPHONE")
    names = {item["name"] for item in results}
    assert "iPhone 15" in names
