from __future__ import annotations

from typing import Any, Dict

import httpx  # type: ignore[import-not-found]
import pytest  # type: ignore[import-not-found]

from backend.app import app
from backend.lib import repository


@pytest.fixture(autouse=True)
def _set_db_root(tmp_path):
    repository.configure_db_root(tmp_path)
    yield


@pytest.mark.asyncio
async def test_inbound_webhook_process(monkeypatch):
    vendor = repository.upsert_vendor(
        phone_number_id="12345",
        name="Demo Vendor",
        access_token="access-token-xyz",
    )

    async def fake_runner_hook(**_: Dict[str, Any]):
        return {"reply_text": "Hello back!", "action": "reply"}

    async def fake_send_text_message(**kwargs):
        fake_send_text_message.called_with = kwargs  # type: ignore[attr-defined]
        return {"messages": [{"id": "wamid.reply"}]}

    monkeypatch.setattr("backend.runner.runner_hook", fake_runner_hook)
    monkeypatch.setattr("backend.services.whatsapp.send_text_message", fake_send_text_message)

    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "12345"},
                            "contacts": [
                                {
                                    "wa_id": "447700900123",
                                    "profile": {"name": "John"},
                                }
                            ],
                            "messages": [
                                {
                                    "from": "447700900123",
                                    "id": "wamid.inbound",
                                    "timestamp": "1700000000",
                                    "type": "text",
                                    "text": {"body": "Hi"},
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    }

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/webhook", json=payload)

    assert response.status_code == 200
    messages = repository.list_messages(vendor["vendor_id"], "447700900123")
    assert len(messages) == 2  # inbound + outbound
    assert messages[0]["direction"] == "inbound"
    assert messages[1]["direction"] == "outbound"
    assert getattr(fake_send_text_message, "called_with")["body"] == "Hello back!"


@pytest.mark.asyncio
async def test_webhook_verification():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/webhook",
            params={"hub.mode": "subscribe", "hub.verify_token": "test123", "hub.challenge": "abc"},
        )
    assert response.status_code == 200
    assert response.text == "abc"
