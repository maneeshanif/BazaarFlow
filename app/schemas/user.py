"""User, auth and tenant-membership request/response schemas."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator

from app.core.passwords import is_common_password
from app.models.tenant import TenantRole

_Trimmed80 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]


class RegisterRequest(BaseModel):
    """PRD F-002: create an account and its first shop in one step."""

    full_name: _Trimmed80
    email: EmailStr  # unique; compared case-insensitively
    password: str = Field(min_length=8, max_length=128)
    shop_name: _Trimmed80
    phone: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")  # E.164, the form pre-fills +92
    city: Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)] | None = None
    accept_terms: bool

    @field_validator("password")
    @classmethod
    def _not_a_common_password(cls, value: str) -> str:
        if is_common_password(value):
            raise ValueError("is too common; choose something harder to guess")
        return value

    @field_validator("accept_terms")
    @classmethod
    def _terms_must_be_accepted(cls, value: bool) -> bool:
        if not value:
            raise ValueError("must be accepted to create an account")
        return value

    @field_validator("city")
    @classmethod
    def _blank_city_is_none(cls, value: str | None) -> str | None:
        return value or None


class LoginRequest(BaseModel):
    """PRD F-001. ``tenant_id`` is only needed when the user belongs to more than one tenant."""

    email: EmailStr  # RFC format, at most 254 characters; compared case-insensitively
    password: str = Field(min_length=8, max_length=128)
    tenant_id: UUID | None = None


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


class SwitchTenantRequest(BaseModel):
    tenant_id: UUID


class TenantMembershipOut(BaseModel):
    tenant_id: UUID
    tenant_name: str
    role: TenantRole


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    tenant_id: UUID
    role: TenantRole


class UserOut(BaseModel):
    id: UUID
    email: str
    name: str | None
    is_active: bool
    is_platform_admin: bool
    model_config = {"from_attributes": True}


class MeOut(BaseModel):
    user: UserOut
    tenant_id: UUID
    role: TenantRole
    memberships: list[TenantMembershipOut]
