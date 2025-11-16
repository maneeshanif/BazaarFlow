"""Persistence helpers for marketing automation features."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from .json_store import JsonStore

__all__ = [
    "configure_marketing_root",
    "upsert_facebook_account",
    "list_facebook_accounts",
    "get_facebook_account",
    "delete_facebook_account",
    "save_schedule",
    "get_schedule",
    "mark_schedule_triggered",
    "record_marketing_post",
    "list_marketing_posts",
    "update_post_insights",
    "delete_marketing_post",
]


_DB_ROOT_ENV = "BF_JSON_DB_ROOT"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_accounts() -> List[Dict[str, Any]]:
    return []


def _default_schedules() -> List[Dict[str, Any]]:
    return []


def _default_posts() -> List[Dict[str, Any]]:
    return []


def _resolve_root() -> Path:
    try:
        import os

        env_value = os.getenv(_DB_ROOT_ENV)
        if env_value:
            return Path(env_value)
    except Exception:  # pragma: no cover - defensive guard
        pass
    return Path(__file__).resolve().parent.parent / "db"


_FACEBOOK_ACCOUNTS_STORE: JsonStore
_SCHEDULES_STORE: JsonStore
_POSTS_STORE: JsonStore


def configure_marketing_root(root: Path | str) -> None:
    """Initialise marketing JsonStore instances at the given filesystem root."""

    global _FACEBOOK_ACCOUNTS_STORE, _SCHEDULES_STORE, _POSTS_STORE
    base_path = Path(root)
    base_path.mkdir(parents=True, exist_ok=True)

    _FACEBOOK_ACCOUNTS_STORE = JsonStore(base_path / "facebook_accounts.json", _default_accounts)
    _SCHEDULES_STORE = JsonStore(base_path / "marketing_schedules.json", _default_schedules)
    _POSTS_STORE = JsonStore(base_path / "marketing_posts.json", _default_posts)


configure_marketing_root(_resolve_root())


def _copy(record: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if record is None:
        return None
    return dict(record)


def upsert_facebook_account(
    *,
    user_id: str,
    page_id: str,
    access_token: str,
    page_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create or update a Facebook account credential bundle for the user."""

    def mutate(doc: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        now = _utcnow()
        for account in doc:
            if account.get("user_id") == user_id and account.get("page_id") == page_id:
                account["access_token"] = access_token
                if page_name:
                    account["page_name"] = page_name
                account["updated_at"] = now
                return doc, _copy(account)

        account_id = str(uuid4())
        record = {
            "account_id": account_id,
            "user_id": user_id,
            "page_id": page_id,
            "access_token": access_token,
            "page_name": page_name,
            "created_at": now,
            "updated_at": now,
        }
        doc.append(record)
        return doc, _copy(record)

    return _FACEBOOK_ACCOUNTS_STORE.update(mutate)


def list_facebook_accounts(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    accounts = [_copy(account) for account in _FACEBOOK_ACCOUNTS_STORE.read()]
    if user_id is None:
        return accounts
    return [account for account in accounts if account.get("user_id") == user_id]


def get_facebook_account(account_id: str) -> Optional[Dict[str, Any]]:
    for account in _FACEBOOK_ACCOUNTS_STORE.read():
        if account.get("account_id") == account_id:
            return _copy(account)
    return None


def delete_facebook_account(account_id: str) -> bool:
    def mutate(doc: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
        initial_len = len(doc)
        doc[:] = [account for account in doc if account.get("account_id") != account_id]
        return doc, len(doc) < initial_len

    return _FACEBOOK_ACCOUNTS_STORE.update(mutate)


def save_schedule(
    *,
    account_id: str,
    user_id: str,
    times: List[str],
    timezone_name: str = "UTC",
) -> Dict[str, Any]:
    """Persist up to three preferred posting times for an account."""

    trimmed_times = sorted({time.strip() for time in times if time.strip()})
    if len(trimmed_times) > 3:
        raise ValueError("A maximum of three scheduled times is supported")

    def mutate(doc: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        now = _utcnow()
        for schedule in doc:
            if schedule.get("account_id") == account_id:
                schedule["times"] = trimmed_times
                schedule["timezone"] = timezone_name
                schedule["updated_at"] = now
                return doc, _copy(schedule)

        schedule_id = str(uuid4())
        record = {
            "schedule_id": schedule_id,
            "account_id": account_id,
            "user_id": user_id,
            "times": trimmed_times,
            "timezone": timezone_name,
            "last_triggered_at": None,
            "created_at": now,
            "updated_at": now,
        }
        doc.append(record)
        return doc, _copy(record)

    return _SCHEDULES_STORE.update(mutate)


def get_schedule(account_id: str) -> Optional[Dict[str, Any]]:
    for schedule in _SCHEDULES_STORE.read():
        if schedule.get("account_id") == account_id:
            return _copy(schedule)
    return None


def mark_schedule_triggered(account_id: str, *, triggered_at: Optional[str] = None) -> Optional[Dict[str, Any]]:
    timestamp = triggered_at or _utcnow()

    def mutate(doc: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        for schedule in doc:
            if schedule.get("account_id") == account_id:
                schedule["last_triggered_at"] = timestamp
                schedule["updated_at"] = timestamp
                return doc, _copy(schedule)
        return doc, None

    return _SCHEDULES_STORE.update(mutate)


def record_marketing_post(
    *,
    account_id: str,
    user_id: str,
    facebook_post_id: str,
    message: str,
    image_url: Optional[str],
    product_sku: Optional[str],
    hashtags: Optional[List[str]],
    angle: Optional[str],
    source: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Persist metadata for a marketing post that was published."""

    def mutate(doc: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        record_id = str(uuid4())
        now = _utcnow()
        record = {
            "record_id": record_id,
            "account_id": account_id,
            "user_id": user_id,
            "facebook_post_id": facebook_post_id,
            "message": message,
            "image_url": image_url,
            "product_sku": product_sku,
            "hashtags": hashtags or [],
            "angle": angle,
            "source": source,
            "extra": extra or {},
            "created_at": now,
            "updated_at": now,
            "insights": None,
        }
        doc.append(record)
        return doc, _copy(record)

    return _POSTS_STORE.update(mutate)


def list_marketing_posts(account_id: str, *, limit: int = 20) -> List[Dict[str, Any]]:
    records = [record for record in _POSTS_STORE.read() if record.get("account_id") == account_id]
    records.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return [_copy(record) for record in records[: max(limit, 0) or len(records)]]


def update_post_insights(
    *,
    account_id: str,
    facebook_post_id: str,
    insights: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    def mutate(doc: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        for record in doc:
            if record.get("account_id") == account_id and record.get("facebook_post_id") == facebook_post_id:
                record["insights"] = insights
                record["updated_at"] = _utcnow()
                return doc, _copy(record)
        return doc, None

    return _POSTS_STORE.update(mutate)


def delete_marketing_post(*, account_id: str, facebook_post_id: str) -> bool:
    """Remove a marketing post record for the given account."""

    def mutate(doc: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
        initial_len = len(doc)
        doc[:] = [
            record
            for record in doc
            if not (record.get("account_id") == account_id and record.get("facebook_post_id") == facebook_post_id)
        ]
        return doc, len(doc) < initial_len

    return _POSTS_STORE.update(mutate)
