"""The agent service must never hold database access (ADR 0003). It refuses to start if it does."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping

# Names that mean "database access". Anchored so ordinary variables (DEBUG, DBUS_*) are not caught.
_DATABASE_NAME = re.compile(
    r"^(DATABASE(_|$)|POSTGRES(QL)?(_|$)|PG(PASSWORD|HOST|USER|PORT|DATABASE|SERVICE)$"
    r"|SUPABASE_(DB|SERVICE|DATABASE)|DB_(HOST|URL|USER|PASSWORD|NAME|PORT|DSN|CONNECTION)|SQLALCHEMY_)"
    r"|(_DATABASE_URL|_DB_URL|_DSN)$",
    re.IGNORECASE,
)
# A connection string under any name is still database access.
_DATABASE_VALUE = re.compile(r"^(postgres(ql)?|mysql|mariadb|mssql|sqlite)(\+\w+)?://", re.IGNORECASE)


class DatabaseCredentialsPresent(RuntimeError):
    """A database variable is set in the agent service's environment."""


def find_database_variables(env: Mapping[str, str]) -> list[str]:
    return sorted(name for name, value in env.items() if _DATABASE_NAME.search(name) or _DATABASE_VALUE.match(value))


def assert_no_database_environment(env: Mapping[str, str] | None = None) -> None:
    found = find_database_variables(os.environ if env is None else env)
    if found:
        raise DatabaseCredentialsPresent(
            f"the agent service must not have database access, but its environment sets: {', '.join(found)}. "
            "Remove them; the service reaches data only through the API."
        )
