"""Import all models here so Alembic autodiscovers them during migrations."""

from app.models.agent import ActionStatus, AgentAction
from app.models.agent_run import AgentRun
from app.models.automation import Automation, AutomationRun
from app.models.conversation import Conversation, WebhookEvent
from app.models.customer import Customer
from app.models.facebook import FacebookAccount
from app.models.inventory import InventoryItem
from app.models.marketing import MarketingPost, ScheduledCampaign
from app.models.marketing_schedule import MarketingSchedule
from app.models.message import Message, MessageDirection
from app.models.order import Order, OrderItem
from app.models.payment import LedgerEntry, Payment
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.security import LoginAttempt, RefreshToken
from app.models.stock import StockMovement
from app.models.support import SupportTicket
from app.models.tenant import AuditLog, Membership, Tenant, TenantIntegration, TenantRole
from app.models.user import User
from app.models.vendor import Vendor, VendorBill, VendorPayment
from app.models.voice import VoiceCall, VoiceSettings

__all__ = [
    "ActionStatus",
    "AgentAction",
    "AgentRun",
    "AuditLog",
    "Automation",
    "AutomationRun",
    "Conversation",
    "Customer",
    "FacebookAccount",
    "InventoryItem",
    "LedgerEntry",
    "LoginAttempt",
    "MarketingPost",
    "MarketingSchedule",
    "Membership",
    "Message",
    "MessageDirection",
    "Order",
    "OrderItem",
    "Payment",
    "Product",
    "PurchaseOrder",
    "PurchaseOrderItem",
    "RefreshToken",
    "ScheduledCampaign",
    "StockMovement",
    "SupportTicket",
    "Tenant",
    "TenantIntegration",
    "TenantRole",
    "User",
    "WebhookEvent",
    "Vendor",
    "VendorBill",
    "VendorPayment",
    "VoiceCall",
    "VoiceSettings",
]
