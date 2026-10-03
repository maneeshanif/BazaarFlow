"""Task 57 acceptance: a failed request can be traced from the response id to the log line, and nothing private is logged."""

from __future__ import annotations

import json
import logging

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core import logging_config
from app.core.logging_config import JsonFormatter, RequestIdFilter
from app.core.problems import install_problem_handlers
from app.core.settings import settings
from app.middleware.request_logger import RequestLoggerMiddleware


def make_app() -> FastAPI:
    app = FastAPI()
    install_problem_handlers(app)
    app.add_middleware(RequestLoggerMiddleware)

    @app.get("/boom/{item}")
    async def boom(item: str) -> None:
        raise RuntimeError(f"secret detail for {item}")

    @app.get("/fine")
    async def fine() -> dict[str, bool]:
        logging.getLogger("bazaarflow.test").info("inside the request")
        return {"ok": True}

    return app


@pytest.fixture
def records(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    logging_config.configure_logging()
    caplog.set_level(logging.INFO)
    return caplog


async def call(path: str, **kwargs: object) -> tuple[int, dict[str, str], dict[str, object]]:
    async with AsyncClient(
        transport=ASGITransport(app=make_app(), raise_app_exceptions=False), base_url="http://t"
    ) as client:
        res = await client.get(path, **kwargs)  # type: ignore[arg-type]
    return res.status_code, dict(res.headers), res.json()


async def test_a_failed_request_is_traced_from_the_response_id_to_the_log_line(
    records: pytest.LogCaptureFixture,
) -> None:
    status, headers, body = await call("/boom/42?phone=0300123")
    assert status == 500 and body["code"] == "internal_error" and "secret detail" not in json.dumps(body)
    rid = headers["x-request-id"]
    assert body["request_id"] == rid
    error = next(r for r in records.records if r.name == "bazaarflow.error")
    assert error.request_id == rid and error.exc_info is not None  # type: ignore[attr-defined]
    access = next(r for r in records.records if r.name == "bazaarflow.access")
    assert (access.request_id, access.status, access.route) == (rid, 500, "/boom/{item}")  # type: ignore[attr-defined]


async def test_every_line_of_a_request_carries_its_id_and_a_caller_id_is_reused(
    records: pytest.LogCaptureFixture,
) -> None:
    status, headers, _ = await call("/fine", headers={"X-Request-ID": "trace-from-the-web-1234"})
    assert status == 200 and headers["x-request-id"] == "trace-from-the-web-1234" and "x-response-time" in headers
    inside = next(r for r in records.records if r.name == "bazaarflow.test")
    assert inside.request_id == "trace-from-the-web-1234"  # type: ignore[attr-defined]
    _, other, _ = await call("/fine", headers={"X-Request-ID": "bad id with spaces"})
    assert other["x-request-id"] != "bad id with spaces" and len(other["x-request-id"]) == 32


async def test_the_query_string_and_headers_are_never_logged(records: pytest.LogCaptureFixture) -> None:
    await call("/fine?q=Ali%20Raza&phone=03001234567", headers={"Authorization": "Bearer abc.def.ghi"})
    text = " ".join(
        r.getMessage() + json.dumps({k: str(v) for k, v in r.__dict__.items() if k in ("route", "method")})
        for r in records.records
        if r.name.startswith("bazaarflow")
    )
    assert "Ali" not in text and "03001234567" not in text and "abc.def.ghi" not in text


def test_the_json_format_is_one_parseable_object_with_the_request_id(monkeypatch: pytest.MonkeyPatch) -> None:
    record = logging.LogRecord("bazaarflow.access", logging.INFO, __file__, 1, "GET %s %s", ("/x", 200), None)
    record.status, record.duration_ms, record.tenant_id = 200, 1.5, "t-1"
    record.request_id = "rid-1"
    line = json.loads(JsonFormatter().format(record))
    assert (
        line["message"] == "GET /x 200"
        and line["request_id"] == "rid-1"
        and line["tenant_id"] == "t-1"
        and line["level"] == "info"
    )
    assert RequestIdFilter().filter(record) is True

    monkeypatch.setattr(settings, "LOG_FORMAT", "auto")
    monkeypatch.setattr(settings, "APP_ENV", "production")
    assert logging_config.use_json() is True
    monkeypatch.setattr(settings, "APP_ENV", "development")
    assert logging_config.use_json() is False
    monkeypatch.setattr(settings, "LOG_FORMAT", "json")
    assert logging_config.use_json() is True
