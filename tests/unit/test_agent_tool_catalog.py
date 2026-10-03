"""Task 29: every agent tool is declared in the catalogue (schema, permission, approval), a forbidden call is
rejected, and every tool has its own unit test (PRD 3.7 constraint 4, 36.3, 36.4, 36.9)."""

from __future__ import annotations

import importlib
import json
import pkgutil
import uuid
from typing import Any

import pytest
from agents.tool import FunctionTool
from agents.tool_context import ToolContext as SdkToolContext

import app.agents.tools as tools_pkg
from app.agents.context import ToolContext
from app.agents.tools.catalog import (
    CATALOG,
    FORBIDDEN_PARAMS,
    ApprovalRequired,
    UnknownToolError,
    authorize_call,
)
from app.agents.tools.manifest import DECLARATIONS, DELEGATION_WRAPPERS
from app.core.settings import settings
from app.models.tenant import TenantRole


def _sdk_tools() -> dict[str, FunctionTool]:
    found: dict[str, FunctionTool] = {}
    for mod in pkgutil.iter_modules(tools_pkg.__path__):
        module = importlib.import_module(f"{tools_pkg.__name__}.{mod.name}")
        for value in vars(module).values():
            if isinstance(value, FunctionTool):
                found[value.name] = value
    return found


TOOLS = _sdk_tools()


def _ctx(role: TenantRole) -> ToolContext:
    return ToolContext(tenant_id=uuid.uuid4(), user_id=uuid.uuid4(), role=role, session=None)  # type: ignore[arg-type]


# --- the catalogue is complete and consistent ---------------------------------------------------------------


def test_every_sdk_tool_is_declared_and_every_declaration_is_a_real_tool() -> None:
    function_declarations = set(DECLARATIONS) - DELEGATION_WRAPPERS
    assert set(TOOLS) == function_declarations, (
        f"undeclared tools: {sorted(set(TOOLS) - function_declarations)}; "
        f"declarations without a tool: {sorted(function_declarations - set(TOOLS))}. "
        "Declare each tool in app/agents/tools/manifest.py."
    )
    assert set(CATALOG) >= set(DECLARATIONS)


def test_every_tool_an_agent_can_call_is_declared_including_the_delegation_wrappers() -> None:
    """The review found consult_* wrappers (agents-as-tools) reaching governed tools undeclared."""
    from app.agents.finance_agent import finance_agent
    from app.agents.inventory_agent import inventory_agent
    from app.agents.marketing_agent import marketing_agent
    from app.agents.sales_agent import sales_agent

    wired = {
        tool.name for agent in (finance_agent, inventory_agent, marketing_agent, sales_agent) for tool in agent.tools
    }
    assert wired <= set(DECLARATIONS), f"agent tools without a declaration: {sorted(wired - set(DECLARATIONS))}"


def test_a_role_that_arrives_as_a_plain_string_is_handled_not_a_keyerror() -> None:
    ctx = ToolContext(tenant_id=uuid.uuid4(), user_id=None, role="manager", session=None)  # type: ignore[arg-type]
    assert authorize_call("marketing_sales_insights", ctx).name == "marketing_sales_insights"
    bad = ToolContext(tenant_id=uuid.uuid4(), user_id=None, role="superuser", session=None)  # type: ignore[arg-type]
    with pytest.raises(PermissionError):
        authorize_call("marketing_sales_insights", bad)


def test_write_tools_always_require_approval_and_reads_never_do() -> None:
    for name, spec in DECLARATIONS.items():
        if spec.access == "write":
            assert spec.approval == "required", name
        else:
            assert spec.approval == "none", name


def test_the_order_tool_is_declared_as_a_write_that_needs_approval() -> None:
    """PRD 36.9: the customer-facing agent has draft-only order creation."""
    spec = DECLARATIONS["create_customer_order"]
    assert (spec.access, spec.approval) == ("write", "required")


# --- a forbidden call is rejected ---------------------------------------------------------------------------


def test_an_unknown_tool_name_is_rejected() -> None:
    with pytest.raises(UnknownToolError):
        authorize_call("delete_everything", _ctx(TenantRole.owner))


def test_a_role_below_the_minimum_is_rejected() -> None:
    with pytest.raises(PermissionError):
        authorize_call("marketing_sales_insights", _ctx(TenantRole.staff))
    assert authorize_call("marketing_sales_insights", _ctx(TenantRole.manager)).name == "marketing_sales_insights"


def test_an_approval_gated_write_is_never_authorised_for_direct_execution() -> None:
    for role in TenantRole:
        with pytest.raises(ApprovalRequired):
            authorize_call("create_customer_order", _ctx(role))


def test_the_model_cannot_name_a_tenant_user_or_role_in_any_tool_schema() -> None:
    for name, tool in TOOLS.items():
        properties = set(tool.params_json_schema.get("properties", {}))
        assert not properties & FORBIDDEN_PARAMS, name


# --- one unit test per tool ---------------------------------------------------------------------------------

# valid arguments for a happy-path call of each read tool (writes are covered by the approval tests above)
SAMPLE_ARGS: dict[str, dict[str, Any]] = {
    "inventory_stock_overview": {},
    "inventory_restock_alerts": {"limit": 2},
    "inventory_category_summary": {"category": "Electronics"},
    "inventory_search_items": {"query": "phone"},
    "inventory_customer_catalog": {"limit": 3},
    "payment_status_overview": {},
    "payment_method_breakdown": {},
    "recent_pending_payments": {"limit": 2},
    "marketing_inventory_snapshot": {"limit": 3},
    "marketing_sales_insights": {},
    "marketing_image_search": {"query": "shoes", "orientation": "square"},
    "lookup_product": {"query": "phone"},
    "list_all_products": {},
    "get_product_by_price_range": {"min_price": 0, "max_price": 1000000},
    "get_product_by_category": {"category": "Electronics"},
}


# The sales agent's tools on the shop's database (app/agents/tools/shop_tools.py) need a tenant-scoped session, so they
# are exercised against real Postgres in tests/pg/test_shop_tools.py (which asserts it covers exactly this set).
DB_BACKED_READS = frozenset({"find_product", "find_customer", "get_balance", "draft_order", "get_sales_summary", "get_profit"})


def test_every_read_tool_has_sample_arguments_so_none_goes_untested() -> None:
    reads = {n for n, s in DECLARATIONS.items() if s.access == "read" and n not in DELEGATION_WRAPPERS}
    assert DB_BACKED_READS <= reads, "a database-backed read tool must be declared"
    assert reads - DB_BACKED_READS == set(SAMPLE_ARGS), f"add or remove sample arguments: {sorted((reads - DB_BACKED_READS) ^ set(SAMPLE_ARGS))}"


async def _call(tool: FunctionTool, arguments: dict[str, Any]) -> Any:
    ctx = SdkToolContext(context=None, tool_name=tool.name, tool_call_id="t1", tool_arguments=json.dumps(arguments))
    return await tool.on_invoke_tool(ctx, json.dumps(arguments))


@pytest.mark.parametrize("name", sorted(SAMPLE_ARGS))
async def test_read_tool_runs_and_returns_text_or_a_dict(name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "PEXELS_API_KEY", "", raising=False)  # never reach the network from a unit test
    result = await _call(TOOLS[name], SAMPLE_ARGS[name])
    assert isinstance(result, (str, dict)) and result, name
    assert "An error occurred while running the tool" not in str(result), f"{name} raised: {result}"


@pytest.mark.parametrize("name", sorted(TOOLS))
def test_tool_schema_is_strict_and_documented(name: str) -> None:
    tool = TOOLS[name]
    schema = tool.params_json_schema
    assert tool.description.strip(), f"{name} needs a description: the model reads it"
    assert schema.get("additionalProperties") is False, f"{name} accepts undeclared arguments"
    assert schema.get("type") == "object"


@pytest.mark.parametrize("name", sorted(SAMPLE_ARGS))
async def test_injected_tenant_or_role_arguments_never_reach_the_tool(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A model that adds tenant_id/role to a call gets either an error or exactly the normal result: the extra
    arguments are dropped before the function runs, so they cannot steer it."""
    monkeypatch.setattr(settings, "PEXELS_API_KEY", "", raising=False)
    normal = await _call(TOOLS[name], SAMPLE_ARGS[name])
    injected = {**SAMPLE_ARGS[name], "tenant_id": str(uuid.uuid4()), "role": "owner", "user_id": str(uuid.uuid4())}
    try:
        result = await _call(TOOLS[name], injected)
    except Exception:  # noqa: BLE001 - a validation error is a correct outcome
        return
    assert result == normal or "error" in str(result).lower() or "invalid" in str(result).lower(), name
