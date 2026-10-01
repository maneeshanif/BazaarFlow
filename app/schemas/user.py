"""User, auth and tenant-membership request/response schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.tenant import TenantRole


class RegisterRequest(BaseModel):
    """PRD F-002: create an account and its first shop in one step."""

    full_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    shop_name: str = Field(min_length=2, max_length=80)
    phone: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    city: str | None = Field(default=None, max_length=60)
    accept_terms: bool


class LoginRequest(BaseModel):
    """PRD F-001. ``tenant_id`` is only needed when the user belongs to more than one tenant."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
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
