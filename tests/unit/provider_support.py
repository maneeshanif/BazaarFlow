"""Shared helpers for the provider adapter tests: recorded fixtures and a scripted transport that never touches the network."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "providers"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8").strip()


def fixture_json(name: str) -> Any:
    return json.loads(fixture_text(name))


class Script:
    """A transport that answers from a list (one entry per call) and records every request it saw.

    An entry is an ``httpx.Response``, an exception to raise, or a callable taking the request.
    """

    def __init__(self, *steps: httpx.Response | Exception | Callable[[httpx.Request], httpx.Response]) -> None:
        self.steps = list(steps)
        self.requests: list[httpx.Request] = []
        self.transport = httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        index = min(len(self.requests) - 1, len(self.steps) - 1)
        step = self.steps[index]
        if isinstance(step, Exception):
            raise step
        if callable(step):
            return step(request)
        return step


def json_response(status: int, name: str, headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(status, json=fixture_json(name), headers=headers)


class Sleeps:
    """A sleep replacement that records the delays instead of waiting."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)
