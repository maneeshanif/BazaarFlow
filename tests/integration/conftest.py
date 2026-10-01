"""Auth override for tests that exercise controller behaviour without a database.

Authentication and role enforcement are covered end to end by ``tests/pg`` and the architecture
tests; here every request is simply made by a platform-admin owner.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest

from app.core.auth import get_principal
from app.core.tenancy import Principal
from app.main import app
from app.models.tenant import TenantRole


@pytest.fixture(autouse=True)
def _authenticated_owner() -> Iterator[None]:
    principal = Principal(
        user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role=TenantRole.owner, is_platform_admin=True
    )
    app.dependency_overrides[get_principal] = lambda: principal
    yield
    app.dependency_overrides.pop(get_principal, None)
