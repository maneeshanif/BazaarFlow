"""Marketing studio schemas (PRD F-014): AI drafts, edited by a person, sent for approval. Nothing here publishes."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Goal = Literal["promote_product", "announce_offer", "festival_greeting", "general"]
Tone = Literal["friendly", "professional", "festive"]
Language = Literal["english", "roman_urdu"]
PostStatus = Literal["draft", "pending_approval", "approved", "archived"]

_TAG = re.compile(r"^#[A-Za-z0-9_]{2,40}$")


def clean_hashtags(raw: str | None) -> str:
    """One space between tags, each starting with #, at most 10."""
    tags = [t if t.startswith("#") else f"#{t}" for t in (raw or "").split()]
    return " ".join(tags[:10])


class DraftRequest(BaseModel):
    goal: Goal
    tone: Tone = "friendly"
    language: Language = "english"
    product_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=300)

    @field_validator("notes")
    @classmethod
    def _notes(cls, value: str | None) -> str | None:
        return (value or "").strip() or None

    @model_validator(mode="after")
    def _needs_product(self) -> DraftRequest:
        if self.goal == "promote_product" and self.product_id is None:
            raise ValueError("Choose the product to promote")
        return self


class PostUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=1000)
    hashtags: str = Field(default="", max_length=300)

    @field_validator("title", "message")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This cannot be blank")
        return value

    @field_validator("hashtags")
    @classmethod
    def _tags(cls, value: str) -> str:
        cleaned = clean_hashtags(value)
        if any(not _TAG.match(t) for t in cleaned.split()):
            raise ValueError("Hashtags use letters, numbers and underscores only")
        return cleaned


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    message: str
    hashtags: str
    status: PostStatus
    created_at: datetime
    updated_at: datetime
