"""Notification service backed by the JSON store.

This keeps notification persistence lightweight and aligned with the rest of the
MVP JSON database. Notifications are stored in a single document of the form:

    {"notifications": [ ... ]}

Notifications are append-only and can be marked as read.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:  # When running via `python -m backend.app` or similar
    from backend.lib.json_store import JsonStore  # type: ignore[import-not-found]
except Exception:  # When tests import services.* from backend root
    from lib.json_store import JsonStore  # type: ignore[no-redef,import-not-found]


_store = JsonStore(
    "backend/db/notifications.json", default_factory=lambda: {"notifications": []}
)


@dataclass
class Notification:
    id: int
    type: str
    title: str
    message: str
    severity: str  # info | warning | error
    created_at: str
    read: bool = False
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Ensure metadata is always a dict for JSON consumers
        if data["metadata"] is None:
            data["metadata"] = {}
        return data


class NotificationService:
    """High-level helper for creating and listing notifications."""

    def __init__(self) -> None:
        self._store = _store

    def _next_id(self, payload: Dict[str, Any]) -> int:
        existing: List[Dict[str, Any]] = list(payload.get("notifications", []))
        if not existing:
            return 1
        return max(int(item.get("id", 0) or 0) for item in existing) + 1

    def create_notification(
        self,
        *,
        type: str,
        title: str,
        message: str,
        severity: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Append a new notification and return it as a dict."""

        def mutator(current: Dict[str, Any]):
            notifications: List[Dict[str, Any]] = list(current.get("notifications", []))
            new_id = self._next_id(current)
            now = datetime.now(timezone.utc).isoformat()
            notification = Notification(
                id=new_id,
                type=type,
                title=title,
                message=message,
                severity=severity,
                created_at=now,
                read=False,
                metadata=metadata or {},
            )
            notifications.append(notification.to_dict())
            return {"notifications": notifications}, notification.to_dict()

        return self._store.update(mutator)

    def list_notifications(self, *, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return notifications ordered newest-first (by id)."""

        payload: Dict[str, Any] = self._store.read()
        notifications: List[Dict[str, Any]] = list(payload.get("notifications", []))
        notifications.sort(key=lambda item: int(item.get("id", 0) or 0), reverse=True)
        if limit is not None and limit > 0:
            return notifications[:limit]
        return notifications

    def mark_read(self, notification_id: int) -> Optional[Dict[str, Any]]:
        """Mark a single notification as read. Returns the updated notification or None."""

        def mutator(current: Dict[str, Any]):
            notifications: List[Dict[str, Any]] = list(current.get("notifications", []))
            updated: Optional[Dict[str, Any]] = None
            for item in notifications:
                if int(item.get("id", 0) or 0) == notification_id:
                    item["read"] = True
                    updated = dict(item)
                    break
            return {"notifications": notifications}, updated

        return self._store.update(mutator)

    def mark_all_read(self) -> int:
        """Mark all notifications as read. Returns the count updated."""

        def mutator(current: Dict[str, Any]):
            notifications: List[Dict[str, Any]] = list(current.get("notifications", []))
            count = 0
            for item in notifications:
                if not item.get("read"):
                    item["read"] = True
                    count += 1
            return {"notifications": notifications}, count

        return self._store.update(mutator)


notification_service = NotificationService()

__all__ = ["notification_service", "NotificationService"]
