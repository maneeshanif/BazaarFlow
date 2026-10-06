"""Task 85: the Pexels image search against recorded responses (happy path, timeout, error, duplicate delivery)."""

from __future__ import annotations

import httpx
import pytest

from app.integrations.http import ProviderError
from app.integrations.pexels import CACHE_SECONDS, PexelsClient
from tests.unit.provider_support import Script, Sleeps, json_response


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def pexels(script: Script, clock: Clock | None = None, key: str = "pexels-test-key") -> PexelsClient:
    return PexelsClient(key, transport=script.transport, sleep=Sleeps(), clock=clock or Clock())


async def test_a_search_returns_images_with_a_large_url_a_thumbnail_and_the_credit() -> None:
    script = Script(json_response(200, "pexels_search.json"))
    images = await pexels(script).search("blue shirt", per_page=2)
    assert [i.id for i in images] == [2379004, 1040880]
    first = images[0]
    assert first.url.endswith("h=650&w=940") and first.thumbnail.endswith("h=350")
    assert first.photographer == "Italo Melo" and first.credit_url.startswith("https://www.pexels.com/photo/")
    assert images[1].thumbnail.endswith("h=350") and images[1].alt == ""
    request = script.requests[0]
    assert request.url.path == "/v1/search" and request.url.params["query"] == "blue shirt" and request.url.params["per_page"] == "2"
    assert request.headers["authorization"] == "pexels-test-key"  # the key goes in the header, without "Bearer"


async def test_the_same_search_twice_in_a_row_calls_the_provider_once() -> None:
    script = Script(json_response(200, "pexels_search.json"))
    client = pexels(script)
    first = await client.search("Blue  Shirt", per_page=2)
    second = await client.search("blue shirt", per_page=2)
    assert first == second and len(script.requests) == 1


async def test_after_the_cache_window_the_search_is_made_again() -> None:
    script = Script(json_response(200, "pexels_search.json"))
    clock = Clock()
    client = pexels(script, clock)
    await client.search("shirt")
    clock.now += CACHE_SECONDS + 1
    await client.search("shirt")
    assert len(script.requests) == 2


async def test_a_different_page_size_is_a_different_search() -> None:
    script = Script(json_response(200, "pexels_search.json"))
    client = pexels(script)
    await client.search("shirt", per_page=2)
    await client.search("shirt", per_page=3)
    assert len(script.requests) == 2


async def test_the_page_size_is_kept_within_the_providers_limit() -> None:
    script = Script(json_response(200, "pexels_search.json"))
    await pexels(script).search("shirt", per_page=500)
    assert script.requests[0].url.params["per_page"] == "20"


async def test_a_timeout_is_retried_then_raised() -> None:
    script = Script(httpx.ReadTimeout("slow"))
    with pytest.raises(ProviderError) as caught:
        await pexels(script).search("shirt")
    assert caught.value.kind == "timeout" and len(script.requests) == 3


async def test_a_429_waits_and_a_later_success_is_returned() -> None:
    script = Script(httpx.Response(429, json={"error": "Too many requests"}, headers={"Retry-After": "1"}), json_response(200, "pexels_search.json"))
    assert len(await pexels(script).search("shirt")) == 2 and len(script.requests) == 2


async def test_a_rejected_key_is_an_auth_error_and_a_failure_is_not_cached() -> None:
    script = Script(httpx.Response(401, json={"error": "Unauthorized"}), json_response(200, "pexels_search.json"))
    client = pexels(script)
    with pytest.raises(ProviderError) as caught:
        await client.search("shirt")
    assert caught.value.needs_reconnect and "pexels-test-key" not in str(caught.value)
    assert len(await client.search("shirt")) == 2  # the next try goes to the provider again


async def test_a_missing_key_is_reported_without_calling_the_provider() -> None:
    script = Script(json_response(200, "pexels_search.json"))
    with pytest.raises(ProviderError) as caught:
        await pexels(script, key="").search("shirt")
    assert caught.value.kind == "auth" and script.requests == []


async def test_an_empty_query_returns_nothing_without_a_call() -> None:
    script = Script(json_response(200, "pexels_search.json"))
    assert await pexels(script).search("   ") == [] and script.requests == []
