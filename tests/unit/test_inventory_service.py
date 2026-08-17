import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
BACKEND_DIR = HERE.parent
sys.path.insert(0, str(BACKEND_DIR))

from services.inventory_service import InventoryAnalyticsService


@pytest.fixture(scope="module")
def inventory_service():
    data_path = BACKEND_DIR / "data" / "inventory_items.json"
    return InventoryAnalyticsService(data_path=data_path)


def test_stock_health(inventory_service):
    overview = inventory_service.get_stock_health()

    assert overview["in_stock"]["count"] == 4
    assert overview["in_stock"]["total_units"] == 46

    assert overview["low_stock"]["count"] == 3
    assert overview["low_stock"]["total_units"] == 12

    assert overview["out_of_stock"]["count"] == 1
    assert overview["out_of_stock"]["total_units"] == 0


def test_stock_health_detail(inventory_service):
    detail = inventory_service.get_stock_health_detail()
    in_stock_names = {item["name"] for item in detail["in_stock"]["items"]}
    assert "iPhone 15" in in_stock_names


def test_category_breakdown(inventory_service):
    breakdown = inventory_service.get_category_breakdown()

    assert breakdown["mobile"]["count"] == 3
    assert breakdown["mobile"]["total_units"] == 21

    assert breakdown["computer"]["count"] == 2
    assert breakdown["computer"]["total_units"] == 9

    assert breakdown["audio"]["count"] == 1
    assert breakdown["audio"]["total_units"] == 18


def test_restock_queue(inventory_service):
    queue = inventory_service.get_restock_queue(limit=3)

    assert [item["sku"] for item in queue] == [
        "SKU-GALAXY-S24",
        "SKU-LOGI-MX4",
        "SKU-SURFACE-10",
    ]

    assert queue[0]["stock"] == 0
    assert queue[0]["incoming"] == 18


def test_search_items_case_insensitive(inventory_service):
    results = inventory_service.search_items("IPHONE")
    names = {item["name"] for item in results}
    assert "iPhone 15" in names
