"""Schemas for the agent chat, the approvals center (F-021) and the agent activity log (F-022)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ActionStatusName = Literal["pending", "approved", "rejected", "executed", "failed", "expired"]
RunOutcome = Literal["ok", "failed", "step_limit", "paused", "spend_limit"]


class ChatRequest(BaseModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    session_id: Annotated[str, StringConstraints(min_length=1, max_length=60, pattern=r"^[A-Za-z0-9_-]+$")] | None = None


class ChatAction(BaseModel):
    """An approval the agent filed during this turn, shown as a card in the chat."""

    id: UUID
    tool: str
    summary: str
    status: ActionStatusName = "pending"


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    outcome: RunOutcome
    run_id: UUID
    actions: list[ChatAction]
    notice: str | None = None


class ApprovalOut(BaseModel):
    id: UUID
    agent: str
    tool: str
    summary: str
    details: list[str]  # the proposal in plain words (names, amounts), worked out from the live data
    payload: dict[str, Any]
    status: ActionStatusName
    requested_by: UUID | None
    requested_by_name: str | None
    decided_by: UUID | None
    decision_note: str | None
    created_at: datetime
    expires_at: datetime | None
    executed_at: datetime | None


class ApprovalReject(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=255)]


class ApprovalEdit(BaseModel):
    """Replace the proposed payload (for example a smaller quantity). It is re-validated like a new request."""

    payload: dict[str, Any]


class AgentRunOut(BaseModel):
    id: UUID
    user_id: UUID | None
    user_name: str | None
    agent: str
    session_id: str
    outcome: RunOutcome
    input_text: str
    output_text: str
    tokens_in: int
    tokens_out: int
    spend_usd: str  # the run's cost as dollars with 4 decimals
    duration_ms: int
    action_ids: list[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AgentRunDetail(AgentRunOut):
    trace: list[dict[str, Any]]


class AgentStatus(BaseModel):
    enabled: bool
    month_spend_usd: str
    month_cap_usd: str
    percent_used: int = Field(ge=0)
    runs_this_month: int


class AgentSwitch(BaseModel):
    enabled: bool
