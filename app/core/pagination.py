"""List conventions (PRD §13.1): ``limit``, ``cursor``, ``sort``, ``q``.

The cursor is opaque to clients (a base64 offset). Sorting always ends with ``id`` so pages are stable. At demo scale
(a catalog under 10k rows per tenant) an offset cursor is simpler and safe; swap the encoding here if that changes.
"""

from __future__ import annotations

import base64
import binascii
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.problems import DomainError

T = TypeVar("T")
MAX_LIMIT = 100
DEFAULT_LIMIT = 50


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(ge=0)
    next_cursor: str | None = None


def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(f"o:{offset}".encode()).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        kind, _, number = raw.partition(":")
        offset = int(number)
    except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise DomainError("The cursor is not valid", code="invalid_cursor", status_code=400) from exc
    if kind != "o" or offset < 0:
        raise DomainError("The cursor is not valid", code="invalid_cursor", status_code=400)
    return offset


def next_cursor(offset: int, limit: int, total: int) -> str | None:
    return encode_cursor(offset + limit) if offset + limit < total else None
