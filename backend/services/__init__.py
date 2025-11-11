"""Service package exports with lazy imports.

Modules are imported lazily to avoid circular import issues during app startup.
"""

from importlib import import_module

_CHAT_EXPORTS = {"ChatService", "chat_service", "finance_chat_service", "inventory_chat_service"}
_FINANCE_EXPORTS = {"FinanceAnalyticsService", "finance_analytics_service"}
_INVENTORY_EXPORTS = {"InventoryAnalyticsService", "inventory_analytics_service"}

__all__ = sorted(_CHAT_EXPORTS | _FINANCE_EXPORTS | _INVENTORY_EXPORTS)


def __getattr__(name):
    if name in _CHAT_EXPORTS:
        module = import_module("services.chat_service")
        return getattr(module, name)
    if name in _FINANCE_EXPORTS:
        module = import_module("services.finance_service")
        return getattr(module, name)
    if name in _INVENTORY_EXPORTS:
        module = import_module("services.inventory_service")
        return getattr(module, name)
    raise AttributeError(f"module 'services' has no attribute '{name}'")
