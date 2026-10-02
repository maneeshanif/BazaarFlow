"""Declaration of every agent tool: what it does to data, who may call it, whether it needs approval (PRD 36.4).

A test fails when a tool exists without a declaration here (or the reverse), so a new tool cannot ship
ungoverned. Import this module before calling ``authorize_call``.
"""

from __future__ import annotations

from app.agents.tools.catalog import ToolSpec, declare_tool
from app.models.tenant import TenantRole

_STAFF, _MANAGER = TenantRole.staff, TenantRole.manager

DECLARATIONS: dict[str, ToolSpec] = {
    # inventory (read-only)
    "inventory_stock_overview": declare_tool("inventory_stock_overview", access="read"),
    "inventory_restock_alerts": declare_tool("inventory_restock_alerts", access="read"),
    "inventory_category_summary": declare_tool("inventory_category_summary", access="read"),
    "inventory_search_items": declare_tool("inventory_search_items", access="read"),
    "inventory_customer_catalog": declare_tool("inventory_customer_catalog", access="read"),
    # finance
    "payment_status_overview": declare_tool("payment_status_overview", access="read", min_role=_MANAGER),
    "payment_method_breakdown": declare_tool("payment_method_breakdown", access="read", min_role=_MANAGER),
    "recent_pending_payments": declare_tool("recent_pending_payments", access="read", min_role=_MANAGER),
    # customer-facing order draft: PRD 36.9 says orders created by customers go to approval
    "create_customer_order": declare_tool("create_customer_order", access="write", approval="required"),
    # marketing
    "marketing_inventory_snapshot": declare_tool("marketing_inventory_snapshot", access="read", min_role=_MANAGER),
    "marketing_sales_insights": declare_tool("marketing_sales_insights", access="read", min_role=_MANAGER),
    "marketing_image_search": declare_tool("marketing_image_search", access="read", min_role=_MANAGER),
    # sales (read-only product lookups for the customer chat)
    "lookup_product": declare_tool("lookup_product", access="read"),
    "list_all_products": declare_tool("list_all_products", access="read"),
    "get_product_by_price_range": declare_tool("get_product_by_price_range", access="read"),
    "get_product_by_category": declare_tool("get_product_by_category", access="read"),
}
