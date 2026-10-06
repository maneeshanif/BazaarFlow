"""Task 73 (F-012, R-005): vendors, purchase bills, payments and the payables report, end to end on Postgres."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.tenancy import tenant_session
from tests.pg.conftest import bearer, member, register

pytestmark = pytest.mark.pg

URL = "/api/v1/vendors/"


async def _vendor(client: AsyncClient, acct: dict[str, Any], name: str = "Karachi Cloth House", **over: object) -> dict[str, Any]:
    res = await client.post(URL, json={"name": name, "phone": "+923001234567", **over}, headers=bearer(acct))
    assert res.status_code == 201, res.text
    body: dict[str, Any] = res.json()
    return body


async def test_create_list_get_update_and_audit(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    v = await _vendor(client, acct)
    assert v["balance"] == "0.00" and v["tenant_id"] == acct["tenant_id"]
    listed = (await client.get(URL, headers=bearer(acct))).json()
    assert listed["total"] == 1 and listed["items"][0]["name"] == "Karachi Cloth House"
    patched = await client.patch(f"{URL}{v['id']}", json={"name": "Karachi Cloth"}, headers=bearer(acct))
    assert patched.status_code == 200 and patched.json()["name"] == "Karachi Cloth"
    tid = uuid.UUID(acct["tenant_id"])
    async with tenant_session(tid) as session:
        actions = set((await session.execute(text("SELECT action FROM audit_logs WHERE tenant_id = :t"), {"t": tid})).scalars())
    assert {"vendor.created", "vendor.updated"} <= actions


@pytest.mark.parametrize(
    ("field", "value"),
    [("name", "a"), ("name", "n" * 121), ("phone", "abc"), ("phone", "12")],
)
async def test_invalid_vendor_fields_are_422(client: AsyncClient, field: str, value: str) -> None:
    acct = await register(client, "Shop A")
    res = await client.post(URL, json={"name": "Good name", "phone": "+923001234567", field: value}, headers=bearer(acct))
    assert res.status_code == 422 and res.json()["code"] == "validation_failed"
    assert field in {e["field"] for e in res.json()["errors"]}


async def test_a_bill_raises_the_balance_and_a_payment_lowers_it_and_the_ledger_adds_up(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    v = await _vendor(client, acct)
    bill = await client.post(f"{URL}{v['id']}/bills", json={"amount": "10000.00", "reference": "INV-7"}, headers=bearer(acct))
    assert bill.status_code == 201 and bill.json()["balance"] == "10000.00"
    pay = await client.post(f"{URL}{v['id']}/payments", json={"amount": "4000.00", "method": "bank"}, headers=bearer(acct))
    assert pay.status_code == 201 and pay.json()["balance"] == "6000.00"
    assert (await client.get(f"{URL}{v['id']}", headers=bearer(acct))).json()["balance"] == "6000.00"
    ledger = (await client.get(f"{URL}{v['id']}/ledger", headers=bearer(acct))).json()
    assert [(e["direction"], e["amount"], e["balance_after"]) for e in ledger["items"]] == [
        ("credit", "4000.00", "6000.00"),
        ("debit", "10000.00", "10000.00"),
    ]


async def test_paying_more_than_is_owed_is_refused_and_changes_nothing(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    v = await _vendor(client, acct)
    await client.post(f"{URL}{v['id']}/bills", json={"amount": "500.00"}, headers=bearer(acct))
    res = await client.post(f"{URL}{v['id']}/payments", json={"amount": "500.01", "method": "cash"}, headers=bearer(acct))
    assert res.status_code == 422 and res.json()["code"] == "payment_exceeds_balance"
    assert (await client.get(f"{URL}{v['id']}", headers=bearer(acct))).json()["balance"] == "500.00"


@pytest.mark.parametrize("amount", ["0", "-5", "1.234", "abc"])
async def test_bill_and_payment_amounts_must_be_positive_money(client: AsyncClient, amount: str) -> None:
    acct = await register(client, "Shop A")
    v = await _vendor(client, acct)
    assert (await client.post(f"{URL}{v['id']}/bills", json={"amount": amount}, headers=bearer(acct))).status_code == 422
    pay = await client.post(f"{URL}{v['id']}/payments", json={"amount": amount, "method": "cash"}, headers=bearer(acct))
    assert pay.status_code == 422


async def test_a_vendor_with_a_balance_cannot_be_deleted(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    v = await _vendor(client, acct)
    await client.post(f"{URL}{v['id']}/bills", json={"amount": "100.00"}, headers=bearer(acct))
    res = await client.delete(f"{URL}{v['id']}", headers=bearer(acct))
    assert res.status_code == 422 and res.json()["code"] == "vendor_has_balance"
    await client.post(f"{URL}{v['id']}/payments", json={"amount": "100.00", "method": "cash"}, headers=bearer(acct))
    assert (await client.delete(f"{URL}{v['id']}", headers=bearer(acct))).status_code == 204
    assert (await client.get(f"{URL}{v['id']}", headers=bearer(acct))).status_code == 404


async def test_payables_report_shows_owed_overdue_and_next_due_with_oldest_bills_paid_first(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    v = await _vendor(client, acct)
    past = (date.today() - timedelta(days=10)).isoformat()
    soon = (date.today() + timedelta(days=5)).isoformat()
    await client.post(f"{URL}{v['id']}/bills", json={"amount": "1000.00", "due_date": past}, headers=bearer(acct))
    await client.post(f"{URL}{v['id']}/bills", json={"amount": "2000.00", "due_date": soon}, headers=bearer(acct))
    await client.post(f"{URL}{v['id']}/payments", json={"amount": "400.00", "method": "cash"}, headers=bearer(acct))
    paid_off = await _vendor(client, acct, name="Paid Up Traders", phone="+923009999999")
    await client.post(f"{URL}{paid_off['id']}/bills", json={"amount": "50.00"}, headers=bearer(acct))
    await client.post(f"{URL}{paid_off['id']}/payments", json={"amount": "50.00", "method": "cash"}, headers=bearer(acct))

    rows = (await client.get(f"{URL}payables", headers=bearer(acct))).json()
    assert len(rows) == 1  # a vendor owed nothing is left out
    assert (rows[0]["owed"], rows[0]["overdue"], rows[0]["next_due"]) == ("2600.00", "600.00", past)


async def test_report_is_empty_when_nothing_is_owed(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    assert (await client.get(f"{URL}payables", headers=bearer(acct))).json() == []


async def test_roles_manager_can_work_staff_cannot_and_only_the_owner_deletes_or_reports(
    client: AsyncClient, app_engine: AsyncEngine
) -> None:
    owner = await register(client, "Shop A")
    manager = await member(client, app_engine, owner, "manager")
    staff = await member(client, app_engine, owner, "staff")
    v = await _vendor(client, manager)
    assert (await client.get(URL, headers=bearer(staff))).status_code == 403
    assert (await client.post(URL, json={"name": "Nope Nope"}, headers=bearer(staff))).status_code == 403
    assert (await client.get(f"{URL}payables", headers=bearer(manager))).status_code == 403
    assert (await client.delete(f"{URL}{v['id']}", headers=bearer(manager))).status_code == 403
    assert (await client.get(f"{URL}payables", headers=bearer(owner))).status_code == 200


async def test_a_shop_never_sees_or_touches_another_shops_vendors(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    v = await _vendor(client, a)
    assert (await client.get(URL, headers=bearer(b))).json()["total"] == 0
    assert (await client.get(f"{URL}{v['id']}", headers=bearer(b))).status_code == 404
    assert (await client.post(f"{URL}{v['id']}/bills", json={"amount": "5.00"}, headers=bearer(b))).status_code == 404
    assert (await client.delete(f"{URL}{v['id']}", headers=bearer(b))).status_code == 404


async def test_client_supplied_tenant_id_and_balance_are_ignored_or_rejected(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    res = await client.post(URL, json={"name": "Sneaky Co", "tenant_id": b["tenant_id"], "balance": "999"}, headers=bearer(a))
    assert res.status_code == 201 and res.json()["tenant_id"] == a["tenant_id"] and res.json()["balance"] == "0.00"
    v = res.json()
    bad = await client.patch(f"{URL}{v['id']}", json={"balance": "5.00"}, headers=bearer(a))
    assert bad.status_code == 422
