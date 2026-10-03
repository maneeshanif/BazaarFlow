"""Request id, access log and last-resort error response (build-plan task 57).

A pure ASGI middleware, so the request id is still set when an unhandled error is turned into a response: the caller
gets a problem body carrying the same ``request_id`` as the ``X-Request-ID`` header and every log line of the request.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.request_context import new_request_id, request_id_var

logger = logging.getLogger("bazaarflow.access")
error_logger = logging.getLogger("bazaarflow.error")


def _template(scope: Scope) -> str:
    """The path with the ids replaced by their names (``/orders/{order_id}``), so ids never fan out the log."""
    path: str = scope["path"]
    for name, value in (scope.get("path_params") or {}).items():
        path = path.replace(f"/{value}", f"/{{{name}}}", 1)
    return path


class RequestLoggerMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        request_id = new_request_id(headers.get("x-request-id"))
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        status = 500
        started = False

        async def send_with_headers(message: Message) -> None:
            nonlocal status, started
            if message["type"] == "http.response.start":
                started = True
                status = message["status"]
                elapsed = f"{(time.perf_counter() - start) * 1000:.2f}ms"
                extra = [(b"x-request-id", request_id.encode()), (b"x-response-time", elapsed.encode())]
                message = {**message, "headers": [*message.get("headers", []), *extra]}
            await send(message)

        try:
            try:
                await self.app(scope, receive, send_with_headers)
            except Exception:  # noqa: BLE001 - the last line of defence: never leak a stack trace to the caller
                error_logger.exception("unhandled error while serving %s %s", scope["method"], scope["path"])
                if not started:
                    body = json.dumps(
                        {
                            "type": "about:blank",
                            "title": "Internal Server Error",
                            "status": 500,
                            "detail": "Something went wrong on our side. Quote this request id if you ask for help.",
                            "code": "internal_error",
                            "request_id": request_id,
                        }
                    ).encode()
                    await send_with_headers(
                        {"type": "http.response.start", "status": 500, "headers": [(b"content-type", b"application/problem+json"), (b"content-length", str(len(body)).encode())]}
                    )
                    await send({"type": "http.response.body", "body": body})
                status = 500
        finally:
            state: dict[str, Any] = scope.get("state") or {}
            route_template = _template(scope)
            logger.info(
                "%s %s %s",
                scope["method"],
                route_template,
                status,
                extra={
                    "method": scope["method"],
                    "route": route_template,  # the template, never the filled-in ids or the query string
                    "status": status,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                    "tenant_id": state.get("tenant_id"),
                    "user_id": state.get("user_id"),
                },
            )
            request_id_var.reset(token)
