from __future__ import annotations

from pathlib import Path

import pytest  # type: ignore[import-not-found]

from backend.lib import repository


def _configure(tmp_path: Path) -> None:
    repository.configure_db_root(tmp_path)


def test_vendor_customer_message_cycle(tmp_path: Path) -> None:
    _configure(tmp_path)

    vendor = repository.upsert_vendor(phone_number_id="12345", name="Test Vendor")
    assert vendor["phone_number_id"] == "12345"

    found = repository.get_vendor_by_phone_number_id("12345")
    assert found is not None

    customer = repository.upsert_customer(vendor["vendor_id"], phone="+123", name="Alice")
    assert customer["phone"] == "+123"

    repository.record_message(
        vendor_id=vendor["vendor_id"],
        customer_phone="+123",
        direction="inbound",
        text="Hello",
        raw_payload={"id": "abc"},
        timestamp="2024-01-01T00:00:00+00:00",
    )

    messages = repository.list_messages(vendor["vendor_id"], "+123")
    assert len(messages) == 1
    assert messages[0]["text"] == "Hello"


@pytest.mark.parametrize("limit,expected", [(None, 3), (2, 2)])
def test_recent_messages_limit(tmp_path: Path, limit: int | None, expected: int) -> None:
    _configure(tmp_path)
    vendor = repository.upsert_vendor(phone_number_id="12345")
    repository.upsert_customer(vendor["vendor_id"], phone="+1")
    for idx in range(3):
        repository.record_message(
            vendor_id=vendor["vendor_id"],
            customer_phone="+1",
            direction="inbound",
            text=f"msg {idx}",
            raw_payload={"sequence": idx},
            timestamp=f"2024-01-01T00:00:0{idx}+00:00",
        )
    messages = repository.list_messages(vendor["vendor_id"], "+1", limit=limit)
    assert len(messages) == expected
