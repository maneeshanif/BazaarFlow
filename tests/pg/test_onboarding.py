"""Task 70 (F-003, W-001): the onboarding wizard: roles, each field rule, the state machine, CSV import, the test message."""

from __future__ import annotations

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.pg.channel_support import FakeProviders, connect_twilio
from tests.pg.conftest import bearer, member, register
from tests.unit.provider_support import fixture_json

pytestmark = pytest.mark.pg

URL = "/api/v1/onboarding/"
SHOP = {"name": "Ali Mart Lahore", "owner_phone": "+923001234567", "city": "Lahore"}
CSV = "sku,name,price,cost,qty,category\nSH-1,Classic Shirt,2500,1800,10,Clothes\nCAP-1,Cap,500,,5,\n"


async def state(client: AsyncClient, owner: dict[str, object]) -> dict[str, object]:
    out: dict[str, object] = (await client.get(URL, headers=bearer(owner))).json()
    return out


async def through_products(client: AsyncClient, owner: dict[str, object]) -> None:
    assert (await client.put(f"{URL}shop", json=SHOP, headers=bearer(owner))).status_code == 200
    assert (await client.post(f"{URL}channels/continue", headers=bearer(owner))).status_code == 200
    assert (await client.post(f"{URL}products/continue", headers=bearer(owner))).status_code == 200


async def test_a_new_shop_starts_at_the_first_step_and_only_the_owner_can_use_the_wizard(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    body = await state(client, owner)
    assert body["state"] == "created" and [s["status"] for s in body["steps"]] == ["current", "pending", "pending", "pending"]  # type: ignore[union-attr]
    assert [s["required"] for s in body["steps"]] == [True, False, False, False]  # type: ignore[union-attr]
    for role in ("manager", "staff"):
        other = await member(client, app_engine, owner, role)
        assert (await client.get(URL, headers=bearer(other))).status_code == 403
        assert (await client.put(f"{URL}shop", json=SHOP, headers=bearer(other))).status_code == 403
        assert (await client.post(f"{URL}finish", headers=bearer(other))).status_code == 403
    assert (await client.get(URL)).status_code == 401


@pytest.mark.parametrize(
    ("over", "field"),
    [
        ({"name": "a"}, "name"),
        ({"name": "n" * 81}, "name"),
        ({"owner_phone": "03001234567"}, "owner_phone"),
        ({"owner_phone": ""}, "owner_phone"),
        ({"city": "c" * 61}, "city"),
        ({"plan": "free"}, "plan"),
    ],
)
async def test_each_shop_detail_rule_is_enforced(client: AsyncClient, over: dict[str, str], field: str) -> None:
    owner = await register(client, "Shop A")
    res = await client.put(f"{URL}shop", json={**SHOP, **over}, headers=bearer(owner))
    assert res.status_code == 422 and res.json()["code"] == "validation_failed" and field in {e["field"] for e in res.json()["errors"]}
    assert (await state(client, owner))["state"] == "created"  # nothing moved


async def test_the_shop_step_is_required_and_the_others_cannot_jump_ahead(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    for path in ("channels/continue", "products/continue", "test-message", "finish"):
        res = await client.post(f"{URL}{path}", headers=bearer(owner))
        assert res.status_code == 409 and res.json()["code"] == "step_order", path
    assert (await client.post(f"{URL}products/import", json={"csv": CSV}, headers=bearer(owner))).status_code in (200, 422)  # allowed, but does not advance
    assert (await state(client, owner))["state"] == "created"


async def test_saving_the_shop_details_updates_the_shop_and_moves_to_shop_set(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    body = (await client.put(f"{URL}shop", json=SHOP, headers=bearer(owner))).json()
    assert body["state"] == "shop_set" and body["shop_name"] == "Ali Mart Lahore" and body["owner_phone"] == "+923001234567"
    assert [s["status"] for s in body["steps"]] == ["done", "current", "pending", "pending"]
    assert (await client.get("/api/v1/settings/shop", headers=bearer(owner))).json()["city"] == "Lahore"
    again = (await client.put(f"{URL}shop", json={**SHOP, "city": "Karachi"}, headers=bearer(owner))).json()
    assert again["state"] == "shop_set"  # saving again never moves it backwards or forwards


async def test_every_step_after_the_shop_can_be_skipped_all_the_way_to_live(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    await through_products(client, owner)
    assert (await state(client, owner))["state"] == "products_added"
    live = (await client.post(f"{URL}finish", headers=bearer(owner))).json()
    assert live["state"] == "live" and all(s["status"] == "done" for s in live["steps"])


async def test_the_state_never_moves_backwards(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    await through_products(client, owner)
    await client.post(f"{URL}finish", headers=bearer(owner))
    await client.post(f"{URL}channels/continue", headers=bearer(owner))
    await client.put(f"{URL}shop", json=SHOP, headers=bearer(owner))
    assert (await state(client, owner))["state"] == "live"


async def test_a_csv_import_adds_valid_rows_and_lists_each_bad_row_with_its_line(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    await client.put(f"{URL}shop", json=SHOP, headers=bearer(owner))
    await client.post(f"{URL}channels/continue", headers=bearer(owner))
    text = (
        "SKU,Product,Price,Cost,Quantity,Category\n"
        "SH-1,Classic Shirt,2500,1800,10,Clothes\n"
        "SH-1,Duplicate shirt,100,,1,\n"  # line 3: duplicate sku
        ",No sku,100,,1,\n"  # line 4: missing sku
        "BAD-1,Bad price,abc,,1,\n"  # line 5
        "BAD-2,Negative,-5,,1,\n"  # line 6
        "BAD-3,Stock text,100,,lots,\n"  # line 7
        "OK-2,Fine cap,\"1,200\",,3,\n"  # line 8: a quoted thousands separator is fine
        "\n"
    )
    report = (await client.post(f"{URL}products/import", json={"csv": text}, headers=bearer(owner))).json()
    assert report["imported"] == 2 and report["state"] == "products_added"
    assert [(e["row"], e["sku"]) for e in report["failed"]] == [(3, "SH-1"), (4, None), (5, "BAD-1"), (6, "BAD-2"), (7, "BAD-3")]
    assert "already exists" in report["failed"][0]["error"] and all(e["error"] for e in report["failed"])
    products = (await client.get("/api/v1/inventory/", headers=bearer(owner))).json()
    assert {p["sku"] for p in products["items"]} == {"SH-1", "OK-2"}
    shirt = next(p for p in products["items"] if p["sku"] == "SH-1")
    assert (shirt["qty_on_hand"], shirt["price"], shirt["cost"]) == (10, "2500.00", "1800.00")


async def test_a_file_without_the_needed_columns_or_too_big_is_refused_as_a_whole(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    bad = await client.post(f"{URL}products/import", json={"csv": "name,qty\nShirt,3\n"}, headers=bearer(owner))
    assert bad.status_code == 422 and bad.json()["code"] == "bad_csv_header"
    many = "sku,name,price\n" + "".join(f"S{i},Item {i},10\n" for i in range(501))
    big = await client.post(f"{URL}products/import", json={"csv": many}, headers=bearer(owner))
    assert big.status_code == 422 and big.json()["code"] == "too_many_rows"
    assert (await client.get("/api/v1/inventory/", headers=bearer(owner))).json()["total"] == 0  # nothing half imported
    assert (await client.post(f"{URL}products/import", json={"csv": ""}, headers=bearer(owner))).status_code == 422
    assert (await client.post(f"{URL}products/import", json={"csv": "x" * 200_001}, headers=bearer(owner))).status_code == 422


async def test_a_successful_test_message_goes_to_the_owners_phone_and_makes_the_shop_live(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    await through_products(client, owner)
    res = await client.post(f"{URL}test-message", headers=bearer(owner))
    assert res.status_code == 200 and res.json()["sent"] is True and res.json()["state"] == "live"
    sent = providers.calls("twilio.send")
    assert len(sent) == 1 and b"whatsapp%3A%2B923001234567" in sent[0].content


async def test_a_test_message_that_cannot_be_sent_explains_why_and_blocks_nothing(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    await through_products(client, owner)  # WhatsApp was skipped
    res = await client.post(f"{URL}test-message", headers=bearer(owner))
    assert res.status_code == 200 and res.json()["sent"] is False and "sandbox" in res.json()["detail"]
    assert res.json()["state"] == "products_added"
    await connect_twilio(client, owner)
    providers.on("twilio.send", httpx.Response(400, json=fixture_json("twilio_error_63015.json")))
    joined = await client.post(f"{URL}test-message", headers=bearer(owner))
    assert joined.json()["sent"] is False and "join" in joined.json()["detail"]
    providers.on("twilio.send", httpx.ReadTimeout("slow"))
    down = await client.post(f"{URL}test-message", headers=bearer(owner))
    assert down.json()["sent"] is False and "skip" in down.json()["detail"]
    assert (await client.post(f"{URL}finish", headers=bearer(owner))).json()["state"] == "live"  # skipping still works


async def test_a_shop_only_ever_changes_its_own_onboarding(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    await client.put(f"{URL}shop", json=SHOP, headers=bearer(a))
    assert (await state(client, b))["state"] == "created" and (await state(client, b))["shop_name"] == "Shop B"
