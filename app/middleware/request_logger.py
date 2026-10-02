"""Request logging middleware � logs method, path, status code, and latency."""
from __future__ import annotations

import logging
import time
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.request_context import new_request_id, request_id_var

logger = logging.getLogger("bazaarflow.access")


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """Logs every inbound HTTP request with timing information."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = new_request_id(request.headers.get("X-Request-ID"))
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        # Try to extract vendor_id from path or query params
        vendor_id = request.path_params.get("vendor_id") or request.query_params.get("vendor_id", "-")

        logger.info(
            "%s %s %s %.2fms vendor=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            vendor_id,
            request_id,
        )
        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
        response.headers["X-Request-ID"] = request_id
        return response
