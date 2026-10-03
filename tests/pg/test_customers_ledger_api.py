"""Task 40: customers and the udhaar ledger (PRD F-009): roles, lookup, balances, payments, isolation."""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.tenancy import tenant_session
from app.services import ledger_service
from tests.pg.conftest import bearer, member, register

pytestmark = pytest.mark.pg

URL = "/api/v1/customers/"


async def make(client: AsyncClient, acct: dict[str, Any], phone: str, name: str | None = "Ali") -> dict[str, Any]:
    res = await client.post(URL, json={"phone": phone, "name": name}, headers=bearer(acct))
    assert res.status_code == 201, res.text
    body: dict[str, Any] = res.json()
    return body


async def owe(acct: dict[str, Any], customer_id: str, amount: str) -> None:
    """A credit sale is not built yet (task 38): put the debit in the ledger the way a sale will."""
    tenant_id = uuid.UUID(acct["tenant_id"])
    async with tenant_session(tenant_id) as db:
        await ledger_service.add_entry(
            db,
            tenant_id=tenant_id,
            party_type="customer",
            party_id=uuid.UUID(customer_id),
            amount=Decimal(amount),
            direction="debit",
            ref_type="order",
            ref_id=None,
            created_by=None,
        )


async def test_lookup_search_sort_and_paging(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    h = bearer(acct)
    for i, name in enumerate(["Zara", "Ali", "Bilal", "Chand", "Danish"]):
        await make(client, acct, f"+9230011100{i:02d}", name)
    page1 = (await client.get(URL, params={"limit": 2}, headers=h)).json()
    assert [c["name"] for c in page1["items"]] == ["Ali", "Bilal"] and page1["total"] == 5 and page1["next_cursor"]
    page2 = (await client.get(URL, params={"limit": 2, "cursor": page1["next_cursor"]}, headers=h)).json()
    assert [c["name"] for c in page2["items"]] == ["Chand", "Danish"]
    assert (await client.get(URL, params={"q": "zar"}, headers=h)).json()["total"] == 1
    assert (await client.get(URL, params={"q": "0001"}, headers=h)).json()["total"] == 1  # by phone
    assert (await client.get(URL, params={"q": "%"}, headers=h)).json()["total"] == 0
    assert (await client.get(URL, params={"sort": "tenant_id"}, headers=h)).status_code == 400


async def test_balances_filter_sort_and_total_outstanding(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    h = bearer(acct)
    a = await make(client, acct, "+923001110001", "Ali")
    b = await make(client, acct, "+923001110002", "Bilal")
    await make(client, acct, "+923001110003", "Chand")
    await owe(acct, a["id"], "1500.50")
    await owe(acct, b["id"], "300.00")

    everyone = (await client.get(URL, headers=h)).json()["items"]
    assert {c["name"]: c["balance"] for c in everyone} == {"Ali": "1500.50", "Bilal": "300.00", "Chand": "0.00"}
    owing = (await client.get(URL, params={"owing_only": "true"}, headers=h)).json()
    assert owing["total"] == 2 and {c["name"] for c in owing["items"]} == {"Ali", "Bilal"}
    by_debt = (await client.get(URL, params={"sort": "-balance"}, headers=h)).json()["items"]
    assert [c["name"] for c in by_debt][:2] == ["Ali", "Bilal"]

    tenant_id = uuid.UUID(acct["tenant_id"])
    async with tenant_session(tenant_id) as db:
        assert await ledger_service.total_outstanding(db, tenant_id) == Decimal("1800.50")


async def test_a_payment_reduces_the_balance_and_the_ledger_adds_up(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    h = bearer(acct)
    c = await make(client, acct, "+923001110001")
    await owe(acct, c["id"], "1000.00")
    paid = await client.post(f"{URL}{c['id']}/payments", json={"amount": "400.00", "method": "cash"}, headers=h)
    assert paid.status_code == 201, paid.text
    assert paid.json()["balance"] == "600.00"
    assert (await client.get(f"{URL}{c['id']}", headers=h)).json()["balance"] == "600.00"

    ledger = (await client.get(f"{URL}{c['id']}/ledger", headers=h)).json()
    assert [(e["direction"], e["amount"], e["balance_after"]) for e in ledger["items"]] == [
        ("credit", "400.00", "600.00"),
        ("debit", "1000.00", "1000.00"),
    ]
    settled = await client.post(f"{URL}{c['id']}/payments", json={"amount": "600.00", "method": "bank"}, headers=h)
    assert settled.json()["balance"] == "0.00"


async def test_a_payment_cannot_exceed_what_is_owed_and_must_be_valid(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    h = bearer(acct)
    c = await make(client, acct, "+923001110001")
    await owe(acct, c["id"], "100.00")
    over = await client.post(f"{URL}{c['id']}/payments", json={"amount": "100.01", "method": "cash"}, headers=h)
    assert over.status_code == 422 and over.json()["code"] == "payment_exceeds_balance"
    for bad in ({"amount": "0", "method": "cash"}, {"amount": "-5", "method": "cash"}, {"amount": "5", "method": "udhaar"}, {"amount": "1.234", "method": "cash"}):
        assert (await client.post(f"{URL}{c['id']}/payments", json=bad, headers=h)).status_code == 422
    assert (await client.get(f"{URL}{c['id']}", headers=h)).json()["balance"] == "100.00"


async def test_two_simultaneous_payments_cannot_both_take_the_last_of_the_balance(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    h = bearer(acct)
    c = await make(client, acct, "+923001110001")
    await owe(acct, c["id"], "100.00")
    body = {"amount": "70.00", "method": "cash"}
    results = await asyncio.gather(*[client.post(f"{URL}{c['id']}/payments", json=body, headers=h) for _ in range(2)])
    assert sorted(r.status_code for r in results) == [201, 422]
    assert (await client.get(f"{URL}{c['id']}", headers=h)).json()["balance"] == "30.00"


async def test_roles_staff_look_up_but_never_see_credit(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    manager = await member(client, app_engine, owner, "manager")
    staff = await member(client, app_engine, owner, "staff")
    c = await make(client, owner, "+923001110001")
    await owe(owner, c["id"], "250.00")

    # staff may list, look up and add a customer (they do it while selling) but see no balance
    listed = (await client.get(URL, headers=bearer(staff))).json()["items"][0]
    assert listed["name"] == "Ali" and listed["balance"] is None
    assert (await client.get(f"{URL}{c['id']}", headers=bearer(staff))).json()["balance"] is None
    assert (await client.post(URL, json={"phone": "+923001110009", "name": "Walk-in"}, headers=bearer(staff))).status_code == 201
    assert (await client.get(URL, params={"owing_only": "true"}, headers=bearer(staff))).status_code == 403
    assert (await client.get(URL, params={"sort": "-balance"}, headers=bearer(staff))).status_code == 403
    # but not the ledger, payments, edits or deletion
    assert (await client.get(f"{URL}{c['id']}/ledger", headers=bearer(staff))).status_code == 403
    assert (await client.post(f"{URL}{c['id']}/payments", json={"amount": "1", "method": "cash"}, headers=bearer(staff))).status_code == 403
    assert (await client.patch(f"{URL}{c['id']}", json={"name": "X"}, headers=bearer(staff))).status_code == 403
    # a manager runs the ledger and edits, but only the owner deletes
    assert (await client.get(f"{URL}{c['id']}", headers=bearer(manager))).json()["balance"] == "250.00"
    assert (await client.patch(f"{URL}{c['id']}", json={"name": "Ali Raza"}, headers=bearer(manager))).json()["name"] == "Ali Raza"
    assert (await client.delete(f"{URL}{c['id']}", headers=bearer(manager))).status_code == 403


async def test_edit_rules_and_duplicate_phone(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    h = bearer(acct)
    a = await make(client, acct, "+923001110001", "Ali")
    await make(client, acct, "+923001110002", "Bilal")
    assert (await client.patch(f"{URL}{a['id']}", json={"phone": "+923001110002"}, headers=h)).status_code == 409
    assert (await client.patch(f"{URL}{a['id']}", json={"tenant_id": str(uuid.uuid4())}, headers=h)).status_code == 422
    assert (await client.patch(f"{URL}{a['id']}", json={"balance": "0"}, headers=h)).status_code == 422
    assert (await client.patch(f"{URL}{a['id']}", json={}, headers=h)).status_code == 422
    ok = await client.patch(f"{URL}{a['id']}", json={"email": "ali@example.com", "address": "Lahore"}, headers=h)
    assert ok.status_code == 200 and ok.json()["email"] == "ali@example.com"
    assert (await client.post(URL, json={"phone": "+923001110002"}, headers=h)).json()["code"] == "duplicate_phone"


async def test_a_customer_who_owes_money_cannot_be_deleted(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    h = bearer(acct)
    c = await make(client, acct, "+923001110001")
    await owe(acct, c["id"], "50.00")
    refused = await client.delete(f"{URL}{c['id']}", headers=h)
    assert refused.status_code == 422 and refused.json()["code"] == "customer_owes_money"
    await client.post(f"{URL}{c['id']}/payments", json={"amount": "50.00", "method": "cash"}, headers=h)
    assert (await client.delete(f"{URL}{c['id']}", headers=h)).status_code == 204


async def test_another_shops_customer_is_a_404_everywhere(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    c = await make(client, a, "+923001110001")
    await owe(a, c["id"], "75.00")
    hb = bearer(b)
    cid = c["id"]
    assert (await client.get(f"{URL}{cid}", headers=hb)).status_code == 404
    assert (await client.patch(f"{URL}{cid}", json={"name": "Hijack"}, headers=hb)).status_code == 404
    assert (await client.get(f"{URL}{cid}/ledger", headers=hb)).status_code == 404
    assert (await client.post(f"{URL}{cid}/payments", json={"amount": "1", "method": "cash"}, headers=hb)).status_code == 404
    assert (await client.delete(f"{URL}{cid}", headers=hb)).status_code == 404
    assert (await client.get(f"{URL}{cid}", headers=bearer(a))).json()["balance"] == "75.00"
    assert (await client.get(f"{URL}not-a-uuid", headers=hb)).status_code == 404


async def test_changes_are_audited(client: AsyncClient) -> None:
    from sqlalchemy import text

    acct = await register(client, "Shop A")
    h = bearer(acct)
    c = await make(client, acct, "+923001110001")
    await owe(acct, c["id"], "10.00")
    await client.patch(f"{URL}{c['id']}", json={"name": "Renamed"}, headers=h)
    await client.post(f"{URL}{c['id']}/payments", json={"amount": "10.00", "method": "cash"}, headers=h)
    await client.delete(f"{URL}{c['id']}", headers=h)
    tenant_id = uuid.UUID(acct["tenant_id"])
    async with tenant_session(tenant_id) as db:
        actions = set((await db.execute(text("SELECT action FROM audit_logs WHERE tenant_id = :t"), {"t": tenant_id})).scalars())
    assert {"customer.created", "customer.updated", "payment.recorded", "customer.deleted"} <= actions
