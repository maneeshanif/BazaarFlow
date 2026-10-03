"""Import all models here so Alembic autodiscovers them during migrations."""

from app.models.agent import ActionStatus, AgentAction
from app.models.customer import Customer
from app.models.facebook import FacebookAccount
from app.models.inventory import InventoryItem
from app.models.marketing import MarketingPost, ScheduledCampaign
from app.models.message import Message, MessageDirection
from app.models.order import Order, OrderItem
from app.models.payment import LedgerEntry, Payment
from app.models.product import Product
from app.models.security import LoginAttempt, RefreshToken
from app.models.stock import StockMovement
from app.models.support import SupportTicket
from app.models.tenant import AuditLog, Membership, Tenant, TenantIntegration, TenantRole
from app.models.user import User
from app.models.vendor import Vendor

__all__ = [
    "ActionStatus",
    "AgentAction",
    "AuditLog",
    "Customer",
    "FacebookAccount",
    "InventoryItem",
    "LedgerEntry",
    "LoginAttempt",
    "MarketingPost",
    "Membership",
    "Message",
    "MessageDirection",
    "Order",
    "OrderItem",
    "Payment",
    "Product",
    "RefreshToken",
    "ScheduledCampaign",
    "StockMovement",
    "SupportTicket",
    "Tenant",
    "TenantIntegration",
    "TenantRole",
    "User",
    "Vendor",
]
