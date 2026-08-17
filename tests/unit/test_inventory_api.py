"""Test inventory management API endpoints."""
import sys
from pathlib import Path
from types import SimpleNamespace
import importlib

import pytest
from fastapi.testclient import TestClient

HERE = Path(__file__).resolve().parent
BACKEND_DIR = HERE.parent
sys.path.insert(0, str(BACKEND_DIR))

import app as app_module

chat_service_module = importlib.import_module("services.chat_service")


class DummyResp:
    def __init__(self):
        self.id = "dummy-startup-id"


class DummyWA:
    async def send_message(self, *args, **kwargs):
        return DummyResp()


@pytest.fixture(autouse=True)
def patch_wa(monkeypatch):
    monkeypatch.setattr(app_module, "wa", DummyWA())


def test_inventory_chat_endpoint(monkeypatch):
    async def fake_run(*args, **kwargs):
        return SimpleNamespace(final_output="📦 Stock looks healthy!")

    monkeypatch.setattr(chat_service_module.Runner, "run", fake_run)

    client = TestClient(app_module.fastapi_app)

    payload = {"message": "Show low stock"}

    res = client.post("/api/chat/inventory", json=payload)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["response"].startswith("📦")
    assert body["session_id"].startswith("web_inventory")


# ============ INVENTORY CRUD API TESTS ============

def test_get_all_inventory():
    """Test GET /api/inventory - should return all items."""
    client = TestClient(app_module.fastapi_app)
    response = client.get("/api/inventory")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "items" in data
    assert isinstance(data["items"], list)
    print(f"✅ Found {len(data['items'])} inventory items")


def test_get_inventory_item():
    """Test GET /api/inventory/{sku} - should return specific item."""
    client = TestClient(app_module.fastapi_app)
    # First get all items to find a valid SKU
    response = client.get("/api/inventory")
    items = response.json()["items"]
    
    if items:
        test_sku = items[0]["sku"]
        response = client.get(f"/api/inventory/{test_sku}")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["item"]["sku"] == test_sku
        print(f"✅ Retrieved item: {data['item']['name']}")


def test_get_nonexistent_item():
    """Test GET /api/inventory/{sku} with invalid SKU - should return 404."""
    client = TestClient(app_module.fastapi_app)
    response = client.get("/api/inventory/INVALID-SKU-123")
    assert response.status_code == 404


def test_create_inventory_item():
    """Test POST /api/inventory - should create new item."""
    client = TestClient(app_module.fastapi_app)
    new_item = {
        "sku": "TEST-CREATE-001",
        "name": "Test Product",
        "category": "Test Category",
        "price": 999.99,
        "stock": 100,
        "reorder_point": 20,
        "incoming": 50,
        "supplier": "Test Supplier"
    }
    
    response = client.post("/api/inventory", json=new_item)
    assert response.status_code == 201
    data = response.json()
    assert data["ok"] is True
    assert data["item"]["sku"] == new_item["sku"]
    assert data["item"]["name"] == new_item["name"]
    assert "last_restocked" in data["item"]
    print(f"✅ Created item: {data['item']['name']}")


def test_create_duplicate_sku():
    """Test POST /api/inventory with duplicate SKU - should return 400."""
    client = TestClient(app_module.fastapi_app)
    # Get existing SKU
    response = client.get("/api/inventory")
    items = response.json()["items"]
    
    if items:
        duplicate_item = {
            "sku": items[0]["sku"],
            "name": "Duplicate Test",
            "category": "Test",
            "price": 100,
            "stock": 10,
            "reorder_point": 5,
            "incoming": 0,
            "supplier": "Test"
        }
        response = client.post("/api/inventory", json=duplicate_item)
        assert response.status_code == 400


def test_update_inventory_item():
    """Test PUT /api/inventory/{sku} - should update item fields."""
    client = TestClient(app_module.fastapi_app)
    # First create a test item
    test_sku = "TEST-UPDATE-001"
    new_item = {
        "sku": test_sku,
        "name": "Original Name",
        "category": "Original Category",
        "price": 500,
        "stock": 50,
        "reorder_point": 10,
        "incoming": 0,
        "supplier": "Original Supplier"
    }
    client.post("/api/inventory", json=new_item)
    
    # Update the item
    updates = {
        "name": "Updated Name",
        "price": 750
    }
    response = client.put(f"/api/inventory/{test_sku}", json=updates)
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["item"]["name"] == "Updated Name"
    assert data["item"]["price"] == 750
    assert data["item"]["category"] == "Original Category"  # Should remain unchanged
    print(f"✅ Updated item: {data['item']['name']}")


def test_update_nonexistent_item():
    """Test PUT /api/inventory/{sku} with invalid SKU - should return 404."""
    client = TestClient(app_module.fastapi_app)
    updates = {"name": "Test"}
    response = client.put("/api/inventory/INVALID-SKU-999", json=updates)
    assert response.status_code == 404


def test_add_stock():
    """Test PATCH /api/inventory/{sku}/add-stock - should increment stock."""
    client = TestClient(app_module.fastapi_app)
    # First create a test item
    test_sku = "TEST-STOCK-001"
    new_item = {
        "sku": test_sku,
        "name": "Stock Test Product",
        "category": "Test",
        "price": 100,
        "stock": 50,
        "reorder_point": 10,
        "incoming": 0,
        "supplier": "Test Supplier"
    }
    client.post("/api/inventory", json=new_item)
    
    # Add stock
    add_quantity = 30
    response = client.patch(
        f"/api/inventory/{test_sku}/add-stock",
        json={"quantity": add_quantity}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["item"]["stock"] == 50 + add_quantity
    assert "last_restocked" in data["item"]
    print(f"✅ Added {add_quantity} units, new stock: {data['item']['stock']}")


def test_add_stock_invalid_quantity():
    """Test PATCH /api/inventory/{sku}/add-stock with negative quantity - should return 400."""
    client = TestClient(app_module.fastapi_app)
    response = client.get("/api/inventory")
    items = response.json()["items"]
    
    if items:
        test_sku = items[0]["sku"]
        response = client.patch(
            f"/api/inventory/{test_sku}/add-stock",
            json={"quantity": -10}
        )
        assert response.status_code == 400


def test_add_stock_nonexistent_item():
    """Test PATCH /api/inventory/{sku}/add-stock with invalid SKU - should return 404."""
    client = TestClient(app_module.fastapi_app)
    response = client.patch(
        "/api/inventory/INVALID-SKU-777/add-stock",
        json={"quantity": 10}
    )
    assert response.status_code == 404


def test_delete_inventory_item():
    """Test DELETE /api/inventory/{sku} - should remove existing item."""
    client = TestClient(app_module.fastapi_app)

    test_sku = "TEST-DELETE-001"
    new_item = {
        "sku": test_sku,
        "name": "Delete Me",
        "category": "Disposable",
        "price": 50,
        "stock": 5,
        "reorder_point": 2,
        "incoming": 0,
        "supplier": "Temp Supplier",
    }
    client.post("/api/inventory", json=new_item)

    delete_response = client.delete(f"/api/inventory/{test_sku}")
    assert delete_response.status_code == 200
    body = delete_response.json()
    assert body["ok"] is True
    assert body["item"]["sku"] == test_sku

    follow_up = client.get(f"/api/inventory/{test_sku}")
    assert follow_up.status_code == 404


def test_delete_nonexistent_item():
    """Test DELETE /api/inventory/{sku} with invalid SKU - should return 404."""
    client = TestClient(app_module.fastapi_app)
    response = client.delete("/api/inventory/INVALID-SKU-DELETE")
    assert response.status_code == 404
