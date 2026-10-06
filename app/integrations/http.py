"""One way to call an outside provider (PRD §3.7 constraint 11, tasks 59-62).

Every adapter (Twilio, Facebook, Pexels) calls its provider through ``ProviderClient``, so each one gets the same
guarantees: a hard timeout, a few retries with growing delays for the failures that can pass (a timeout, a 5xx, a 429
that says when to come back), no retry for the ones that cannot (a refused credential, a bad request), and a small set
of error kinds the rest of the code can act on. Secrets never appear in an error message.
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Literal

import httpx

logger = logging.getLogger("bazaarflow.providers")

ErrorKind = Literal["timeout", "rate_limited", "server", "auth", "client", "network"]

AUTH_CODES = frozenset({"190", "102", "10", "200"})
RATE_CODES = frozenset({"4", "17", "32", "613"})
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_RETRIES = 3
MAX_RETRY_AFTER_SECONDS = 30.0


class ProviderError(Exception):
    """A provider call failed. ``kind`` says what to do next; ``retryable`` is what the client already tried."""

    def __init__(self, provider: str, kind: ErrorKind, message: str, *, status: int | None = None, code: str | None = None) -> None:
        super().__init__(f"{provider}: {message}")
        self.provider = provider
        self.kind = kind
        self.message = message
        self.status = status
        self.code = code

    @property
    def needs_reconnect(self) -> bool:
        """The credential was refused: only the owner can fix it (a new token), so the integration goes to ``error``."""
        return self.kind == "auth"


Sleep = Callable[[float], Awaitable[None]]


class ProviderClient:
    """A thin retrying wrapper over ``httpx.AsyncClient``. Pass ``transport`` in tests (``httpx.MockTransport``)."""

    def __init__(
        self,
        provider: str,
        base_url: str,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        retries: int = DEFAULT_RETRIES,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.provider = provider
        self.retries = max(1, retries)
        self._sleep: Sleep = sleep or asyncio.sleep
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout, transport=transport, headers=dict(headers or {}))

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> ProviderClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    @staticmethod
    def _retry_after(response: httpx.Response) -> float | None:
        raw = response.headers.get("retry-after")
        if raw is None:
            return None
        try:
            return min(max(float(raw), 0.0), MAX_RETRY_AFTER_SECONDS)
        except ValueError:
            return None

    def _delay(self, attempt: int, response: httpx.Response | None) -> float:
        if response is not None and (after := self._retry_after(response)) is not None:
            return after
        return float(min(0.5 * (2**attempt), 8.0) * (0.75 + random.random() / 2))  # noqa: S311 (jitter, not security)

    def _classify(self, response: httpx.Response) -> ProviderError:
        status = response.status_code
        message = f"HTTP {status}"
        code: str | None = None
        try:
            body = response.json()
        except ValueError:
            body = None
        if isinstance(body, dict):
            error = body.get("error")
            if isinstance(error, dict):  # Facebook: {"error": {"message", "code"}}
                code = str(error.get("code")) if error.get("code") is not None else None
                message = f"HTTP {status}: {error.get('message', 'error')}"
            elif body.get("message"):  # Twilio: {"message", "code"}
                code = str(body.get("code")) if body.get("code") is not None else None
                message = f"HTTP {status}: {body['message']}"
        # Facebook reports an expired or revoked token as HTTP 400 with code 190 (102 and 10/200 are session and permission
        # failures) and throttling as codes 4, 17, 32 and 613: only the first group needs the owner, the second passes.
        if status in (401, 403) or code in AUTH_CODES:
            return ProviderError(self.provider, "auth", message, status=status, code=code)
        if status == 429 or code in RATE_CODES:
            return ProviderError(self.provider, "rate_limited", message, status=status, code=code)
        if status >= 500:
            return ProviderError(self.provider, "server", message, status=status, code=code)
        return ProviderError(self.provider, "client", message, status=status, code=code)

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Send the request. Returns a 2xx response, or raises ``ProviderError`` after the retries run out."""
        last: ProviderError | None = None
        for attempt in range(self.retries):
            response: httpx.Response | None = None
            try:
                response = await self._client.request(method, url, **kwargs)
            except httpx.TimeoutException:
                last = ProviderError(self.provider, "timeout", "the provider did not answer in time")
            except httpx.HTTPError:
                last = ProviderError(self.provider, "network", "the provider could not be reached")
            else:
                if response.is_success:
                    return response
                last = self._classify(response)
                if last.kind in {"auth", "client"}:
                    break  # retrying cannot help
            if attempt < self.retries - 1:
                await self._sleep(self._delay(attempt, response))
        assert last is not None
        logger.warning("provider call failed", extra={"provider": self.provider, "kind": last.kind, "status": last.status})
        raise last
