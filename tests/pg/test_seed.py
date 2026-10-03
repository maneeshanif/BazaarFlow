"""The seed command creates one demo tenant, is idempotent, and its login works (PRD §12.4)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.cli.seed import DEMO_EMAIL, DEMO_MANAGER_EMAIL, DEMO_STAFF_EMAIL, seed_database

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


async def test_role_users_are_created_only_on_request_and_only_once(
    client: AsyncClient, app_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Manager and staff logins let the role checks run against a real database (used by the Supabase e2e)."""
    monkeypatch.setenv("DEMO_USER_PASSWORD", "demo-password-123")
    await seed_database()
    absent = await client.post(
        "/api/v1/auth/login", json={"email": DEMO_MANAGER_EMAIL, "password": "demo-password-123"}
    )
    assert absent.status_code == 401, "role users must not exist unless asked for"

    monkeypatch.setenv("SEED_ROLE_USERS", "true")
    await seed_database()  # the demo tenant already exists: only the role users are added
    await seed_database()  # and again: still no duplicates, no error
    for email, role in ((DEMO_MANAGER_EMAIL, "manager"), (DEMO_STAFF_EMAIL, "staff")):
        login = await client.post("/api/v1/auth/login", json={"email": email, "password": "demo-password-123"})
        assert login.status_code == 200, login.text
        assert login.json()["role"] == role
