"""Team and roles schemas (PRD F-019). Owners add people and set their role; there is always exactly the owner(s) above."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.core.passwords import is_common_password

AssignableRole = Literal["manager", "staff"]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]


class TeamMemberCreate(BaseModel):
    """Add a person to the shop. A new person needs an initial password to be given to them; someone who already has
    an account (for example in another shop) keeps theirs and ``password`` is ignored."""

    name: Name
    email: EmailStr
    role: AssignableRole
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _not_common(cls, value: str | None) -> str | None:
        if value is not None and is_common_password(value):
            raise ValueError("is too common; choose something harder to guess")
        return value


class TeamMemberUpdate(BaseModel):
    """Only the role can change; unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")

    role: AssignableRole


class TeamMemberOut(BaseModel):
    id: UUID  # the membership id: what the other team endpoints take
    user_id: UUID
    name: str | None
    email: str
    role: str
    is_active: bool
    joined_at: datetime
    is_you: bool
    new_account: bool = False  # true only in the response to adding someone who had no account yet
