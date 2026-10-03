"""Task 34: sign-in follows PRD F-001, one test per rule (field spec in section 5.3)."""

from __future__ import annotations

import logging
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.settings import settings
from app.core.tenancy import apply_context
from tests.pg.conftest import register

pytestmark = pytest.mark.pg

LOGIN = "/api/v1/auth/login"


async def test_email_must_be_a_valid_address(client: AsyncClient) -> None:
    res = await client.post(LOGIN, json={"email": "not-an-email", "password": "correct-horse-battery"})
    assert res.status_code == 422
    assert "email" in {e["field"] for e in res.json()["errors"]}
    missing = await client.post(LOGIN, json={"password": "correct-horse-battery"})
    assert missing.status_code == 422


async def test_email_is_at_most_254_characters(client: AsyncClient) -> None:
    too_long = "a" * 64 + "@" + ".".join(["b" * 63] * 3) + ".com"  # 261 characters
    assert len(too_long) > 254
    res = await client.post(LOGIN, json={"email": too_long, "password": "correct-horse-battery"})
    assert res.status_code == 422


async def test_email_is_case_insensitive(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    res = await client.post(LOGIN, json={"email": acct["email"].upper(), "password": acct["password"]})
    assert res.status_code == 200, res.text
    assert res.json()["tenant_id"] == acct["tenant_id"]


async def test_password_needs_at_least_8_characters(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    res = await client.post(LOGIN, json={"email": acct["email"], "password": "short"})
    assert res.status_code == 422
    assert "password" in {e["field"] for e in res.json()["errors"]}
    exactly_eight = await client.post(LOGIN, json={"email": acct["email"], "password": "12345678"})
    assert exactly_eight.status_code == 401  # long enough to be checked, and simply wrong


async def test_the_password_is_never_logged_or_audited(
    client: AsyncClient, app_engine: AsyncEngine, caplog: pytest.LogCaptureFixture
) -> None:
    acct = await register(client, "Shop A")
    marker = f"Zx9-{uuid.uuid4().hex}"
    with caplog.at_level(logging.DEBUG):
        await client.post(LOGIN, json={"email": acct["email"], "password": marker})
        await client.post(LOGIN, json={"email": acct["email"], "password": acct["password"]})
    assert marker not in caplog.text
    assert acct["password"] not in caplog.text
    session = AsyncSession(app_engine)
    await session.begin()
    try:
        await apply_context(session, tenant_id=uuid.UUID(acct["tenant_id"]))
        rows = (await session.execute(text("SELECT coalesce(before_json::text,'') || coalesce(after_json::text,'') FROM audit_logs"))).scalars()
        assert not any(marker in r or acct["password"] in r for r in rows)
    finally:
        await session.rollback()


async def test_five_failures_lock_the_account_for_15_minutes(client: AsyncClient) -> None:
    assert (settings.LOGIN_MAX_FAILURES, settings.LOGIN_LOCKOUT_MINUTES) == (5, 15)  # the PRD numbers
    acct = await register(client, "Shop A")
    for _ in range(5):
        wrong = await client.post(LOGIN, json={"email": acct["email"], "password": "wrong-password-1"})
        assert wrong.status_code == 401
    locked = await client.post(LOGIN, json={"email": acct["email"], "password": acct["password"]})
    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) == 15 * 60


async def _add_membership(engine: AsyncEngine, user_email: str, tenant_id: uuid.UUID, role: str) -> None:
    session = AsyncSession(engine)
    await session.begin()
    try:
        await apply_context(session, tenant_id=tenant_id)
        await session.execute(
            text(
                "INSERT INTO memberships (id, tenant_id, user_id, role, created_at, updated_at) "
                "SELECT gen_random_uuid(), :t, id, :r, now(), now() FROM users WHERE email = :e"
            ),
            {"t": tenant_id, "r": role, "e": user_email},
        )
        await session.commit()
    finally:
        await session.close()


async def test_a_user_in_several_shops_must_choose_one(client: AsyncClient, app_engine: AsyncEngine) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    other = await register(client, "Shop C")
    await _add_membership(app_engine, a["email"], uuid.UUID(b["tenant_id"]), "manager")

    body = {"email": a["email"], "password": a["password"]}
    ask = await client.post(LOGIN, json=body)
    assert ask.status_code == 409
    problem = ask.json()
    assert problem["code"] == "tenant_required"
    assert {t["tenant_name"] for t in problem["tenants"]} == {"Shop A", "Shop B"}

    chosen = await client.post(LOGIN, json={**body, "tenant_id": b["tenant_id"]})
    assert chosen.status_code == 200 and chosen.json()["tenant_id"] == b["tenant_id"] and chosen.json()["role"] == "manager"

    foreign = await client.post(LOGIN, json={**body, "tenant_id": other["tenant_id"]})
    assert foreign.status_code == 403  # a shop the user does not belong to


async def test_a_wrong_password_and_an_unknown_email_look_the_same(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    wrong = await client.post(LOGIN, json={"email": acct["email"], "password": "not-the-password"})
    unknown = await client.post(LOGIN, json={"email": "nobody@example.com", "password": "not-the-password"})
    assert wrong.status_code == unknown.status_code == 401
    assert {**wrong.json(), "request_id": None} == {**unknown.json(), "request_id": None}
