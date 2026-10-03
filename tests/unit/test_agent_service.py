"""Task 28: the agent service runs separately from the API and holds no database credentials.

The owner decided to keep this task (ADR 0003): agents can run in their own process that reaches business data only
through the API. These tests prove the skeleton starts and cannot be started with database access.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_service.guards import DatabaseCredentialsPresent, assert_no_database_environment, find_database_variables
from agent_service.main import create_app
from agent_service.settings import AgentServiceSettings

TOKEN = "agent-service-test-token-0123456789"


def _client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    for name in list(__import__("os").environ):
        if find_database_variables({name: "x"}):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AGENT_SERVICE_TOKEN", TOKEN)
    return TestClient(create_app(AgentServiceSettings(AGENT_SERVICE_TOKEN=TOKEN)))


def test_the_service_starts_and_answers_health(monkeypatch: pytest.MonkeyPatch) -> None:
    with _client(monkeypatch) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "agent-service"}


def test_run_requires_the_service_token(monkeypatch: pytest.MonkeyPatch) -> None:
    with _client(monkeypatch) as client:
        assert client.post("/v1/run", json={"agent": "sales", "message": "hi"}).status_code == 401
        wrong = client.post(
            "/v1/run", json={"agent": "sales", "message": "hi"}, headers={"X-Agent-Service-Token": "no"}
        )
        assert wrong.status_code == 401


def test_run_validates_the_request_and_is_honest_about_not_being_wired_yet(monkeypatch: pytest.MonkeyPatch) -> None:
    headers = {"X-Agent-Service-Token": TOKEN}
    with _client(monkeypatch) as client:
        assert client.post("/v1/run", json={"agent": "sales"}, headers=headers).status_code == 422
        assert client.post("/v1/run", json={"agent": "nope", "message": "hi"}, headers=headers).status_code == 422
        ok = client.post("/v1/run", json={"agent": "sales", "message": "hi"}, headers=headers)
    assert ok.status_code == 501, "the skeleton must not pretend to run agents until they reach data through the API"


def test_the_service_refuses_to_start_when_a_database_variable_is_in_its_environment() -> None:
    for name in (
        "DATABASE_URL",
        "DATABASE_URL_MIGRATIONS",
        "POSTGRES_PASSWORD",
        "SUPABASE_DB_URL",
        "PGPASSWORD",
        "DB_HOST",
        "POSTGRESQL_URL",
        "DB_DSN",
        "SQLALCHEMY_DATABASE_URI",
    ):
        with pytest.raises(DatabaseCredentialsPresent) as raised:
            assert_no_database_environment({name: "postgresql://x", "PATH": "/bin"})
        assert name in str(raised.value)


def test_startup_enforces_the_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://app_user:secret@host/db")
    monkeypatch.setenv("AGENT_SERVICE_TOKEN", TOKEN)
    app: FastAPI = create_app(AgentServiceSettings(AGENT_SERVICE_TOKEN=TOKEN))
    with pytest.raises(DatabaseCredentialsPresent):
        with TestClient(app):
            pass


def test_a_connection_string_is_caught_whatever_the_variable_is_called() -> None:
    for value in ("postgresql://u:p@h/db", "postgresql+asyncpg://u:p@h/db", "mysql://u:p@h/db", "sqlite:///x.db"):
        assert find_database_variables({"MY_INNOCENT_LOOKING_NAME": value}) == ["MY_INNOCENT_LOOKING_NAME"]
    assert find_database_variables({"API_BASE_URL": "http://backend:8000"}) == []


def test_ordinary_variables_are_not_mistaken_for_database_ones() -> None:
    env = {"API_BASE_URL": "http://api", "GEMINI_API_KEY": "k", "PATH": "/bin", "DEBUG": "1", "DBUS_SESSION_BUS": "x"}
    assert find_database_variables(env) == []
    assert_no_database_environment(env)


def test_settings_declare_no_database_field() -> None:
    names = " ".join(AgentServiceSettings.model_fields).upper()
    assert not any(word in names for word in ("DATABASE", "POSTGRES", "SUPABASE", "PGHOST", "DB_"))


def test_the_token_is_mandatory_outside_tests() -> None:
    with pytest.raises(ValueError, match="AGENT_SERVICE_TOKEN"):
        AgentServiceSettings(APP_ENV="production", AGENT_SERVICE_TOKEN="")
