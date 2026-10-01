"""Registry of agent tools and the rules every tool must obey (PRD §3.7 constraint 4, §36.4).

* A tool never takes tenant/user/role as an argument: those come from ``ToolContext``.
* A tool that writes must declare an approval level other than ``none``.
* A tool may only run for callers whose role is at least ``min_role``.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from app.agents.context import ToolContext
from app.models.tenant import TenantRole

FORBIDDEN_PARAMS = frozenset({"tenant_id", "tenant", "user_id", "user", "role", "vendor_id"})
_RANK = {TenantRole.staff: 0, TenantRole.manager: 1, TenantRole.owner: 2}

Access = Literal["read", "write"]
Approval = Literal["none", "auto_under_limit", "required"]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    access: Access
    min_role: TenantRole
    approval: Approval


CATALOG: dict[str, ToolSpec] = {}


def forbidden_params(fn: Callable[..., Any]) -> list[str]:
    return sorted(set(inspect.signature(fn).parameters) & FORBIDDEN_PARAMS)


def register_tool(
    name: str, *, access: Access, min_role: TenantRole = TenantRole.staff, approval: Approval = "none"
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a tool and reject, at import time, a definition that breaks the rules above."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        bad = forbidden_params(fn)
        if bad:
            raise ValueError(f"tool {name!r} takes {bad}; tenant/user/role come from ToolContext, not arguments")
        if access == "write" and approval == "none":
            raise ValueError(f"write tool {name!r} must declare an approval level")
        if name in CATALOG:
            raise ValueError(f"tool {name!r} is already registered")
        CATALOG[name] = ToolSpec(name=name, access=access, min_role=min_role, approval=approval)
        return fn

    return decorator


def ensure_allowed(spec: ToolSpec, ctx: ToolContext) -> None:
    """Raise PermissionError when the caller's role is below the tool's minimum."""
    if _RANK[ctx.role] < _RANK[spec.min_role]:
        raise PermissionError(f"role {ctx.role.value} may not call tool {spec.name}")
