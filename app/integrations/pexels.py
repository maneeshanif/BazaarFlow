"""Pexels stock image search (PRD I-006, build-plan task 85): outbound only, one REST call.

``GET https://api.pexels.com/v1/search?query=...&per_page=...`` with the API key in the ``Authorization`` header (no
``Bearer``); the answer lists ``photos`` with ``src`` sizes, the photographer and the Pexels page to credit. The call goes
through ``ProviderClient`` (timeout, retries, typed errors, a 429 waits for ``Retry-After``). Asking for the same thing
twice within the cache window (a retried request, a double click, the scheduler and the studio at once) returns the first
answer without a second call, which is how a duplicate delivery is handled for an outbound-only provider.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from app.integrations.http import ProviderClient, ProviderError, Sleep

BASE_URL = "https://api.pexels.com"
CACHE_SECONDS = 300.0
MAX_PER_PAGE = 20


@dataclass(frozen=True)
class StockImage:
    id: int
    url: str  # a large version, suitable for a post
    thumbnail: str
    photographer: str
    credit_url: str  # the Pexels page: show it next to the picture
    alt: str


class PexelsClient:
    def __init__(
        self,
        api_key: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep | None = None,
        retries: int = 3,
        timeout: float = 10.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._key = api_key
        self._http = ProviderClient("pexels", BASE_URL, transport=transport, sleep=sleep, retries=retries, timeout=timeout)
        self._clock = clock
        self._cache: dict[tuple[str, int], tuple[float, list[StockImage]]] = {}

    async def aclose(self) -> None:
        await self._http.aclose()

    async def search(self, query: str, *, per_page: int = 5) -> list[StockImage]:
        if not self._key:
            raise ProviderError("pexels", "auth", "PEXELS_API_KEY is not set")
        clean = " ".join(query.split())
        if not clean:
            return []
        per_page = max(1, min(per_page, MAX_PER_PAGE))
        key = (clean.lower(), per_page)
        now = self._clock()
        cached = self._cache.get(key)
        if cached is not None and now - cached[0] < CACHE_SECONDS:
            return list(cached[1])
        response = await self._http.request(
            "GET", "/v1/search", params={"query": clean, "per_page": str(per_page)}, headers={"Authorization": self._key}
        )
        images = [
            StockImage(
                id=int(photo["id"]),
                url=str(photo["src"].get("large") or photo["src"].get("original")),
                thumbnail=str(photo["src"].get("medium") or photo["src"].get("small") or ""),
                photographer=str(photo.get("photographer", "")),
                credit_url=str(photo.get("url", "")),
                alt=str(photo.get("alt", "")),
            )
            for photo in response.json().get("photos", [])
            if isinstance(photo.get("src"), dict) and photo.get("id") is not None
        ]
        self._cache[key] = (now, images)
        return list(images)
