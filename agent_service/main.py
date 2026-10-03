"""Agent service skeleton (build-plan task 28, ADR 0003).

Runs separately from the API and has no database access: it will reach business data only by calling the API with
the caller's scoped token. For now it starts, reports health and validates run requests; running agents here
arrives with the phase 1 tool-call path (``POST /v1/run`` answers 501 until then).
"""

from __future__ import annotations

import hmac
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from agent_service.guards import assert_no_database_environment
from agent_service.settings import AgentServiceSettings


class RunRequest(BaseModel):
    agent: Literal["sales", "finance", "inventory", "marketing"]
    message: str = Field(min_length=1, max_length=4000)


def create_app(settings: AgentServiceSettings | None = None) -> FastAPI:
    cfg = settings or AgentServiceSettings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        assert_no_database_environment()  # fail at start, not later
        yield

    app = FastAPI(title="BazaarFlow Agent Service", version="0.1.0", lifespan=lifespan)

    def require_token(x_agent_service_token: Annotated[str | None, Header()] = None) -> None:
        expected = cfg.AGENT_SERVICE_TOKEN
        if not expected or not x_agent_service_token or not hmac.compare_digest(x_agent_service_token, expected):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid service token")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "agent-service"}

    @app.post("/v1/run", dependencies=[Depends(require_token)])
    async def run(_body: RunRequest) -> dict[str, str]:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "Agents do not run here yet: they will reach data through the API once the tool-call path exists.",
        )

    return app
