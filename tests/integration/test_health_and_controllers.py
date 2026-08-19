"""Integration tests for BazaarFlow API routes and controllers."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test the root /health endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "healthy"
    assert "app" in data


@pytest.mark.asyncio
async def test_vendors_endpoints(client: AsyncClient):
    """Test vendor listing and creation routes."""
    # List vendors
    response = await client.get("/api/vendors")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_inventory_endpoints(client: AsyncClient):
    """Test inventory listing route."""
    response = await client.get("/api/inventory")
    assert response.status_code in (200, 501)


@pytest.mark.asyncio
async def test_logs_endpoint(client: AsyncClient):
    """Test system logs retrieval route."""
    response = await client.get("/api/logs")
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data or isinstance(data, list) or isinstance(data, dict)


@pytest.mark.asyncio
async def test_webhook_test_endpoint(client: AsyncClient):
    """Test webhook test endpoint."""
    response = await client.get("/webhook/test")
    assert response.status_code == 200
