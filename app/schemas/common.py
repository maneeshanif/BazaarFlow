"""Shared Pydantic schemas � pagination, error envelopes, health."""
from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response envelope."""
    items: List[T]
    total: int
    page: int = Field(ge=1, default=1)
    page_size: int = Field(ge=1, le=200, default=20)

    @property
    def pages(self) -> int:
        if self.page_size == 0:
            return 0
        import math
        return math.ceil(self.total / self.page_size)


class ErrorDetail(BaseModel):
    """Standard error response body."""
    code: str
    message: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "2.0.0"
    environment: str = "development"
