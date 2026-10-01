"""Soft-delete filter shared by every CRUD module (PRD §12.2): one definition of "a live row"."""

from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement


def live(model: Any) -> ColumnElement[bool]:
    """``WHERE`` clause that keeps only rows that are not soft-deleted."""
    clause: ColumnElement[bool] = model.deleted_at.is_(None)
    return clause
