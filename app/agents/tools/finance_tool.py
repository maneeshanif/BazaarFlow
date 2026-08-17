"""Tool functions used by the finance agent."""
from agents import function_tool

from app.services.finance_service import finance_analytics_service
from app.services.sales_service import save_order


def _format_summary(summary: dict[str, dict[str, int]]) -> str:
    parts: list[str] = []
    for key, payload in summary.items():
        title = key.replace("_", " ").title()
        count = payload.get("count", 0)
        amount = payload.get("total_amount", 0)
        parts.append(f"• {title}: {count} txns · PKR {amount:,}")
    return "\n".join(parts)


@function_tool
def payment_status_overview() -> str:
    """Summarise paid, pending, and failed invoices."""
    summary = finance_analytics_service.get_payment_status_snapshot()
    if not summary:
        return "No transactions recorded yet."
    return "Payment Status Summary:\n" + _format_summary(summary)


@function_tool
def payment_method_breakdown() -> str:
    """Show totals per payment method (Easypaisa, JazzCash, RAAST)."""
    summary = finance_analytics_service.get_method_summary()
    if not summary:
        return "No payment methods recorded yet."
    return "Payment Methods:\n" + _format_summary(summary)


@function_tool
def recent_pending_payments(limit: int = 3) -> str:
    """List the newest pending payments."""
    transactions = finance_analytics_service.get_recent_transactions(limit=limit, status="pending")
    if not transactions:
        return "All payments are cleared ✅"

    lines: list[str] = []
    for txn in transactions:
        lines.append(
            f"• {txn['id']}: PKR {txn['amount']:,} via {txn['method'].title()}"
        )
    return "Pending Payments:\n" + "\n".join(lines)


@function_tool
def create_customer_order(
    customer_name: str,
    customer_phone: str,
    product_name: str,
    quantity: int,
    delivery_address: str,
    budget: str = "",
    notes: str = "",
) -> str:
    """
    Create a new customer order and save it to the database.
    
    Args:
        customer_name: Full name of the customer
        customer_phone: Phone number (with country code if international)
        product_name: Name of the product being ordered
        quantity: Number of units
        delivery_address: Delivery address
        budget: Optional budget range or amount
        notes: Optional additional notes
    
    Returns:
        Confirmation message with order ID
    """
    if not customer_name or not customer_phone or not product_name:
        return "❌ Missing required fields: customer_name, customer_phone, product_name"
    
    if quantity <= 0:
        return "❌ Quantity must be at least 1"
    
    payload = {
        "customer_name": customer_name.strip(),
        "customer_phone": customer_phone.strip(),
        "product_id": "",  # Will be resolved later if needed
        "product_name": product_name.strip(),
        "quantity": quantity,
        "budget": budget.strip() if budget else "",
        "payment_status": "placed",
        "delivery_address": delivery_address.strip(),
        "notes": notes.strip() if notes else "",
    }
    
    try:
        order = save_order(payload)
    except ValueError as exc:
        return f"❌ {exc}"
    except Exception as exc:  # pragma: no cover - defensive path for unexpected errors
        return f"❌ Failed to create order: {exc}"

    snapshot = order.get("inventory_snapshot", {})
    remaining = snapshot.get("remaining_stock")
    inventory_line = ""
    if remaining is not None:
        inventory_line = f"\nStock remaining: {remaining} unit(s)"

    return (
        f"✅ Order #{order['id']} created successfully!\n"
        f"Product: {order.get('product_name', product_name)}\n"
        f"Quantity: {quantity}\n"
        f"Customer: {customer_name}\n"
        f"Delivery to: {delivery_address}\n"
        f"Status: Order Placed ✓"
        f"{inventory_line}"
    )
