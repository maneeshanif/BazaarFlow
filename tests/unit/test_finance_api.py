import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
import importlib

HERE = Path(__file__).resolve().parent
BACKEND_DIR = HERE.parent
sys.path.insert(0, str(BACKEND_DIR))

import app as app_module

chat_service_module = importlib.import_module("services.chat_service")


class DummyResp:
    def __init__(self):
        self.id = "dummy-startup-id"


class DummyWA:
    async def send_message(self, *args, **kwargs):
        return DummyResp()


@pytest.fixture(autouse=True)
def patch_wa(monkeypatch):
    monkeypatch.setattr(app_module, "wa", DummyWA())


def test_finance_chat_endpoint(monkeypatch):
    async def fake_run(*args, **kwargs):
        return SimpleNamespace(final_output="Payment Status Summary:\n• Paid: 7 txns")

    monkeypatch.setattr(chat_service_module.Runner, "run", fake_run)

    client = TestClient(app_module.fastapi_app)

    payload = {"message": "Show payment status"}

    res = client.post("/api/chat/finance", json=payload)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["response"].startswith("Payment Status Summary")
    assert body["session_id"].startswith("web_finance")
