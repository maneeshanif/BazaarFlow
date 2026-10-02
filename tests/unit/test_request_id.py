"""Every response carries X-Request-ID; a well-formed incoming id is reused, a malformed one is replaced (PRD §13.1)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.request_context import new_request_id
from app.main import app


def test_response_has_a_request_id() -> None:
    res = TestClient(app).get("/health")
    assert len(res.headers["X-Request-ID"]) >= 8


def test_a_valid_incoming_id_is_echoed() -> None:
    res = TestClient(app).get("/health", headers={"X-Request-ID": "trace-1234-abcd"})
    assert res.headers["X-Request-ID"] == "trace-1234-abcd"


def test_a_malformed_incoming_id_is_replaced() -> None:
    for bad in ("short", "has spaces in it!", "x" * 200, "<script>alert(1)</script>"):
        assert new_request_id(bad) != bad
    assert new_request_id(None) and new_request_id("") != ""
