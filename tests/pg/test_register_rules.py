"""Task 35: creating an account and a shop follows PRD F-002, one test per rule."""

from __future__ import annotations

import uuid
from typing import Any

import asyncpg
import pytest
from httpx import AsyncClient

from app.core.settings import settings
from app.core.throttle import reset_signup_throttle
from tests.pg.conftest import bearer

pytestmark = pytest.mark.pg

REGISTER = "/api/v1/auth/register"


def payload(**over: Any) -> dict[str, Any]:
    return {
        "full_name": "Ali Raza",
        "email": f"ali-{uuid.uuid4().hex[:10]}@example.com",
        "password": "correct-horse-battery",
        "shop_name": "Ali Mart",
        "phone": "+923001234567",
        "city": "Lahore",
        "accept_terms": True,
        **over,
    }


def fields(res: Any) -> set[str]:
    return {e["field"] for e in res.json()["errors"]}


async def test_a_valid_sign_up_creates_the_account_the_shop_and_signs_the_owner_in(client: AsyncClient) -> None:
    res = await client.post(REGISTER, json=payload())
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["role"] == "owner" and body["access_token"] and body["refresh_token"]
    me = await client.get("/api/v1/auth/me", headers=bearer(body))
    assert me.json()["role"] == "owner"
    assert me.json()["memberships"][0]["tenant_name"] == "Ali Mart"


@pytest.mark.parametrize("name", ["A", "   ", " A ", "x" * 81])
async def test_full_name_is_2_to_80_characters(client: AsyncClient, name: str) -> None:
    res = await client.post(REGISTER, json=payload(full_name=name))
    assert res.status_code == 422 and "full_name" in fields(res)


@pytest.mark.parametrize("name", ["B", "x" * 81])
async def test_shop_name_is_2_to_80_characters(client: AsyncClient, name: str) -> None:
    res = await client.post(REGISTER, json=payload(shop_name=name))
    assert res.status_code == 422 and "shop_name" in fields(res)


async def test_email_must_be_valid_and_unique_whatever_its_case(client: AsyncClient) -> None:
    assert "email" in fields(await client.post(REGISTER, json=payload(email="nope")))
    first = payload()
    assert (await client.post(REGISTER, json=first)).status_code == 201
    again = await client.post(REGISTER, json=payload(email=first["email"].upper()))
    assert again.status_code == 409 and "already registered" in again.json()["detail"]


async def test_password_needs_8_characters(client: AsyncClient) -> None:
    res = await client.post(REGISTER, json=payload(password="Ab1!xyz"))
    assert res.status_code == 422 and "password" in fields(res)


@pytest.mark.parametrize("weak", ["12345678", "password", "PASSWORD123", "qwertyuiop", "aaaaaaaa", "Bazaarflow123"])
async def test_password_must_not_be_a_common_one(client: AsyncClient, weak: str) -> None:
    res = await client.post(REGISTER, json=payload(password=weak))
    assert res.status_code == 422 and "password" in fields(res)
    assert "too common" in res.json()["errors"][0]["message"]


async def test_the_password_is_stored_as_a_bcrypt_hash_never_as_text(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    body = payload(password="unusual-passphrase-42")
    assert (await client.post(REGISTER, json=body)).status_code == 201
    stored = await admin_conn.fetchval("SELECT hashed_password FROM users WHERE email = $1", body["email"])
    assert stored.startswith("$2") and "unusual-passphrase-42" not in stored


@pytest.mark.parametrize("phone", ["03001234567", "+0123456789", "+92 300 1234567", "+92300", "923001234567"])
async def test_phone_must_be_an_international_number(client: AsyncClient, phone: str) -> None:
    res = await client.post(REGISTER, json=payload(phone=phone))
    assert res.status_code == 422 and "phone" in fields(res)


async def test_city_is_optional_and_at_most_60_characters(client: AsyncClient) -> None:
    assert (await client.post(REGISTER, json=payload(city=None))).status_code == 201
    no_city = payload()
    del no_city["city"]
    assert (await client.post(REGISTER, json=no_city)).status_code == 201
    assert "city" in fields(await client.post(REGISTER, json=payload(city="c" * 61)))


async def test_the_terms_must_be_accepted(client: AsyncClient) -> None:
    res = await client.post(REGISTER, json=payload(accept_terms=False))
    assert res.status_code == 422 and "accept_terms" in fields(res)


async def test_the_shop_gets_a_unique_slug_and_two_shops_can_share_a_name(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    for _ in range(2):
        assert (await client.post(REGISTER, json=payload(shop_name="Same Name Store"))).status_code == 201
    slugs = [r["slug"] for r in await admin_conn.fetch("SELECT slug FROM tenants WHERE name = 'Same Name Store'")]
    assert len(slugs) == 2 and len(set(slugs)) == 2 and all(s.startswith("same-name-store-") for s in slugs)


async def test_everything_is_created_together_or_not_at_all(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    body = payload(shop_name="Atomic Shop")
    assert (await client.post(REGISTER, json=body)).status_code == 201
    counts = await admin_conn.fetchrow(
        "SELECT (SELECT count(*) FROM tenants WHERE name = 'Atomic Shop') AS tenants, "
        "(SELECT count(*) FROM memberships m JOIN tenants t ON t.id = m.tenant_id WHERE t.name = 'Atomic Shop' AND m.role = 'owner') AS owners, "
        "(SELECT count(*) FROM audit_logs WHERE action = 'tenant.registered' AND after_json->>'shop_name' = 'Atomic Shop') AS audits"
    )
    assert (counts["tenants"], counts["owners"], counts["audits"]) == (1, 1, 1)

    before = await admin_conn.fetchval("SELECT count(*) FROM tenants")
    dup = await client.post(REGISTER, json=payload(email=body["email"], shop_name="Orphan Shop"))
    assert dup.status_code == 409
    assert await admin_conn.fetchval("SELECT count(*) FROM tenants") == before, "a refused sign-up leaves no shop behind"
    assert await admin_conn.fetchval("SELECT count(*) FROM tenants WHERE name = 'Orphan Shop'") == 0


async def test_sign_ups_from_one_address_are_limited_per_hour(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SIGNUP_MAX_PER_HOUR", 2)
    reset_signup_throttle()
    try:
        assert (await client.post(REGISTER, json=payload())).status_code == 201
        assert (await client.post(REGISTER, json=payload())).status_code == 201
        limited = await client.post(REGISTER, json=payload())
        assert limited.status_code == 429
        problem = limited.json()
        assert problem["code"] == "signup_rate_limited" and problem["retry_after_seconds"] > 0
        # sign-in is not affected by the sign-up limit
        existing = payload()
        monkeypatch.setattr(settings, "SIGNUP_MAX_PER_HOUR", 0)
        assert (await client.post(REGISTER, json=existing)).status_code == 201
        assert (await client.post("/api/v1/auth/login", json={"email": existing["email"], "password": existing["password"]})).status_code == 200
    finally:
        reset_signup_throttle()
