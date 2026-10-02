"""Regression tests for the independent reviews of tasks 07 and 15: webhooks, chat isolation, CORS, routing, scheduler."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from agents import Runner
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.controllers.chat_controller import router as chat_router
from app.api.controllers.support_controller import router as vapi_router
from app.api.routers.main_router import build_main_router
from app.core.auth import get_principal
from app.core.settings import Settings, settings
from app.core.tenancy import Principal
from app.main import app as real_app
from app.models.tenant import TenantRole
from app.services import vapi_support_service


# ---------------------------------------------------------------- VAPI webhook
def _vapi() -> TestClient:
    app = FastAPI()
    app.include_router(vapi_router)
    return TestClient(app)


CALL = {"message": {"type": "function-call", "functionCall": {"name": "create_support_ticket", "arguments": {"issue": "late"}}}}


def test_vapi_runs_the_requested_tool_and_speaks_its_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_dispatch(name: str, params: dict[str, Any] | None) -> dict[str, Any]:
        seen.update(name=name, params=params)
        return {"success": True, "responseMessage": "Ticket 7 created"}

    monkeypatch.setattr(vapi_support_service, "dispatch_tool_call", fake_dispatch)
    monkeypatch.setattr(settings, "VAPI_WEBHOOK_SECRET", "s3cret")
    res = _vapi().post("/vapi/webhook", json=CALL, headers={"x-vapi-signature": "s3cret"})
    assert res.status_code == 200
    assert res.json()["message"] == "Ticket 7 created"
    assert seen == {"name": "create_support_ticket", "params": {"issue": "late"}}, "the tool must actually run"


def test_vapi_rejects_a_wrong_or_missing_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "VAPI_WEBHOOK_SECRET", "s3cret")
    assert _vapi().post("/vapi/webhook", json=CALL, headers={"x-vapi-signature": "nope"}).status_code == 401
    assert _vapi().post("/vapi/webhook", json=CALL).status_code == 401


def test_vapi_refuses_everything_in_production_when_no_secret_is_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "VAPI_WEBHOOK_SECRET", "")
    monkeypatch.setattr(settings, "APP_ENV", "production")
    assert _vapi().post("/vapi/webhook", json=CALL).status_code == 503


# ------------------------------------------------------- chat sessions per tenant
def _chat_client(tenant: uuid.UUID) -> TestClient:
    app = FastAPI()
    app.include_router(chat_router)
    app.dependency_overrides[get_principal] = lambda: Principal(user_id=uuid.uuid4(), tenant_id=tenant, role=TenantRole.owner)
    return TestClient(app)


def test_the_same_session_id_in_two_tenants_never_shares_a_conversation(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions: list[Any] = []

    async def fake_run(*args: Any, **kwargs: Any) -> SimpleNamespace:
        sessions.append(kwargs["session"])
        return SimpleNamespace(final_output="ok")

    monkeypatch.setattr(Runner, "run", fake_run)
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    a = _chat_client(tenant_a)
    b = _chat_client(tenant_b)
    sid = f"shared-{uuid.uuid4().hex[:6]}"
    for client in (a, b, a):
        res = client.post("/chat/sales", json={"message": "hi", "session_id": sid})
        assert res.json()["session_id"] == sid, "the client still sees the id it sent"
    assert sessions[0] is sessions[2], "one tenant keeps its own conversation"
    assert sessions[0] is not sessions[1], "another tenant must get a different, empty one"


def test_generated_session_ids_are_unguessable(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run(*args: Any, **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(final_output="ok")

    monkeypatch.setattr(Runner, "run", fake_run)
    client = _chat_client(uuid.uuid4())
    ids = {client.post("/chat/sales", json={"message": "hi"}).json()["session_id"] for _ in range(3)}
    assert len(ids) == 3
    assert all(i.startswith("web_") and len(i) >= 16 for i in ids)


# ------------------------------------------------------------------------- CORS
def _preflight(origin: str) -> Any:
    return TestClient(real_app).options(
        "/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
    )


def test_cors_allows_the_frontend_origin_and_nothing_else() -> None:
    assert _preflight(settings.FRONTEND_ORIGIN).headers.get("access-control-allow-origin") == settings.FRONTEND_ORIGIN
    assert "access-control-allow-origin" not in _preflight("https://evil.example").headers


def test_cors_never_uses_a_wildcard_with_credentials() -> None:
    res = _preflight("https://evil.example")
    assert res.headers.get("access-control-allow-origin") != "*"


# ----------------------------------------------- legacy routes switch and settings
def _paths(legacy: bool) -> set[str]:
    app = FastAPI()
    app.include_router(build_main_router(legacy_routes=legacy))
    return set(app.openapi()["paths"])


def test_legacy_routes_can_be_switched_off_and_the_webhooks_stay() -> None:
    on, off = _paths(True), _paths(False)
    assert any(p.startswith("/api/inventory") for p in on)
    assert not any(p.startswith(("/api/inventory", "/api/sales", "/api/vendors", "/api/chat", "/api/marketing", "/api/logs")) for p in off)
    assert {"/webhook", "/vapi/webhook"} <= off


@pytest.mark.parametrize(
    ("env", "override", "expected"),
    [("development", None, True), ("test", None, True), ("production", None, False), ("staging", None, False),
     ("production", True, True), ("development", False, False)],
)
def test_legacy_routes_default_to_off_in_production(env: str, override: bool | None, expected: bool) -> None:
    s = Settings(_env_file=None, APP_ENV=env, SECRET_KEY="x" * 32, LEGACY_V1_ROUTES=override)  # type: ignore[call-arg]
    assert s.legacy_routes_enabled is expected


# --------------------------------------------------------------------- scheduler
def test_the_marketing_scheduler_starts_and_stops_with_the_app(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    async def start() -> None:
        events.append("start")

    async def stop() -> None:
        events.append("stop")

    from app import main

    monkeypatch.setattr(main.marketing_scheduler, "start", start)
    monkeypatch.setattr(main.marketing_scheduler, "stop", stop)
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "MARKETING_SCHEDULER_ENABLED", True)
    with TestClient(real_app):
        assert events == ["start"]
    assert events == ["start", "stop"]


def test_the_scheduler_stays_off_when_disabled_or_under_test(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    async def start() -> None:
        events.append("start")

    from app import main

    monkeypatch.setattr(main.marketing_scheduler, "start", start)
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "MARKETING_SCHEDULER_ENABLED", False)
    with TestClient(real_app):
        pass
    monkeypatch.setattr(settings, "MARKETING_SCHEDULER_ENABLED", True)
    monkeypatch.setattr(settings, "APP_ENV", "test")
    with TestClient(real_app):
        pass
    assert events == []
