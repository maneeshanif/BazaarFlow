"""Marketing schedule and activity schemas (PRD F-015, F-016, W-004)."""

from __future__ import annotations

from datetime import datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ScheduleGoal = Literal["announce_offer", "festival_greeting", "general"]
Tone = Literal["friendly", "professional", "festive"]
Language = Literal["english", "roman_urdu"]
ApprovalMode = Literal["manual", "auto"]
ActivityStatus = Literal["pending_approval", "approved", "queued", "published", "failed", "cancelled"]


class ScheduleIn(BaseModel):
    """F-015. The window is in the shop's local time; ``posts_per_day`` is spread evenly across it."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    goal: ScheduleGoal = "general"
    notes: str | None = Field(default=None, max_length=300)
    tone: Tone = "friendly"
    language: Language = "english"
    posts_per_day: int = Field(default=1, ge=1, le=5)
    window_start: time = time(10, 0)
    window_end: time = time(20, 0)
    approval_mode: ApprovalMode = "manual"

    @field_validator("notes")
    @classmethod
    def _notes(cls, value: str | None) -> str | None:
        return (value or "").strip() or None

    @field_validator("window_start", "window_end")
    @classmethod
    def _no_seconds(cls, value: time) -> time:
        return value.replace(second=0, microsecond=0)

    @model_validator(mode="after")
    def _window_is_forward(self) -> ScheduleIn:
        if self.window_start >= self.window_end:
            raise ValueError("The posting window must end after it starts")
        return self


class ScheduleOut(ScheduleIn):
    configured: bool  # false until the owner saves it once
    facebook_connected: bool  # a schedule can only be switched on when posts have somewhere to go
    next_post_at: datetime | None  # the earliest queued post


class ActivityOut(BaseModel):
    id: UUID
    title: str
    message: str
    status: ActivityStatus
    source: Literal["manual", "schedule"]
    scheduled_for: datetime | None
    published_at: datetime | None
    attempts: int
    last_error: str | None
    created_at: datetime


class ScheduleRequest(BaseModel):
    """Put an approved post in the publishing queue for a given moment."""

    scheduled_for: datetime
