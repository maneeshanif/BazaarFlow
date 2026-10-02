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


class UnknownToolError(LookupError):
    """The model asked for a tool that is not in the catalogue."""


class ApprovalRequired(PermissionError):
    """The tool changes money, stock or something external: it may only be proposed, never run directly."""


def declare_tool(
    name: str, *, access: Access, min_role: TenantRole = TenantRole.staff, approval: Approval = "none"
) -> ToolSpec:
    """Declare an SDK tool (the SDK wraps the function, so the decorator above cannot be applied to it)."""
    if access == "write" and approval == "none":
        raise ValueError(f"write tool {name!r} must declare an approval level")
    if name in CATALOG:
        raise ValueError(f"tool {name!r} is already registered")
    spec = ToolSpec(name=name, access=access, min_role=min_role, approval=approval)
    CATALOG[name] = spec
    return spec


def authorize_call(name: str, ctx: ToolContext) -> ToolSpec:
    """The single gate a tool call passes before it runs: known tool, sufficient role, and no direct write
    when approval is required (the caller turns ``ApprovalRequired`` into an approval request)."""
    spec = CATALOG.get(name)
    if spec is None:
        raise UnknownToolError(f"unknown tool {name!r}")
    ensure_allowed(spec, ctx)
    if spec.access == "write" and spec.approval != "none":
        raise ApprovalRequired(f"tool {name} needs approval before it runs")
    return spec


def ensure_allowed(spec: ToolSpec, ctx: ToolContext) -> None:
    """Raise PermissionError when the caller's role is below the tool's minimum."""
    if _RANK[ctx.role] < _RANK[spec.min_role]:
        raise PermissionError(f"role {ctx.role.value} may not call tool {spec.name}")
