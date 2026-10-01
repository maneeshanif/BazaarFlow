"""Shared fixtures for the legacy-style unit tests.

The v1 services persist to JSON files under ``app/data``. Tests must never write to those
files, so every test gets its own copy of the inventory dataset.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.services import inventory_service


@pytest.fixture(autouse=True)
def _isolate_inventory_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    copy = tmp_path / "inventory_items.json"
    shutil.copy(inventory_service.DEFAULT_DATASET, copy)
    monkeypatch.setattr(inventory_service.inventory_analytics_service, "_data_path", copy)
