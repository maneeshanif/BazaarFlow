"""Task 43: team and roles (PRD F-019): add, change role, remove; owner only; changes take effect at once."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.tenancy import tenant_session
from tests.pg.conftest import bearer, member, register

pytestmark = pytest.mark.pg

TEAM = "/api/v1/team/"
LOGIN = "/api/v1/auth/login"


async def add(client: AsyncClient, owner: dict[str, Any], role: str = "staff", **over: Any) -> Any:
    body = {"name": "Sana Staff", "email": f"sana-{uuid.uuid4().hex[:8]}@example.com", "role": role, "password": "first-pass-2026", **over}
    return await client.post(TEAM, json=body, headers=bearer(owner)), body


async def test_the_owner_sees_the_team_with_themselves_first(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    await member(client, app_engine, owner, "staff")
    await member(client, app_engine, owner, "manager")
    listing = (await client.get(TEAM, headers=bearer(owner))).json()
    assert [m["role"] for m in listing] == ["owner", "manager", "staff"]
    assert listing[0]["is_you"] is True and listing[0]["email"] == owner["email"] and not listing[1]["is_you"]


async def test_adding_someone_new_creates_their_login_with_the_role_given(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    res, body = await add(client, owner, "manager")
    assert res.status_code == 201, res.text
    made = res.json()
    assert (made["role"], made["new_account"], made["is_you"], made["name"]) == ("manager", True, False, "Sana Staff")
    login = await client.post(LOGIN, json={"email": body["email"], "password": body["password"]})
    assert login.status_code == 200 and login.json()["role"] == "manager" and login.json()["tenant_id"] == owner["tenant_id"]
    assert len((await client.get(TEAM, headers=bearer(owner))).json()) == 2


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"role": "owner"}, "role"),
        ({"role": "admin"}, "role"),
        ({"email": "nope"}, "email"),
        ({"name": "A"}, "name"),
        ({"password": "short"}, "password"),
        ({"password": "12345678"}, "password"),
        ({"password": "password123"}, "password"),
    ],
)
async def test_invalid_team_input_is_refused_under_the_field(client: AsyncClient, change: dict[str, Any], field: str) -> None:
    owner = await register(client, "Shop A")
    res, _ = await add(client, owner, **change)
    assert res.status_code == 422 and field in {e["field"] for e in res.json()["errors"]}


async def test_a_new_person_needs_a_first_password(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    res = await client.post(TEAM, json={"name": "No Pass", "email": "nopass@example.com", "role": "staff"}, headers=bearer(owner))
    assert res.status_code == 422 and res.json()["code"] == "password_required"


async def test_someone_with_an_account_elsewhere_keeps_their_own_password(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")  # b's owner already has an account
    res = await client.post(TEAM, json={"name": "Ignored", "email": b["email"], "role": "manager"}, headers=bearer(a))
    assert res.status_code == 201 and res.json()["new_account"] is False
    # they sign in with the password they already had, and now choose between two shops
    ask = await client.post(LOGIN, json={"email": b["email"], "password": b["password"]})
    assert ask.status_code == 409 and ask.json()["code"] == "tenant_required"
    chosen = await client.post(LOGIN, json={"email": b["email"], "password": b["password"], "tenant_id": a["tenant_id"]})
    assert chosen.status_code == 200 and chosen.json()["role"] == "manager"


async def test_the_same_person_cannot_be_added_twice(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    res, body = await add(client, owner)
    assert res.status_code == 201
    again = await client.post(TEAM, json=body, headers=bearer(owner))
    assert again.status_code == 409 and again.json()["code"] == "already_member"
    assert (await client.post(TEAM, json={**body, "email": owner["email"], "role": "staff"}, headers=bearer(owner))).status_code == 409


async def test_a_role_change_takes_effect_on_the_very_next_request(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    res, body = await add(client, owner, "manager")
    token = (await client.post(LOGIN, json={"email": body["email"], "password": body["password"]})).json()
    product = {"sku": "A", "name": "Thing", "price": "10.00"}
    assert (await client.post("/api/v1/inventory/", json=product, headers=bearer(token))).status_code == 201
    changed = await client.patch(f"{TEAM}{res.json()['id']}", json={"role": "staff"}, headers=bearer(owner))
    assert changed.status_code == 200 and changed.json()["role"] == "staff"
    # the old token no longer matches what the shop says about them: it is refused, and refreshing gives a staff token
    assert (await client.post("/api/v1/inventory/", json={**product, "sku": "B"}, headers=bearer(token))).status_code == 401
    fresh = (await client.post("/api/v1/auth/refresh", json={"refresh_token": token["refresh_token"]})).json()
    assert fresh["role"] == "staff"
    assert (await client.post("/api/v1/inventory/", json={**product, "sku": "B"}, headers=bearer(fresh))).status_code == 403


async def test_the_owner_is_fixed(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    mine = (await client.get(TEAM, headers=bearer(owner))).json()[0]["id"]
    for method, payload in (("PATCH", {"role": "staff"}), ("DELETE", None)):
        res = await client.request(method, f"{TEAM}{mine}", json=payload, headers=bearer(owner))
        assert res.status_code == 422 and res.json()["code"] == "owner_is_fixed", method
    assert (await client.patch(f"{TEAM}{mine}", json={"role": "owner"}, headers=bearer(owner))).status_code == 422


async def test_removing_someone_ends_their_access_at_once(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    res, body = await add(client, owner)
    session = (await client.post(LOGIN, json={"email": body["email"], "password": body["password"]})).json()
    assert (await client.get("/api/v1/inventory/", headers=bearer(session))).status_code == 200

    gone = await client.delete(f"{TEAM}{res.json()['id']}", headers=bearer(owner))
    assert gone.status_code == 204
    assert (await client.get("/api/v1/inventory/", headers=bearer(session))).status_code in (401, 403), "the old token stops working"
    refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert refreshed.status_code == 401, "and so does the refresh token"
    relogin = await client.post(LOGIN, json={"email": body["email"], "password": body["password"]})
    assert relogin.status_code == 403, "they have no shop to sign in to"
    assert len((await client.get(TEAM, headers=bearer(owner))).json()) == 1
    assert (await client.delete(f"{TEAM}{res.json()['id']}", headers=bearer(owner))).status_code == 404


async def test_only_the_owner_manages_the_team(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    manager = await member(client, app_engine, owner, "manager")
    staff = await member(client, app_engine, owner, "staff")
    target = (await client.get(TEAM, headers=bearer(owner))).json()[-1]["id"]
    for who in (manager, staff):
        assert (await client.get(TEAM, headers=bearer(who))).status_code == 403
        assert (await client.post(TEAM, json={"name": "Nope", "email": "n@example.com", "role": "staff", "password": "first-pass-2026"}, headers=bearer(who))).status_code == 403
        assert (await client.patch(f"{TEAM}{target}", json={"role": "manager"}, headers=bearer(who))).status_code == 403
        assert (await client.delete(f"{TEAM}{target}", headers=bearer(who))).status_code == 403
    assert (await client.get(TEAM)).status_code == 401


async def test_another_shops_team_is_out_of_reach(client: AsyncClient, app_engine: AsyncEngine) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    await member(client, app_engine, a, "staff")
    target = next(m["id"] for m in (await client.get(TEAM, headers=bearer(a))).json() if m["role"] == "staff")
    assert (await client.patch(f"{TEAM}{target}", json={"role": "manager"}, headers=bearer(b))).status_code == 404
    assert (await client.delete(f"{TEAM}{target}", headers=bearer(b))).status_code == 404
    assert [m["role"] for m in (await client.get(TEAM, headers=bearer(b))).json()] == ["owner"]


async def test_team_changes_are_audited_without_the_password(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    res, body = await add(client, owner)
    await client.patch(f"{TEAM}{res.json()['id']}", json={"role": "manager"}, headers=bearer(owner))
    await client.delete(f"{TEAM}{res.json()['id']}", headers=bearer(owner))
    tenant_id = uuid.UUID(owner["tenant_id"])
    async with tenant_session(tenant_id) as db:
        rows = (
            await db.execute(text("SELECT action, coalesce(before_json::text,'') || coalesce(after_json::text,'') FROM audit_logs WHERE action LIKE 'team.%'"))
        ).all()
    assert {r[0] for r in rows} == {"team.added", "team.role_changed", "team.removed"}
    assert not any(body["password"] in r[1] or body["email"] in r[1] for r in rows), "neither the password nor the full email is stored"
