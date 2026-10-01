"""The seed command creates one demo tenant, is idempotent, and its login works (PRD §12.4)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.cli.seed import DEMO_EMAIL, seed_database

pytestmark = pytest.mark.pg


async def test_seed_creates_a_demo_tenant_once(
    client: AsyncClient, app_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEMO_USER_PASSWORD", "demo-password-123")
    await seed_database()
    await seed_database()  # idempotent: no second tenant, no error

    login = await client.post("/api/v1/auth/login", json={"email": DEMO_EMAIL, "password": "demo-password-123"})
    assert login.status_code == 200, login.text
    assert login.json()["role"] == "owner"
    token = {"Authorization": f"Bearer {login.json()['access_token']}"}

    customers = (await client.get("/api/v1/customers/", headers=token)).json()
    assert sorted(c["name"] for c in customers) == ["Ali Raza", "Sara Khan"]
    me = (await client.get("/api/v1/auth/me", headers=token)).json()
    assert [m["tenant_name"] for m in me["memberships"]] == ["Demo Retail"]
