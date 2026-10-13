"""Replies to comments on the shop's Facebook posts (PRD W-004 step 4).

A comment is stored once (the Facebook comment id is unique per shop). The marketing writer proposes a reply; the shop's
approval mode decides whether it posts at once (``auto``) or waits for a person (``manual``). Posting is done by the
scheduler through the Facebook adapter, with the row id as the idempotency key.

``proposed -> approved -> posted``, or ``skipped`` (nothing worth answering, or a person skipped it) or ``failed``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, TenantMixin

REPLY_STATUSES = ("proposed", "approved", "posted", "skipped", "failed")


class CommentReply(BaseModelMixin, TenantMixin, Base):
    __tablename__ = "comment_replies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "fb_comment_id", name="uq_comment_replies_tenant_comment"),
        CheckConstraint("status in ('proposed', 'approved', 'posted', 'skipped', 'failed')", name="ck_comment_replies_status"),
        Index("ix_comment_replies_tenant_status", "tenant_id", "status"),
    )
    post_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("marketing_posts.id", ondelete="CASCADE"), nullable=False)
    fb_post_id: Mapped[str] = mapped_column(String(255), nullable=False)
    fb_comment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str | None] = mapped_column(String(120), nullable=True)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    reply_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="proposed", server_default=text("'proposed'"))
    action_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fb_reply_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
