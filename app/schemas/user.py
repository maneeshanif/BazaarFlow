"""User request/response schemas."""
from __future__ import annotations
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None
    role: UserRole = UserRole.vendor

class UserOut(BaseModel):
    id: str
    email: str
    name: str | None
    role: UserRole
    is_active: bool
    model_config = {"from_attributes": True}

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
