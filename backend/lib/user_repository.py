"""Simple JSON-backed repository for application users.

This is intentionally minimal and exists primarily to provide a stable
"dev" user identity so the app can run end-to-end in development
without a full auth stack.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .json_store import JsonStore


_DB_PATH = Path(__file__).resolve().parent.parent / "db" / "users.json"
_USERS_STORE = JsonStore(_DB_PATH, default_factory=list)


@dataclass
class UserRecord:
    user_id: str
    name: str
    role: str = "user"
    email: Optional[str] = None
    is_dev_default: bool = False


def list_users() -> List[Dict[str, Any]]:
    """Return a copy of all stored users.

    The JSON file is small, so we simply read the whole document.
    """

    data = _USERS_STORE.read() or []
    return [dict(item) for item in data]


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Look up a user by id.

    Returns a shallow copy of the stored dict or ``None`` if no match
    is found.
    """

    data = _USERS_STORE.read() or []
    for item in data:
        if item.get("user_id") == user_id:
            return dict(item)
    return None


def get_default_dev_user(env_value: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Return a default development user if configured.

    Priority order:
    - explicit ``env_value`` (e.g. from BAZAARFLOW_DEV_USER_ID)
    - first record with ``is_dev_default=true``
    - first user in the file, if any
    """

    users = _USERS_STORE.read() or []
    if not users:
        return None

    if env_value:
        for item in users:
            if item.get("user_id") == env_value:
                return dict(item)

    for item in users:
        if item.get("is_dev_default"):
            return dict(item)

    return dict(users[0])
