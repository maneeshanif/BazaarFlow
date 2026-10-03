"""Task 38: posting a sale follows PRD F-007, one test per rule, plus atomicity, idempotency and concurrency."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.tenancy import tenant_session
from tests.pg.conftest import bearer, member, register

pytestmark = pytest.mark.pg

SALES = "/api/v1/sales/"
STOCK = "/api/v1/inventory/"


async def product(client: AsyncClient, acct: dict[str, Any], sku: str, price: str = "100.00", qty: int = 10, **over: Any) -> dict[str, Any]:
    body = {"sku": sku, "name": f"Item {sku}", "price": price, "cost": "60.00", "qty_on_hand": qty, **over}
    res = await client.post(STOCK, json=body, headers=bearer(acct))
    assert res.status_code == 201, res.text
    made: dict[str, Any] = res.json()
    return made


async def customer(client: AsyncClient, acct: dict[str, Any], phone: str = "+923001110001") -> dict[str, Any]:
    res = await client.post("/api/v1/customers/", json={"phone": phone, "name": "Ali"}, headers=bearer(acct))
    assert res.status_code == 201, res.text
    made: dict[str, Any] = res.json()
    return made


def sale(items: list[tuple[dict[str, Any], int]], **over: Any) -> dict[str, Any]:
    return {"items": [{"product_id": p["id"], "qty": q} for p, q in items], "payment_method": "cash", **over}


async def qty(client: AsyncClient, acct: dict[str, Any], p: dict[str, Any]) -> int:
    got: int = (await client.get(f"{STOCK}{p['id']}", headers=bearer(acct))).json()["qty_on_hand"]
    return got


async def test_a_cash_sale_posts_everything_together(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    shirt = await product(client, acct, "SHIRT", "2500.00", 10)
    res = await client.post(SALES, json=sale([(shirt, 3)], note="Eid order"), headers=bearer(acct))
    assert res.status_code == 201, res.text
    order = res.json()
    assert (order["status"], order["channel"], order["subtotal"], order["discount"], order["total"]) == ("posted", "pos", "7500.00", "0.00", "7500.00")
    assert (order["amount_paid"], order["amount_due"], order["item_count"], order["note"]) == ("7500.00", "0.00", 1, "Eid order")
    assert order["items"][0]["qty"] == 3 and order["items"][0]["unit_price"] == "2500.00" and order["items"][0]["line_total"] == "7500.00"
    assert [(p["amount"], p["method"], p["status"]) for p in order["payments"]] == [("7500.00", "cash", "completed")]

    assert await qty(client, acct, shirt) == 7
    moves = (await client.get(f"{STOCK}{shirt['id']}/stock-movements", headers=bearer(acct))).json()["items"]
    assert (moves[0]["delta"], moves[0]["reason"], moves[0]["ref_type"], moves[0]["ref_id"]) == (-3, "sale", "order", order["id"])

    tenant_id = uuid.UUID(acct["tenant_id"])
    async with tenant_session(tenant_id) as db:
        audited = set((await db.execute(text("SELECT action FROM audit_logs WHERE tenant_id = :t"), {"t": tenant_id})).scalars())
        entries = (await db.execute(text("SELECT count(*) FROM ledger_entries"))).scalar_one()
    assert "order.posted" in audited and entries == 0


async def test_the_discount_comes_off_the_total_and_cannot_exceed_the_items(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A", "1000.00")
    ok = await client.post(SALES, json=sale([(p, 2)], discount="150.50"), headers=bearer(acct))
    assert (ok.json()["subtotal"], ok.json()["discount"], ok.json()["total"], ok.json()["amount_paid"]) == ("2000.00", "150.50", "1849.50", "1849.50")
    over = await client.post(SALES, json=sale([(p, 1)], discount="1000.01"), headers=bearer(acct))
    assert over.status_code == 422 and over.json()["code"] == "discount_exceeds_subtotal"
    assert (await client.post(SALES, json=sale([(p, 1)], discount="-1"), headers=bearer(acct))).status_code == 422
    assert (await client.post(SALES, json=sale([(p, 1)], discount="1.234"), headers=bearer(acct))).status_code == 422


@pytest.mark.parametrize("bad", [{"items": []}, {"items": [{"qty": 1}]}])
async def test_a_sale_needs_at_least_one_valid_line(client: AsyncClient, bad: dict[str, Any]) -> None:
    acct = await register(client, "Shop A")
    res = await client.post(SALES, json={**bad, "payment_method": "cash"}, headers=bearer(acct))
    assert res.status_code == 422


async def test_each_line_needs_a_positive_whole_quantity(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A")
    for q in (0, -2, 1.5):
        res = await client.post(SALES, json={"items": [{"product_id": p["id"], "qty": q}], "payment_method": "cash"}, headers=bearer(acct))
        assert res.status_code == 422, q
    assert await qty(client, acct, p) == 10


async def test_the_price_defaults_to_the_products_and_can_be_changed_per_line(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A", "500.00")
    custom = await client.post(
        SALES, json={"items": [{"product_id": p["id"], "qty": 2, "unit_price": "450.00"}], "payment_method": "cash"}, headers=bearer(acct)
    )
    assert custom.json()["total"] == "900.00"
    assert (await client.post(SALES, json={"items": [{"product_id": p["id"], "qty": 1, "unit_price": "-1"}], "payment_method": "cash"}, headers=bearer(acct))).status_code == 422
    # history is not rewritten when the price changes later
    await client.patch(f"{STOCK}{p['id']}", json={"price": "999.00"}, headers=bearer(acct))
    again = (await client.get(f"/api/v1/orders/{custom.json()['id']}", headers=bearer(acct))).json()
    assert again["items"][0]["unit_price"] == "450.00" and again["total"] == "900.00"


async def test_money_adds_up_exactly(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A", "0.10", 100)
    res = await client.post(SALES, json=sale([(p, 3)]), headers=bearer(acct))
    assert (res.json()["subtotal"], res.json()["total"]) == ("0.30", "0.30")  # binary floats would give 0.30000000000000004


async def test_a_sale_on_credit_needs_a_customer_and_goes_on_their_udhaar(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A", "1000.00")
    ali = await customer(client, acct)
    no_customer = await client.post(SALES, json=sale([(p, 1)], payment_method="udhaar"), headers=bearer(acct))
    assert no_customer.status_code == 422 and no_customer.json()["code"] == "customer_required_for_credit"
    assert await qty(client, acct, p) == 10

    credit = await client.post(SALES, json=sale([(p, 2)], payment_method="udhaar", customer_id=ali["id"]), headers=bearer(acct))
    assert credit.status_code == 201, credit.text
    assert (credit.json()["amount_paid"], credit.json()["amount_due"], credit.json()["payments"]) == ("0.00", "2000.00", [])
    assert (await client.get(f"/api/v1/customers/{ali['id']}", headers=bearer(acct))).json()["balance"] == "2000.00"
    ledger = (await client.get(f"/api/v1/customers/{ali['id']}/ledger", headers=bearer(acct))).json()["items"]
    assert (ledger[0]["direction"], ledger[0]["amount"], ledger[0]["ref_type"], ledger[0]["ref_id"]) == ("debit", "2000.00", "order", credit.json()["id"])


async def test_a_part_payment_puts_only_the_rest_on_udhaar(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A", "1000.00")
    ali = await customer(client, acct)
    res = await client.post(SALES, json=sale([(p, 3)], customer_id=ali["id"], amount_paid="1200.00", payment_method="bank"), headers=bearer(acct))
    assert res.status_code == 201, res.text
    assert (res.json()["total"], res.json()["amount_paid"], res.json()["amount_due"]) == ("3000.00", "1200.00", "1800.00")
    assert [(x["amount"], x["method"]) for x in res.json()["payments"]] == [("1200.00", "bank")]
    assert (await client.get(f"/api/v1/customers/{ali['id']}", headers=bearer(acct))).json()["balance"] == "1800.00"
    # paying less than the total without naming a customer is refused, and nothing is sold
    anon = await client.post(SALES, json=sale([(p, 1)], amount_paid="500.00"), headers=bearer(acct))
    assert anon.status_code == 422 and anon.json()["code"] == "customer_required_for_credit"
    assert await qty(client, acct, p) == 7


async def test_the_amount_paid_cannot_exceed_the_total_and_udhaar_means_nothing_paid(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A", "100.00")
    ali = await customer(client, acct)
    over = await client.post(SALES, json=sale([(p, 1)], amount_paid="100.01"), headers=bearer(acct))
    assert over.status_code == 422 and over.json()["code"] == "paid_exceeds_total"
    mixed = await client.post(SALES, json=sale([(p, 1)], payment_method="udhaar", customer_id=ali["id"], amount_paid="50.00"), headers=bearer(acct))
    assert mixed.status_code == 422
    assert (await client.post(SALES, json=sale([(p, 1)], amount_paid="-1"), headers=bearer(acct))).status_code == 422
    free = await client.post(SALES, json=sale([(p, 1)], discount="100.00"), headers=bearer(acct))
    assert free.status_code == 201 and free.json()["total"] == "0.00" and free.json()["payments"] == []


async def test_products_and_customers_must_belong_to_this_shop_and_be_for_sale(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    mine = await product(client, a, "A")
    theirs = await product(client, b, "B")
    other_customer = await customer(client, b)
    foreign = await client.post(SALES, json=sale([(theirs, 1)]), headers=bearer(a))
    assert foreign.status_code == 422 and foreign.json()["code"] == "unknown_product"
    stranger = await client.post(SALES, json=sale([(mine, 1)], customer_id=other_customer["id"]), headers=bearer(a))
    assert stranger.status_code == 422 and stranger.json()["code"] == "unknown_customer"
    await client.patch(f"{STOCK}{mine['id']}", json={"active": False}, headers=bearer(a))
    inactive = await client.post(SALES, json=sale([(mine, 1)]), headers=bearer(a))
    assert inactive.status_code == 422 and inactive.json()["code"] == "product_inactive"
    assert (await client.post(SALES, json=sale([({"id": str(uuid.uuid4())}, 1)]), headers=bearer(a))).json()["code"] == "unknown_product"


async def test_not_enough_stock_refuses_the_whole_sale_and_changes_nothing(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    plenty = await product(client, acct, "PLENTY", qty=10)
    scarce = await product(client, acct, "SCARCE", qty=2)
    res = await client.post(SALES, json=sale([(plenty, 4), (scarce, 3)]), headers=bearer(acct))
    assert res.status_code == 422 and res.json()["code"] == "insufficient_stock"
    assert "2 on hand, 3 needed" in res.json()["detail"]
    assert (await qty(client, acct, plenty), await qty(client, acct, scarce)) == (10, 2), "the first line must not have been taken out"
    assert (await client.get("/api/v1/orders/", headers=bearer(acct))).json()["total"] == 0


async def test_the_same_product_on_two_lines_is_checked_together(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A", qty=5)
    res = await client.post(SALES, json=sale([(p, 3), (p, 3)]), headers=bearer(acct))
    assert res.status_code == 422 and res.json()["code"] == "insufficient_stock"
    ok = await client.post(SALES, json=sale([(p, 2), (p, 3)]), headers=bearer(acct))
    assert ok.status_code == 201 and ok.json()["item_count"] == 2
    assert await qty(client, acct, p) == 0


async def test_only_a_manager_may_sell_more_than_is_on_the_shelf_and_it_is_recorded(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    manager = await member(client, app_engine, owner, "manager")
    staff = await member(client, app_engine, owner, "staff")
    p = await product(client, owner, "A", qty=2)
    refused = await client.post(SALES, json=sale([(p, 5)], stock_override=True), headers=bearer(staff))
    assert refused.status_code == 403 and refused.json()["code"] == "override_needs_manager"
    assert await qty(client, owner, p) == 2

    done = await client.post(SALES, json=sale([(p, 5)], stock_override=True), headers=bearer(manager))
    assert done.status_code == 201, done.text
    assert await qty(client, owner, p) == 0, "the shelf count is corrected, then the sale takes it to zero"
    moves = (await client.get(f"{STOCK}{p['id']}/stock-movements", headers=bearer(owner))).json()["items"]
    assert [(m["delta"], m["reason"]) for m in moves] == [(-5, "sale"), (3, "adjustment"), (2, "opening")]
    tenant_id = uuid.UUID(owner["tenant_id"])
    async with tenant_session(tenant_id) as db:
        actions = set((await db.execute(text("SELECT action FROM audit_logs WHERE tenant_id = :t"), {"t": tenant_id})).scalars())
    assert "order.stock_override" in actions
    # an override is not needed (and changes nothing) when the stock is there
    assert (await client.post(SALES, json=sale([(p, 1)], stock_override=True), headers=bearer(manager))).status_code == 201


async def test_a_retried_request_with_the_same_key_returns_the_same_sale(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A", qty=10)
    headers = {**bearer(acct), "Idempotency-Key": "retry-key-0001"}
    first = await client.post(SALES, json=sale([(p, 2)]), headers=headers)
    second = await client.post(SALES, json=sale([(p, 2)]), headers=headers)
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["id"] == second.json()["id"]
    assert await qty(client, acct, p) == 8, "stock was taken out once"
    other = await client.post(SALES, json=sale([(p, 2)]), headers={**bearer(acct), "Idempotency-Key": "retry-key-0002"})
    assert other.status_code == 201 and other.json()["id"] != first.json()["id"]
    assert (await client.post(SALES, json=sale([(p, 1)]), headers={**bearer(acct), "Idempotency-Key": "short"})).status_code == 422


async def test_two_simultaneous_retries_make_one_sale(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A", qty=10)
    headers = {**bearer(acct), "Idempotency-Key": "race-key-000001"}
    results = await asyncio.gather(*[client.post(SALES, json=sale([(p, 2)]), headers=headers) for _ in range(2)])
    assert {r.json()["id"] for r in results} == {results[0].json()["id"]}
    assert sorted(r.status_code for r in results) == [200, 201]
    assert await qty(client, acct, p) == 8
    assert (await client.get("/api/v1/orders/", headers=bearer(acct))).json()["total"] == 1


async def test_the_last_unit_cannot_be_sold_twice(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A", qty=1)
    results = await asyncio.gather(*[client.post(SALES, json=sale([(p, 1)]), headers=bearer(acct)) for _ in range(3)])
    assert sorted(r.status_code for r in results) == [201, 422, 422]
    assert await qty(client, acct, p) == 0


async def test_staff_can_sell_but_never_see_cost_while_a_manager_does(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    manager = await member(client, app_engine, owner, "manager")
    staff = await member(client, app_engine, owner, "staff")
    p = await product(client, owner, "A", cost="40.00")
    made = await client.post(SALES, json=sale([(p, 1)]), headers=bearer(staff))
    assert made.status_code == 201
    assert made.json()["items"][0]["unit_cost"] is None
    assert (await client.get(f"/api/v1/orders/{made.json()['id']}", headers=bearer(manager))).json()["items"][0]["unit_cost"] == "40.00"
    assert (await client.post(SALES, json=sale([(p, 1)]))).status_code == 401


async def test_the_channel_is_set_by_the_source_not_the_caller(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A")
    res = await client.post(SALES, json=sale([(p, 1)], channel="whatsapp", tenant_id=str(uuid.uuid4()), status="draft"), headers=bearer(acct))
    assert res.status_code == 201
    assert (res.json()["channel"], res.json()["status"]) == ("pos", "posted")
    assert res.json()["created_by"] is not None


async def test_orders_are_listed_filtered_and_isolated_per_shop(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    pa = await product(client, a, "A", "100.00", 50)
    pb = await product(client, b, "B", "100.00", 50)
    ali = await customer(client, a)
    first = (await client.post(SALES, json=sale([(pa, 1)]), headers=bearer(a))).json()
    credit = (await client.post(SALES, json=sale([(pa, 2)], payment_method="udhaar", customer_id=ali["id"]), headers=bearer(a))).json()
    await client.post(SALES, json=sale([(pb, 1)]), headers=bearer(b))

    listing = (await client.get("/api/v1/orders/", headers=bearer(a))).json()
    assert listing["total"] == 2 and [o["id"] for o in listing["items"]] == [credit["id"], first["id"]]  # newest first
    by_customer = (await client.get("/api/v1/orders/", params={"customer_id": ali["id"]}, headers=bearer(a))).json()
    assert [(o["id"], o["customer_name"], o["amount_due"]) for o in by_customer["items"]] == [(credit["id"], "Ali", "200.00")]
    assert (await client.get("/api/v1/orders/", params={"q": "Ali"}, headers=bearer(a))).json()["total"] == 1
    assert (await client.get("/api/v1/orders/", params={"q": "Item A"}, headers=bearer(a))).json()["total"] == 2
    assert (await client.get("/api/v1/orders/", params={"status": "reversed"}, headers=bearer(a))).json()["total"] == 0
    assert (await client.get("/api/v1/orders/", params={"status": "bogus"}, headers=bearer(a))).status_code == 422
    assert (await client.get("/api/v1/orders/", params={"sort": "tenant_id"}, headers=bearer(a))).status_code == 400
    by_total = (await client.get("/api/v1/orders/", params={"sort": "-total", "limit": 1}, headers=bearer(a))).json()
    assert by_total["items"][0]["id"] == credit["id"] and by_total["next_cursor"]

    assert (await client.get(f"/api/v1/orders/{first['id']}", headers=bearer(b))).status_code == 404
    assert (await client.get(f"/api/v1/orders/{uuid.uuid4()}", headers=bearer(a))).status_code == 404


async def test_the_preview_adds_up_a_sale_without_writing_anything(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    a = await product(client, acct, "A", "100.50", 5)
    b = await product(client, acct, "B", "20.00", 1)
    res = await client.post(
        "/api/v1/sales/preview",
        json={"items": [{"product_id": a["id"], "qty": 2}, {"product_id": b["id"], "qty": 3, "unit_price": "19.99"}], "discount": "10.00"},
        headers=bearer(acct),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["subtotal"], body["discount"], body["total"]) == ("260.97", "10.00", "250.97")
    assert (body["amount_paid"], body["amount_due"]) == ("250.97", "0.00")
    split = await client.post(
        "/api/v1/sales/preview",
        json={"items": [{"product_id": a["id"], "qty": 2}], "payment_method": "bank", "amount_paid": "100.00"},
        headers=bearer(acct),
    )
    assert (split.json()["total"], split.json()["amount_paid"], split.json()["amount_due"]) == ("201.00", "100.00", "101.00")
    credit = await client.post("/api/v1/sales/preview", json={"items": [{"product_id": a["id"], "qty": 2}], "payment_method": "udhaar"}, headers=bearer(acct))
    assert (credit.json()["amount_paid"], credit.json()["amount_due"]) == ("0.00", "201.00")
    overpaid = await client.post("/api/v1/sales/preview", json={"items": [{"product_id": a["id"], "qty": 1}], "amount_paid": "999"}, headers=bearer(acct))
    assert "amount paid cannot be more" in overpaid.json()["warnings"][0]
    assert [(ln["line_total"], ln["available"], ln["enough_stock"]) for ln in body["lines"]] == [("201.00", 5, True), ("59.97", 1, False)]
    assert body["warnings"] == ["Not enough stock for Item B: 1 on hand, 3 needed"]
    assert (await qty(client, acct, a), await qty(client, acct, b)) == (5, 1), "a preview never changes stock"
    assert (await client.get("/api/v1/orders/", headers=bearer(acct))).json()["total"] == 0

    too_much = await client.post("/api/v1/sales/preview", json={"items": [{"product_id": a["id"], "qty": 1}], "discount": "500.00"}, headers=bearer(acct))
    assert "discount cannot be more than" in too_much.json()["warnings"][0]
    empty = await client.post("/api/v1/sales/preview", json={"items": []}, headers=bearer(acct))
    assert (empty.json()["subtotal"], empty.json()["total"], empty.json()["lines"]) == ("0.00", "0.00", [])
    other = await register(client, "Shop B")
    foreign = await client.post("/api/v1/sales/preview", json={"items": [{"product_id": a["id"], "qty": 1}]}, headers=bearer(other))
    assert foreign.json()["lines"] == [] and foreign.json()["warnings"]
