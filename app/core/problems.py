"""RFC 7807 problem details for every error the API returns (PRD §13.1, code-standards "Error Handling").

Body: ``type``, ``title``, ``status``, ``detail``, ``request_id`` and, for validation failures, ``errors`` (one entry
per field). ``detail`` stays a plain string so existing clients that read it keep working. Domain rule violations raise
``DomainError`` (422 unless stated), never leaking stack traces or SQL.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.request_context import current_request_id

PROBLEM_CONTENT_TYPE = "application/problem+json"

_TITLES = {
    400: "Bad request",
    401: "Not authenticated",
    403: "Not allowed",
    404: "Not found",
    405: "Method not allowed",
    409: "Conflict",
    422: "Validation failed",
    429: "Too many requests",
}


class DomainError(Exception):
    """A business rule was violated. ``code`` is a stable machine-readable slug the UI can switch on."""

    status_code = 422

    def __init__(self, detail: str, *, code: str = "rule_violation", status_code: int | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code
        if status_code is not None:
            self.status_code = status_code


class NotFound(DomainError):
    status_code = 404

    def __init__(self, what: str = "Record") -> None:
        super().__init__(f"{what} not found", code="not_found")


class Conflict(DomainError):
    status_code = 409

    def __init__(self, detail: str, *, code: str = "conflict") -> None:
        super().__init__(detail, code=code)


def problem(
    status: int, detail: str, *, code: str | None = None, errors: list[dict[str, str]] | None = None
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"about:blank#{code}" if code else "about:blank",
        "title": _TITLES.get(status, "Error"),
        "status": status,
        "detail": detail,
        "request_id": current_request_id(),
    }
    if code:
        body["code"] = code
    if errors:
        body["errors"] = errors
    return JSONResponse(status_code=status, content=body, media_type=PROBLEM_CONTENT_TYPE)


def _field(loc: tuple[Any, ...]) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path")]
    return ".".join(parts) or "request"


async def _http_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    response = problem(exc.status_code, detail)
    for key, value in (getattr(exc, "headers", None) or {}).items():
        response.headers[key] = value
    return response


async def _validation_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = [{"field": _field(tuple(e["loc"])), "message": str(e["msg"])} for e in exc.errors()]
    summary = "; ".join(f"{e['field']}: {e['message']}" for e in errors[:3]) or "Invalid request"
    return problem(422, summary, code="validation_failed", errors=errors)


async def _domain_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    return problem(exc.status_code, exc.detail, code=exc.code)


def install_problem_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(HTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(DomainError, _domain_error)
