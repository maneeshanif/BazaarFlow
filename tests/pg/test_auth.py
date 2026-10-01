"""Authentication, roles and registration against real Postgres (PRD F-001, F-002, §14.2)."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from httpx import AsyncClient
from jose import jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.security import create_access_token
from app.core.settings import settings
from app.core.tenancy import apply_context
from tests.pg.conftest import bearer, register

pytestmark = pytest.mark.pg


def _claims(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])


async def test_register_creates_user_tenant_owner_membership_and_audit(
    client: AsyncClient, app_engine: AsyncEngine
) -> None:
    acct = await register(client, "Ali Mart")
    claims = _claims(acct["access_token"])
    assert claims["tenant_id"] == acct["tenant_id"]
    assert claims["role"] == "owner"
    assert acct["role"] == "owner"

    me = (await client.get("/api/v1/auth/me", headers=bearer(acct))).json()
    assert me["role"] == "owner"
    assert [m["tenant_name"] for m in me["memberships"]] == ["Ali Mart"]

    session = AsyncSession(app_engine)
    await session.begin()
    try:
        await apply_context(session, tenant_id=uuid.UUID(acct["tenant_id"]))
        actions = {r[0] for r in (await session.execute(text("SELECT action FROM audit_logs"))).all()}
        assert "tenant.registered" in actions
    finally:
        await session.rollback()
        await session.close()


async def test_register_rejects_duplicate_email_and_unaccepted_terms(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    payload = {
        "full_name": "Other Person",
        "email": acct["email"],
        "password": "another-long-password",
        "shop_name": "Second Shop",
        "phone": "+923001111111",
        "accept_terms": True,
    }
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 409
    payload["email"] = f"fresh-{uuid.uuid4().hex[:8]}@example.com"
    payload["accept_terms"] = False
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 422


async def test_login_returns_tenant_and_role_claims(client: AsyncClient) -> None:
    acct = await register(client, "Login Shop")
    res = await client.post("/api/v1/auth/login", json={"email": acct["email"], "password": acct["password"]})
    assert res.status_code == 200, res.text
    claims = _claims(res.json()["access_token"])
    assert claims["tenant_id"] == acct["tenant_id"]
    assert claims["role"] == "owner"
    assert claims["pa"] is False


async def test_wrong_password_and_unknown_email_are_rejected_identically(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    wrong = await client.post("/api/v1/auth/login", json={"email": acct["email"], "password": "not-the-password"})
    unknown = await client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever-123"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


async def test_expired_and_malformed_tokens_are_rejected(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    expired = create_access_token(
        str(uuid.uuid4()),
        expires_delta=timedelta(seconds=-5),
        extra_claims={"tenant_id": acct["tenant_id"], "role": "owner"},
    )
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})).status_code == 401
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})).status_code == 401
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def _add_member(app_engine: AsyncEngine, owner: dict, email: str, role: str) -> None:
    """Create a second user and give them a role in the owner's tenant (what the invite flow will do)."""
    from app.core.security import hash_password

    user_id = uuid.uuid4()
    tenant_id = uuid.UUID(owner["tenant_id"])
    session = AsyncSession(app_engine)
    await session.begin()
    try:
        await apply_context(session, tenant_id=tenant_id, user_id=user_id)
        await session.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, is_platform_admin, is_active, created_at, updated_at) "
                "VALUES (:id, :email, :pw, false, true, now(), now())"
            ),
            {"id": user_id, "email": email, "pw": hash_password("staff-password-1")},
        )
        await session.execute(
            text(
                "INSERT INTO memberships (id, tenant_id, user_id, role, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :t, :u, :r, now(), now())"
            ),
            {"t": tenant_id, "u": user_id, "r": role},
        )
        await session.commit()
    finally:
        await session.close()


@pytest.mark.parametrize(
    ("role", "can_create", "can_delete"),
    [("owner", True, True), ("manager", True, True), ("staff", True, False)],
)
async def test_roles_are_enforced_by_the_api(
    client: AsyncClient, app_engine: AsyncEngine, role: str, can_create: bool, can_delete: bool
) -> None:
    owner = await register(client, f"Role Shop {role}")
    token = owner
    if role != "owner":
        email = f"{role}-{uuid.uuid4().hex[:8]}@example.com"
        await _add_member(app_engine, owner, email, role)
        res = await client.post("/api/v1/auth/login", json={"email": email, "password": "staff-password-1"})
        assert res.status_code == 200, res.text
        assert res.json()["role"] == role
        token = res.json()

    created = await client.post(
        "/api/v1/customers/", json={"phone": f"+92300{uuid.uuid4().int % 10**7:07d}", "name": "X"}, headers=bearer(token)
    )
    assert (created.status_code == 201) is can_create, created.text
    deleted = await client.delete(f"/api/v1/customers/{created.json()['id']}", headers=bearer(token))
    assert (deleted.status_code == 204) is can_delete, deleted.text
    if not can_delete:
        assert deleted.status_code == 403


async def test_staff_cannot_use_manager_only_legacy_routes(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    email = f"staff-{uuid.uuid4().hex[:8]}@example.com"
    await _add_member(app_engine, owner, email, "staff")
    staff = (await client.post("/api/v1/auth/login", json={"email": email, "password": "staff-password-1"})).json()
    assert (await client.get("/api/vendors/", headers=bearer(staff))).status_code == 403
    assert (await client.get("/api/logs/", headers=bearer(staff))).status_code == 403
    assert (await client.get("/api/vendors/")).status_code == 401


async def test_switch_tenant_requires_membership(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    res = await client.post("/api/v1/auth/switch-tenant", json={"tenant_id": b["tenant_id"]}, headers=bearer(a))
    assert res.status_code == 403
    same = await client.post("/api/v1/auth/switch-tenant", json={"tenant_id": a["tenant_id"]}, headers=bearer(a))
    assert same.status_code == 200
