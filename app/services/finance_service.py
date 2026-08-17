"""Finance analytics utilities for the finance agent.

This service exposes deterministic summaries that our agent tools can
query. Keeping the logic in one place lets us test aggregation behaviour
without calling any LLMs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = BASE_DIR / "data" / "finance_transactions.json"


@dataclass(frozen=True)
class FinanceSnapshot:
    """Lightweight immutable view of amount + count."""

    count: int
    total_amount: int

    def to_dict(self) -> Dict[str, int]:
        return {"count": self.count, "total_amount": self.total_amount}


class FinanceAnalyticsService:
    """Provide derived metrics from recorded finance transactions."""

    def __init__(self, data_path: Optional[Path] = None) -> None:
        self._data_path = Path(data_path) if data_path else DEFAULT_DATASET
        self._cache: Optional[List[dict]] = None

    # ------------------------------------------------------------------
    # Data loading helpers
    def _ensure_cache(self) -> List[dict]:
        if self._cache is None:
            with self._data_path.open("r", encoding="utf-8") as handle:
                self._cache = json.load(handle)
        return self._cache

    def refresh(self) -> None:
        """Discard cached data so subsequent calls reload from disk."""
        self._cache = None

    # ------------------------------------------------------------------
    # Aggregations exposed to the agent tools
    def get_payment_status_snapshot(self) -> Dict[str, Dict[str, int]]:
        """Return totals per payment status (paid/pending/failed)."""
        totals: Dict[str, FinanceSnapshot] = {}
        for txn in self._ensure_cache():
            status = txn.get("status", "unknown").lower()
            amount = int(txn.get("amount", 0))
            snapshot = totals.get(status)
            if snapshot is None:
                totals[status] = FinanceSnapshot(count=1, total_amount=amount)
            else:
                totals[status] = FinanceSnapshot(
                    count=snapshot.count + 1,
                    total_amount=snapshot.total_amount + amount,
                )
        return {key: snap.to_dict() for key, snap in totals.items()}

    def get_method_summary(self) -> Dict[str, Dict[str, int]]:
        """Return totals per payment method (easypaisa/jazzcash/raast)."""
        totals: Dict[str, FinanceSnapshot] = {}
        for txn in self._ensure_cache():
            method = txn.get("method", "unknown").lower()
            amount = int(txn.get("amount", 0))
            snapshot = totals.get(method)
            if snapshot is None:
                totals[method] = FinanceSnapshot(count=1, total_amount=amount)
            else:
                totals[method] = FinanceSnapshot(
                    count=snapshot.count + 1,
                    total_amount=snapshot.total_amount + amount,
                )
        return {key: snap.to_dict() for key, snap in totals.items()}

    def get_recent_transactions(
        self,
        *,
        limit: int = 3,
        status: Optional[str] = None,
        method: Optional[str] = None,
    ) -> List[dict]:
        """Return the newest transactions filtered by optional criteria."""
        if limit <= 0:
            return []

        status_filter = status.lower() if status else None
        method_filter = method.lower() if method else None

        def _matches(txn: dict) -> bool:
            status_ok = (
                True if status_filter is None else txn.get("status", "").lower() == status_filter
            )
            method_ok = (
                True if method_filter is None else txn.get("method", "").lower() == method_filter
            )
            return status_ok and method_ok

        filtered: List[dict] = [txn for txn in self._ensure_cache() if _matches(txn)]

        def _parse_timestamp(value: str) -> datetime:
            try:
                return datetime.fromisoformat(value)
            except Exception:
                # Fall back to naive parsing without timezone
                return datetime.fromisoformat(value.replace("Z", ""))

        filtered.sort(key=lambda txn: _parse_timestamp(txn.get("timestamp", "")), reverse=True)
        return filtered[:limit]


# Singleton-style helper the rest of the app can import
finance_analytics_service = FinanceAnalyticsService()
