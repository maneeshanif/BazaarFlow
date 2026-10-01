"""Import all models here so Alembic autodiscovers them during migrations."""
from app.models.customer import Customer
from app.models.facebook import FacebookAccount
from app.models.inventory import InventoryItem
from app.models.marketing import MarketingPost, ScheduledCampaign
from app.models.message import Message, MessageDirection
from app.models.order import Order
from app.models.support import SupportTicket
from app.models.tenant import AuditLog, Membership, Tenant, TenantIntegration, TenantRole
from app.models.user import User
from app.models.vendor import Vendor

__all__ = [
    "AuditLog",
    "Customer",
    "FacebookAccount",
    "InventoryItem",
    "MarketingPost",
    "Membership",
    "Message",
    "MessageDirection",
    "Order",
    "ScheduledCampaign",
    "SupportTicket",
    "Tenant",
    "TenantIntegration",
    "TenantRole",
    "User",
    "Vendor",
]
