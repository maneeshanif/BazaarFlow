import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
BACKEND_DIR = HERE.parent
sys.path.insert(0, str(BACKEND_DIR))

from services.finance_service import FinanceAnalyticsService


@pytest.fixture(scope="module")
def finance_service():
    data_path = BACKEND_DIR / "data" / "finance_transactions.json"
    return FinanceAnalyticsService(data_path=data_path)


def test_payment_status_snapshot(finance_service):
    snapshot = finance_service.get_payment_status_snapshot()

    assert set(snapshot.keys()) == {"paid", "pending", "failed"}

    assert snapshot["paid"]["count"] == 7
    assert snapshot["paid"]["total_amount"] == 450_000

    assert snapshot["pending"]["count"] == 3
    assert snapshot["pending"]["total_amount"] == 66_000

    assert snapshot["failed"]["count"] == 2
    assert snapshot["failed"]["total_amount"] == 42_000


def test_method_summary(finance_service):
    summary = finance_service.get_method_summary()

    assert summary["easypaisa"]["count"] == 4
    assert summary["easypaisa"]["total_amount"] == 238_000

    assert summary["jazzcash"]["count"] == 4
    assert summary["jazzcash"]["total_amount"] == 143_000

    assert summary["raast"]["count"] == 4
    assert summary["raast"]["total_amount"] == 177_000


def test_recent_transactions_filtering(finance_service):
    recent_pending = finance_service.get_recent_transactions(limit=2, status="pending")

    assert len(recent_pending) == 2
    # Ensure newest first by timestamp
    assert recent_pending[0]["id"] == "INV-2024-0009"
    assert recent_pending[1]["id"] == "INV-2024-0004"

    # Ensure filter respects status and keeps original amount
    assert all(txn["status"] == "pending" for txn in recent_pending)
    assert {txn["amount"] for txn in recent_pending} == {23_000, 15_000}
