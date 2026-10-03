"""Search helpers shared by the list endpoints."""

from __future__ import annotations


def escape_like(text: str) -> str:
    """Make user text safe inside ILIKE: a typed % or _ is a literal character, not a wildcard (escape char is a backslash)."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
