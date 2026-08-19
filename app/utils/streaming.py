"""Server-Sent Events (SSE) streaming helpers for chat endpoints."""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator

from fastapi.responses import StreamingResponse


async def token_stream(
    tokens: AsyncGenerator[str, None],
    event: str = "message",
) -> AsyncGenerator[str, None]:
    """Wrap an async token generator into SSE format.

    Args:
        tokens: Async generator yielding text chunks.
        event:  SSE event name (default ``message``).

    Yields:
        SSE-formatted strings ready to stream to the client.
    """
    async for chunk in tokens:
        data = json.dumps({"delta": chunk})
        yield f"event: {event}\ndata: {data}\n\n"
    yield "event: done\ndata: {}\n\n"


def make_sse_response(tokens: AsyncGenerator[str, None]) -> StreamingResponse:
    """Return a ``StreamingResponse`` pre-configured for SSE."""
    return StreamingResponse(
        token_stream(tokens),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable Nginx buffering
        },
    )
