from app.core.settings import settings
"""Domain helpers for the JSON-backed MVP data store."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .json_store import JsonStore

JsonDocument = List[Dict[str, Any]]

_DB_ROOT_ENV = "BF_JSON_DB_ROOT"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_vendors() -> JsonDocument:
    return []


def _default_customers() -> JsonDocument:
    return []


def _default_messages() -> JsonDocument:
    return []


def _resolve_root() -> Path:
    env_path = os.getenv(_DB_ROOT_ENV)
    if env_path:
        return Path(env_path)
    # Default to the legacy JSON location under backend/db so existing data persists.
    return Path(__file__).resolve().parent.parent / "db"


_DB_ROOT = _resolve_root()

vendors_store: JsonStore
customers_store: JsonStore
messages_store: JsonStore


def configure_db_root(root: Path | str) -> None:
    """Re-initialise stores when tests point the DB at a temp directory."""
    global vendors_store, customers_store, messages_store, _DB_ROOT
    _DB_ROOT = Path(root)
    _DB_ROOT.mkdir(parents=True, exist_ok=True)

    vendors_store = JsonStore(_DB_ROOT / "vendors.json", _default_vendors)
    customers_store = JsonStore(_DB_ROOT / "customers.json", _default_customers)
    messages_store = JsonStore(_DB_ROOT / "messages.json", _default_messages)


configure_db_root(_DB_ROOT)


def _copy_dict(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if data is None:
        return None
    return {**data}


def get_vendor_by_phone_number_id(phone_number_id: str) -> Optional[Dict[str, Any]]:
    vendors = vendors_store.read()
    for vendor in vendors:
        if vendor.get("phone_number_id") == phone_number_id:
            return _copy_dict(vendor)
    return None


def get_vendor(vendor_id: str) -> Optional[Dict[str, Any]]:
    vendors = vendors_store.read()
    for vendor in vendors:
        if vendor.get("vendor_id") == vendor_id:
            return _copy_dict(vendor)
    return None


def upsert_vendor(
    *,
    phone_number_id: str,
    name: Optional[str] = None,
    waba_id: Optional[str] = None,
    access_token: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create or update a vendor identified by ``phone_number_id``."""

    def mutate(doc: JsonDocument):
        now = _utcnow()
        for vendor in doc:
            if vendor.get("phone_number_id") == phone_number_id:
                if name and name != vendor.get("name"):
                    vendor["name"] = name
                if waba_id and waba_id != vendor.get("waba_id"):
                    vendor["waba_id"] = waba_id
                if access_token:
                    vendor["access_token"] = access_token
                if settings:
                    merged = {**vendor.get("settings", {}), **settings}
                    vendor["settings"] = merged
                vendor["updated_at"] = now
                return doc, _copy_dict(vendor)
        vendor_id = str(uuid4())
        record = {
            "vendor_id": vendor_id,
            "name": name or f"Vendor {phone_number_id}",
            "phone_number_id": phone_number_id,
            "waba_id": waba_id,
            "access_token": access_token,
            "settings": settings or {},
            "created_at": now,
            "updated_at": now,
        }
        doc.append(record)
        return doc, _copy_dict(record)

    return vendors_store.update(mutate)


def update_vendor_settings(
    vendor_id: str,
    *,
    phone_number_id: Optional[str] = None,
    waba_id: Optional[str] = None,
    access_token: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Apply settings updates to a vendor, raising if unknown."""

    def mutate(doc: JsonDocument):
        now = _utcnow()
        for vendor in doc:
            if vendor.get("vendor_id") == vendor_id:
                if phone_number_id:
                    vendor["phone_number_id"] = phone_number_id
                if waba_id is not None:
                    vendor["waba_id"] = waba_id
                if access_token is not None:
                    vendor["access_token"] = access_token
                if settings:
                    merged = {**vendor.get("settings", {}), **settings}
                    vendor["settings"] = merged
                vendor["updated_at"] = now
                return doc, _copy_dict(vendor)
        raise KeyError(f"Vendor {vendor_id} not found")

    return vendors_store.update(mutate)


def list_vendors() -> List[Dict[str, Any]]:
    return [dict(vendor) for vendor in vendors_store.read()]


def upsert_customer(
    vendor_id: str,
    *,
    phone: str,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create or update a customer under ``vendor_id``."""

    def mutate(doc: JsonDocument):
        now = _utcnow()
        for customer in doc:
            if customer.get("vendor_id") == vendor_id and customer.get("phone") == phone:
                if name:
                    customer["name"] = name
                customer["last_seen"] = now
                return doc, _copy_dict(customer)
        record = {
            "id": str(uuid4()),
            "vendor_id": vendor_id,
            "phone": phone,
            "name": name,
            "first_seen": now,
            "last_seen": now,
        }
        doc.append(record)
        return doc, _copy_dict(record)

    return customers_store.update(mutate)


def list_customers(vendor_id: str) -> List[Dict[str, Any]]:
    customers = customers_store.read()
    return [dict(customer) for customer in customers if customer.get("vendor_id") == vendor_id]


def get_customer(vendor_id: str, phone: str) -> Optional[Dict[str, Any]]:
    customers = customers_store.read()
    for customer in customers:
        if customer.get("vendor_id") == vendor_id and customer.get("phone") == phone:
            return _copy_dict(customer)
    return None


def record_message(
    *,
    vendor_id: str,
    customer_phone: str,
    direction: str,
    text: Optional[str],
    raw_payload: Optional[Dict[str, Any]],
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist a chat message."""

    def mutate(doc: JsonDocument):
        record = {
            "id": str(uuid4()),
            "vendor_id": vendor_id,
            "customer_phone": customer_phone,
            "direction": direction,
            "text": text,
            "raw_payload": raw_payload,
            "timestamp": timestamp or _utcnow(),
        }
        doc.append(record)
        return doc, _copy_dict(record)

    return messages_store.update(mutate)


def list_messages(vendor_id: str, customer_phone: str, *, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    messages = [
        dict(message)
        for message in messages_store.read()
        if message.get("vendor_id") == vendor_id and message.get("customer_phone") == customer_phone
    ]
    messages.sort(key=lambda item: item.get("timestamp", ""))
    if limit is not None:
        return messages[-limit:]
    return messages


def recent_messages(vendor_id: str, customer_phone: str, *, limit: int = 10) -> List[Dict[str, Any]]:
    return list_messages(vendor_id, customer_phone, limit=limit)


__all__ = [
    "configure_db_root",
    "get_vendor_by_phone_number_id",
    "get_vendor",
    "list_vendors",
    "upsert_vendor",
    "update_vendor_settings",
    "upsert_customer",
    "get_customer",
    "list_customers",
    "record_message",
    "list_messages",
    "recent_messages",
]
