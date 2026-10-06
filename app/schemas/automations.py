"""Automation recipes schemas (PRD F-024, W-008)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

RunStatus = Literal["queued", "running", "succeeded", "failed"]


class LastRun(BaseModel):
    status: RunStatus
    summary: str | None
    error: str | None
    finished_at: datetime | None


class AutomationOut(BaseModel):
    key: str
    label: str
    description: str
    trigger: str
    enabled: bool
    requires: list[str]  # integrations that must be connected before it can be switched on
    requirements_met: bool
    last_run_at: datetime | None
    consecutive_failures: int
    needs_attention: bool  # three failures in a row: the owner should look
    last_run: LastRun | None


class ToggleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


class RunOut(BaseModel):
    id: UUID
    automation_key: str
    label: str
    status: RunStatus
    trigger_source: Literal["schedule", "manual"]
    summary: str | None
    error: str | None
    started_at: datetime
    finished_at: datetime | None
