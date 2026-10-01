"""Architecture tests for agent tools (PRD §3.7 constraint 4, §36.3-36.4, §36.20).

The model must never be able to choose the tenant, the user or the role. These tests look at what the model
actually sees (the JSON schema of every registered SDK tool) and at the catalog rules.
"""

from __future__ import annotations

import importlib
import pkgutil
import uuid
from typing import Any

import pytest
from agents.tool import FunctionTool

import app.agents.tools as tools_pkg
from app.agents.context import ToolContext
from app.agents.tools.catalog import (
    CATALOG,
    FORBIDDEN_PARAMS,
    ensure_allowed,
    forbidden_params,
    register_tool,
)
from app.models.tenant import TenantRole


def _sdk_tools() -> list[FunctionTool]:
    found: list[FunctionTool] = []
    for mod in pkgutil.iter_modules(tools_pkg.__path__):
        module = importlib.import_module(f"{tools_pkg.__name__}.{mod.name}")
        found.extend(v for v in vars(module).values() if isinstance(v, FunctionTool))
    return found


def test_there_are_sdk_tools_to_check() -> None:
    assert len(_sdk_tools()) >= 10


def test_no_sdk_tool_exposes_tenant_user_or_role_to_the_model() -> None:
    offenders = {
        tool.name: sorted(set(tool.params_json_schema.get("properties", {})) & FORBIDDEN_PARAMS)
        for tool in _sdk_tools()
        if set(tool.params_json_schema.get("properties", {})) & FORBIDDEN_PARAMS
    }
    assert not offenders, f"Tools the model could point at another tenant/user: {offenders}"


def test_every_registered_write_tool_requires_approval() -> None:
    assert all(spec.approval != "none" for spec in CATALOG.values() if spec.access == "write")


def test_registering_a_tool_with_a_tenant_argument_fails() -> None:
    def bad(tenant_id: str, sku: str) -> None: ...

    assert forbidden_params(bad) == ["tenant_id"]
    with pytest.raises(ValueError, match="ToolContext"):
        register_tool("bad_tool", access="read")(bad)
    assert "bad_tool" not in CATALOG


def test_registering_a_write_tool_without_approval_fails() -> None:
    def adjust(sku: str, delta: int) -> None: ...

    with pytest.raises(ValueError, match="approval"):
        register_tool("unsafe_write_tool", access="write")(adjust)
    assert "unsafe_write_tool" not in CATALOG


def test_role_gate_blocks_a_lower_role() -> None:
    def adjust_stock(sku: str, delta: int) -> None: ...

    register_tool("test_adjust_stock", access="write", min_role=TenantRole.manager, approval="required")(adjust_stock)
    spec = CATALOG["test_adjust_stock"]
    try:

        def ctx(role: TenantRole) -> ToolContext:
            return ToolContext(tenant_id=uuid.uuid4(), user_id=uuid.uuid4(), role=role, session=None)  # type: ignore[arg-type]

        ensure_allowed(spec, ctx(TenantRole.owner))
        ensure_allowed(spec, ctx(TenantRole.manager))
        with pytest.raises(PermissionError):
            ensure_allowed(spec, ctx(TenantRole.staff))
    finally:
        CATALOG.pop("test_adjust_stock", None)


def _unused(_: Any) -> None:  # keep Any imported for type checkers on older tool signatures
    return None
