"""Onboarding wizard schemas (PRD F-003, W-001): the steps, their state, and the product import report."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

State = Literal["created", "shop_set", "whatsapp_connected", "products_added", "live"]
StepStatus = Literal["done", "current", "pending"]

MAX_CSV_BYTES = 200_000


class Step(BaseModel):
    key: Literal["shop", "channels", "products", "test"]
    label: str
    status: StepStatus
    required: bool  # only the shop details cannot be skipped


class OnboardingOut(BaseModel):
    state: State
    steps: list[Step]
    whatsapp_connected: bool
    facebook_connected: bool
    product_count: int
    owner_phone: str | None
    shop_name: str


class ShopStep(BaseModel):
    """The one required step: the same rules as the shop profile (F-020) and sign-up (F-002)."""

    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
    owner_phone: Annotated[str, Field(pattern=r"^\+[1-9][0-9]{7,14}$")]
    city: Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)] | None = None


class ImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    csv: Annotated[str, StringConstraints(min_length=1, max_length=MAX_CSV_BYTES)]


class RowError(BaseModel):
    row: int  # the line number in the file (the header is line 1)
    sku: str | None
    error: str


class ImportReport(BaseModel):
    imported: int
    failed: list[RowError]  # valid rows were imported; these were not
    state: State


class TestMessageResult(BaseModel):
    sent: bool
    state: State
    detail: str
