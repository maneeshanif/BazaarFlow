"""The customers slice end to end: tenant isolation through the HTTP API (PRD F-009, §19)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.pg.conftest import bearer, register

pytestmark = pytest.mark.pg


async def test_a_tenant_only_sees_its_own_customers(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    created = await client.post("/api/v1/customers/", json={"phone": "+923001110001", "name": "A-customer"}, headers=bearer(a))
    assert created.status_code == 201
    await client.post("/api/v1/customers/", json={"phone": "+923001110002", "name": "B-customer"}, headers=bearer(b))

    a_list = (await client.get("/api/v1/customers/", headers=bearer(a))).json()["items"]
    b_list = (await client.get("/api/v1/customers/", headers=bearer(b))).json()["items"]
    assert [c["name"] for c in a_list] == ["A-customer"]
    assert [c["name"] for c in b_list] == ["B-customer"]
    assert {c["tenant_id"] for c in a_list} == {a["tenant_id"]}


async def test_a_tenant_cannot_delete_another_tenants_customer(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    created = (await client.post("/api/v1/customers/", json={"phone": "+923001110003", "name": "Keep"}, headers=bearer(a))).json()
    res = await client.delete(f"/api/v1/customers/{created['id']}", headers=bearer(b))
    assert res.status_code == 404
    assert (await client.get("/api/v1/customers/", headers=bearer(a))).json()["total"] == 1


async def test_the_same_phone_can_exist_in_two_tenants_but_not_twice_in_one(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    payload = {"phone": "+923001110004", "name": "Shared number"}
    assert (await client.post("/api/v1/customers/", json=payload, headers=bearer(a))).status_code == 201
    assert (await client.post("/api/v1/customers/", json=payload, headers=bearer(b))).status_code == 201
    assert (await client.post("/api/v1/customers/", json=payload, headers=bearer(a))).status_code == 409


async def test_client_supplied_tenant_id_is_ignored(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    res = await client.post(
        "/api/v1/customers/",
        json={"phone": "+923001110005", "name": "Sneaky", "tenant_id": b["tenant_id"]},
        headers=bearer(a),
    )
    assert res.status_code == 201
    assert res.json()["tenant_id"] == a["tenant_id"]
