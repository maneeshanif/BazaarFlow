"""Per-request correlation id (PRD §13.1): set by the middleware, read by logging and the audit helper."""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

_VALID = re.compile(r"^[A-Za-z0-9._\-]{8,64}$")


def new_request_id(incoming: str | None) -> str:
    """Reuse a well-formed id from the caller (so traces join up) or mint a fresh one."""
    return incoming if incoming and _VALID.match(incoming) else uuid.uuid4().hex


def current_request_id() -> str | None:
    return request_id_var.get()
