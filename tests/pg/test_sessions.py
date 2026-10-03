"""Refresh tokens, logout, login lockout and immediate role revocation (PRD F-001, §14)."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.settings import settings
from app.core.tenancy import apply_context
from tests.pg.conftest import bearer, register

pytestmark = pytest.mark.pg


async def _audit_actions(app_engine: AsyncEngine, tenant_id: str) -> list[str]:
    session = AsyncSession(app_engine)
    await session.begin()
    try:
        await apply_context(session, tenant_id=uuid.UUID(tenant_id))
        rows = (await session.execute(text("SELECT action FROM audit_logs ORDER BY created_at"))).all()
        return [r[0] for r in rows]
    finally:
        await session.rollback()
        await session.close()


@pytest.fixture
def strict_reuse(monkeypatch: pytest.MonkeyPatch) -> None:
    """Grace 0 = the strict PRD rule: any reuse of a rotated token is theft."""
    monkeypatch.setattr(settings, "REFRESH_REUSE_GRACE_SECONDS", 0)


async def test_refresh_rotates_the_token_and_the_old_one_stops_working(client: AsyncClient, strict_reuse: None) -> None:
    acct = await register(client, "Shop A")
    first = acct["refresh_token"]
    res = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert res.status_code == 200, res.text
    second = res.json()["refresh_token"]
    assert second != first
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {res.json()['access_token']}"})
    assert me.status_code == 200
    # the rotated token is dead
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": first})).status_code == 401


async def test_reusing_a_rotated_refresh_token_revokes_the_whole_session_family(
    client: AsyncClient, strict_reuse: None
) -> None:
    acct = await register(client, "Shop A")
    first = acct["refresh_token"]
    second = (await client.post("/api/v1/auth/refresh", json={"refresh_token": first})).json()["refresh_token"]
    # attacker replays the old token -> rejected, and the legitimate newer token is revoked as well
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": first})).status_code == 401
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": second})).status_code == 401


async def test_a_reload_during_a_refresh_does_not_sign_the_user_out(client: AsyncClient) -> None:
    """The browser aborted after the server rotated: it presents the OLD token again within the grace window."""
    acct = await register(client, "Shop A")
    first = acct["refresh_token"]
    second = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert second.status_code == 200
    retry = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert retry.status_code == 200, "a reuse inside the grace window must not be treated as theft"
    third = retry.json()["refresh_token"]
    assert third not in {first, second.json()["refresh_token"]}
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": third})).status_code == 200


async def test_reuse_after_the_grace_window_is_still_theft(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, strict_reuse: None
) -> None:
    acct = await register(client, "Shop A")
    first = acct["refresh_token"]
    second = (await client.post("/api/v1/auth/refresh", json={"refresh_token": first})).json()["refresh_token"]
    monkeypatch.setattr(settings, "REFRESH_REUSE_GRACE_SECONDS", 0)
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": first})).status_code == 401
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": second})).status_code == 401


async def test_a_logged_out_token_is_never_revived_by_the_grace_window(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    token = acct["refresh_token"]
    assert (await client.post("/api/v1/auth/logout", json={"refresh_token": token})).status_code == 204
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": token})).status_code == 401


async def test_the_grace_window_is_bounded_in_time(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Move the clock past the window: the second use of the rotated token is theft again."""
    import app.core.refresh_tokens as rt

    acct = await register(client, "Shop A")
    first = acct["refresh_token"]
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": first})).status_code == 200
    real_now = rt._now
    monkeypatch.setattr(rt, "_now", lambda: real_now() + timedelta(seconds=settings.REFRESH_REUSE_GRACE_SECONDS + 5))
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": first})).status_code == 401


async def test_logout_revokes_the_refresh_token_and_is_idempotent(client: AsyncClient, app_engine: AsyncEngine) -> None:
    acct = await register(client, "Shop A")
    assert (await client.post("/api/v1/auth/logout", json={"refresh_token": acct["refresh_token"]})).status_code == 204
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": acct["refresh_token"]})).status_code == 401
    # logging out again, or with a made-up token, is not an error
    assert (await client.post("/api/v1/auth/logout", json={"refresh_token": acct["refresh_token"]})).status_code == 204
    assert (await client.post("/api/v1/auth/logout", json={"refresh_token": "x" * 40})).status_code == 204
    assert "auth.logout" in await _audit_actions(app_engine, acct["tenant_id"])


async def test_unknown_and_malformed_refresh_tokens_are_rejected(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": "z" * 60})).status_code == 401
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": "short"})).status_code == 422


async def test_five_failed_logins_lock_the_account_for_a_while(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    for _ in range(5):
        res = await client.post("/api/v1/auth/login", json={"email": acct["email"], "password": "wrong-password-1"})
        assert res.status_code == 401
    locked = await client.post("/api/v1/auth/login", json={"email": acct["email"], "password": acct["password"]})
    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) == 15 * 60


async def test_lockout_also_applies_to_unknown_emails_so_it_reveals_nothing(client: AsyncClient) -> None:
    email = f"ghost-{uuid.uuid4().hex[:8]}@example.com"
    for _ in range(5):
        assert (await client.post("/api/v1/auth/login", json={"email": email, "password": "whatever-123"})).status_code == 401
    assert (await client.post("/api/v1/auth/login", json={"email": email, "password": "whatever-123"})).status_code == 429


async def test_a_successful_login_clears_earlier_failures(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    for _ in range(3):
        await client.post("/api/v1/auth/login", json={"email": acct["email"], "password": "wrong-password-1"})
    assert (await client.post("/api/v1/auth/login", json={"email": acct["email"], "password": acct["password"]})).status_code == 200
    for _ in range(4):  # would be 7 failures in total if the earlier ones were still counted
        assert (await client.post("/api/v1/auth/login", json={"email": acct["email"], "password": "wrong-password-1"})).status_code == 401


async def test_a_demoted_member_loses_access_immediately(client: AsyncClient, app_engine: AsyncEngine) -> None:
    acct = await register(client, "Shop A")
    headers = bearer(acct)
    assert (await client.get("/api/v1/customers/", headers=headers)).status_code == 200

    session = AsyncSession(app_engine)
    await session.begin()
    try:
        await apply_context(session, tenant_id=uuid.UUID(acct["tenant_id"]))
        await session.execute(text("UPDATE memberships SET role = 'staff'"))
        await session.commit()
    finally:
        await session.close()

    # the token still says owner, but the database says staff: the request is refused until they re-authenticate
    assert (await client.get("/api/v1/customers/", headers=headers)).status_code == 401
    refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": acct["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["role"] == "staff"


async def test_security_relevant_actions_write_exactly_one_audit_row_each(
    client: AsyncClient, app_engine: AsyncEngine
) -> None:
    acct = await register(client, "Audit Shop")
    login = (await client.post("/api/v1/auth/login", json={"email": acct["email"], "password": acct["password"]})).json()
    headers = bearer(login)
    created = (await client.post("/api/v1/customers/", json={"phone": "+923009990001", "name": "C"}, headers=headers)).json()
    await client.delete(f"/api/v1/customers/{created['id']}", headers=headers)
    await client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})

    actions = await _audit_actions(app_engine, acct["tenant_id"])
    for expected in ("tenant.registered", "auth.login", "customer.created", "customer.deleted", "auth.refresh"):
        assert actions.count(expected) == 1, f"{expected}: {actions}"
