"""Import all models here so Alembic autodiscovers them during migrations."""
from app.models.user import User, UserRole
from app.models.vendor import Vendor
from app.models.customer import Customer
from app.models.message import Message, MessageDirection
from app.models.order import Order
from app.models.inventory import InventoryItem
from app.models.marketing import MarketingPost, ScheduledCampaign
from app.models.support import SupportTicket
from app.models.facebook import FacebookAccount

__all__ = [
    "User", "UserRole",
    "Vendor",
    "Customer",
    "Message", "MessageDirection",
    "Order",
    "InventoryItem",
    "MarketingPost", "ScheduledCampaign",
    "SupportTicket",
    "FacebookAccount",
]
