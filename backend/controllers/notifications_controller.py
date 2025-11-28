"""Notifications API endpoints.

These endpoints expose a lightweight notification feed for the dashboard UI.
Currently notifications are global (not per-user) and primarily driven by
inventory threshold events.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from ..services.notification_service import notification_service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(limit: Optional[int] = None):
  """Return notifications ordered newest-first.

  Query params:
  - limit: optional integer to cap the number of returned notifications.
  """

  items = notification_service.list_notifications(limit=limit)
  unread_count = sum(1 for item in items if not item.get("read"))
  return {"ok": True, "notifications": items, "unread": unread_count}


@router.post("/{notification_id}/read")
async def mark_notification_read(notification_id: int):
  """Mark a single notification as read."""

  updated = notification_service.mark_read(notification_id)
  if not updated:
      raise HTTPException(status_code=404, detail="Notification not found")
  return {"ok": True, "notification": updated}


@router.post("/read-all")
async def mark_all_notifications_read():
  """Mark all notifications as read and return how many were updated."""

  count = notification_service.mark_all_read()
  return {"ok": True, "updated": count}
