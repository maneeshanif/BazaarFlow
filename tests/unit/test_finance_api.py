import importlib
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

import app.main as app_module

chat_service_module = importlib.import_module("app.services.chat_service")


class DummyResp:
    def __init__(self) -> None:
        self.id = "dummy-startup-id"


class DummyWA:
    async def send_message(self, *args: Any, **kwargs: Any) -> Any:
        return DummyResp()



def test_finance_chat_endpoint(monkeypatch: Any) -> None:
    async def fake_run(*args: Any, **kwargs: Any) -> Any:
        return SimpleNamespace(final_output="Payment Status Summary:\n• Paid: 7 txns")

    monkeypatch.setattr(chat_service_module.Runner, "run", fake_run)

    client = TestClient(app_module.app)

    payload = {"message": "Show payment status"}

    res = client.post("/api/chat/finance", json=payload)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["response"].startswith("Payment Status Summary")
    assert body["session_id"].startswith("web_finance")
