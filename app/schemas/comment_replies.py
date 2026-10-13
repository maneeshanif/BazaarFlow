"""Facebook comment reply schemas (PRD W-004 step 4). Read-only apart from skipping a proposed reply."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ReplyStatus = Literal["proposed", "approved", "posted", "skipped", "failed"]


class CommentReplyOut(BaseModel):
    id: UUID
    post_id: UUID
    post_title: str | None
    author: str | None
    comment_text: str
    reply_text: str | None
    status: ReplyStatus
    action_id: UUID | None
    last_error: str | None
    created_at: datetime
    posted_at: datetime | None
