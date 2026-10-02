"""Tests for vendor manual send endpoint behaviour."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.main as app_module
from app.repositories import repository
from app.services.whatsapp import WhatsAppAPIError


@pytest.fixture(autouse=True)
def _configure_db(tmp_path: Path) -> Any:
    repository.configure_db_root(tmp_path)
    yield


@pytest.fixture
def client() -> Any:
    return TestClient(app_module.app)


@pytest.fixture
def vendor_id() -> Any:
    vendor = repository.upsert_vendor(
        phone_number_id="111222333",
        access_token="test-access-token",
        name="Test Vendor",
    )
    return vendor["vendor_id"]


def test_manual_send_normalizes_phone(client: Any, vendor_id: Any, monkeypatch: Any) -> None:
    sent_messages: list[dict[str, Any]] = []

    async def fake_send_text_message(**kwargs: Any) -> Any:
        sent_messages.append(kwargs)
        return {"status": "sent"}

    monkeypatch.setattr(
        "app.services.whatsapp.send_text_message",
        fake_send_text_message,
    )

    response = client.post(
        f"/api/vendors/{vendor_id}/customers/+923001234567/messages",
        json={"text": "Hello from dashboard"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "sent"

    called_to = sent_messages[0]["to"]
    assert called_to == "923001234567"

    messages = repository.list_messages(vendor_id, "923001234567")
    assert messages, "Expected message record to be created"
    assert messages[-1]["direction"] == "outbound"


def test_manual_send_surfaces_whatsapp_error(client: Any, vendor_id: Any, monkeypatch: Any) -> None:
    async def failing_send_text_message(**kwargs: Any) -> None:
        raise WhatsAppAPIError(
            "Recipient has not opted in (code 470)",
            status_code=470,
            payload={"status": 470, "body": {"error": {"code": 470}}},
        )

    monkeypatch.setattr(
        "app.services.whatsapp.send_text_message",
        failing_send_text_message,
    )

    response = client.post(
        f"/api/vendors/{vendor_id}/customers/+923009876543/messages",
        json={"text": "Manual test"},
    )

    assert response.status_code == 470
    body = response.json()
    assert body["detail"].startswith("Recipient has not opted in")

    messages = repository.list_messages(vendor_id, "923009876543")
    assert len(messages) == 1
    recorded = messages[0]
    assert recorded["direction"] == "outbound"
    assert recorded["raw_payload"]["status"] == "send_failed"
    assert recorded["raw_payload"]["source"] == "whatsapp_api"