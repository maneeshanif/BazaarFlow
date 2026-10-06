"""Marketing insights (PRD F-017): how the shop's posts did. Owners and managers."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.dashboard import CountFigure, DashboardRange


class InsightDay(BaseModel):
    day: date
    published: int


class TopPost(BaseModel):
    id: UUID
    title: str
    published_at: datetime
    comments: int | None  # None when Facebook could not be asked


class MarketingInsights(BaseModel):
    range: DashboardRange
    published: CountFigure  # posts that went out in the range, against the range before
    failed: int
    queued: int
    success_percent: int | None  # published / (published + failed); None when neither happened
    from_schedule: int  # of the published posts, how many the schedule wrote
    trend: list[InsightDay]  # oldest first, 7 days (30 for the 30d range)
    top_posts: list[TopPost]  # the most recent published posts with their comment counts
    engagement: Literal["available", "unavailable", "not_connected"]
    engagement_note: str | None
    is_empty: bool
    generated_at: datetime
