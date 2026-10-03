"""Per-IP sign-up throttle (owner decision, Phase 1: rate limit only, no e-mail verification).

An in-memory sliding window per client address. That is enough for the demo (one API process); if the API is scaled
to several instances, each keeps its own window, so the effective limit is per instance. ``SIGNUP_MAX_PER_HOUR=0``
turns it off (tests do).
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Request

from app.core.problems import DomainError
from app.core.settings import settings

_WINDOW_SECONDS = 3600
_attempts: dict[str, list[float]] = defaultdict(list)
_demo_attempts: dict[str, list[float]] = defaultdict(list)


def reset_signup_throttle() -> None:
    _attempts.clear()
    _demo_attempts.clear()


def _client_address(request: Request) -> str:
    """The visitor's address. The web app forwards it in X-Forwarded-For (the API only ever sees the web server).

    A caller that talks to the API directly could invent that header to dodge the limit; for a demo throttle that is an
    accepted trade-off (documented in the progress log), not a security boundary.
    """
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


async def signup_throttle(request: Request) -> None:
    """FastAPI dependency for the registration route: refuse the Nth sign-up from one address within an hour."""
    limit = settings.SIGNUP_MAX_PER_HOUR
    if limit <= 0:
        return
    ip = _client_address(request)
    now = time.time()
    recent = [t for t in _attempts[ip] if now - t < _WINDOW_SECONDS]
    if len(recent) >= limit:
        _attempts[ip] = recent
        wait = int(_WINDOW_SECONDS - (now - recent[0])) + 1
        raise DomainError(
            "Too many sign-ups from this connection. Try again later or sign in if you already have an account.",
            code="signup_rate_limited",
            status_code=429,
            extra={"retry_after_seconds": wait},
        )
    recent.append(now)
    _attempts[ip] = recent


async def demo_throttle(request: Request) -> None:
    """FastAPI dependency for starting a demo shop: at most DEMO_MAX_PER_HOUR per address (0 turns it off)."""
    limit = settings.DEMO_MAX_PER_HOUR
    if limit <= 0:
        return
    ip = _client_address(request)
    now = time.time()
    recent = [t for t in _demo_attempts[ip] if now - t < _WINDOW_SECONDS]
    if len(recent) >= limit:
        _demo_attempts[ip] = recent
        raise DomainError(
            "You have started several demos already. Create your own free shop to keep going, or try again in an hour.",
            code="demo_rate_limited",
            status_code=429,
        )
    recent.append(now)
    _demo_attempts[ip] = recent
