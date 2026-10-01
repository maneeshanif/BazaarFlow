"""Shared fixtures for the legacy-style unit tests.

The v1 services persist to JSON files under ``app/data``. Tests must never write to those
files, so every test gets its own copy of the inventory dataset.
"""

from __future__ import annotations

import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.core.auth import get_principal
from app.core.tenancy import Principal
from app.main import app
from app.models.tenant import TenantRole
from app.services import inventory_service


@pytest.fixture(autouse=True)
def _isolate_inventory_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    copy = tmp_path / "inventory_items.json"
    shutil.copy(inventory_service.DEFAULT_DATASET, copy)
    monkeypatch.setattr(inventory_service.inventory_analytics_service, "_data_path", copy)


@pytest.fixture(autouse=True)
def _authenticated_owner() -> Iterator[None]:
    """Controller-level tests run as a platform-admin owner (see tests/integration/conftest.py)."""
    principal = Principal(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role=TenantRole.owner, is_platform_admin=True)
    app.dependency_overrides[get_principal] = lambda: principal
    yield
    app.dependency_overrides.pop(get_principal, None)
