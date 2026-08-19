"""Simple in-memory rate limiter middleware.

Uses a sliding-window counter per (IP, path prefix).
For production, swap the in-memory store with Redis.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# {key: [(timestamp), ...]}
_windows: dict[str, list[float]] = defaultdict(list)

# Default limits (requests / window_seconds)
_LIMIT = 120
_WINDOW = 60  # seconds


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Per-IP sliding-window rate limiter."""

    def __init__(self, app, limit: int = _LIMIT, window: int = _WINDOW) -> None:
        super().__init__(app)
        self.limit = limit
        self.window = window

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Skip static/health paths
        if request.url.path in ("/health", "/docs", "/openapi.json"):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        key = f"{ip}:{request.url.path.split('/')[1]}"  # bucket by top-level path
        now = time.time()

        # Prune old timestamps
        _windows[key] = [t for t in _windows[key] if now - t < self.window]

        if len(_windows[key]) >= self.limit:
            return JSONResponse(
                status_code=429,
                content={"code": "rate_limit_exceeded", "message": "Too many requests"},
            )

        _windows[key].append(now)
        return await call_next(request)
