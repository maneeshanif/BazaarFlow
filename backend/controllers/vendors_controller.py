"""Vendor-facing API surface consumed by the dashboard."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request  # type: ignore[import-not-found]
from pydantic import BaseModel, Field  # type: ignore[import-not-found]

from ..lib import repository
from ..services.whatsapp import WhatsAppAPIError, send_text_message, validate_phone_number

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vendors", tags=["vendors"])


class VendorCreatePayload(BaseModel):
    phone_number_id: str = Field(..., min_length=3)
    name: Optional[str] = None


class VendorSettingsPayload(BaseModel):
    phone_number_id: str = Field(..., min_length=3)
    access_token: str = Field(..., min_length=10)
    waba_id: Optional[str] = None
    facebook_app_id: Optional[str] = None


class SendMessagePayload(BaseModel):
    text: str = Field(..., min_length=1, max_length=1024)


class VendorSettingsResponse(BaseModel):
    vendor_id: str
    phone_number_id: Optional[str]
    waba_id: Optional[str]
    facebook_app_id: Optional[str]
    has_access_token: bool
    access_token_suffix: Optional[str]


class VendorResponse(BaseModel):
    vendor_id: str
    phone_number_id: str
    name: Optional[str]
    waba_id: Optional[str]


@router.get("", response_model=List[VendorResponse])
async def list_vendors():
    vendors = repository.list_vendors()
    return [
        VendorResponse(
            vendor_id=vendor["vendor_id"],
            phone_number_id=vendor.get("phone_number_id", ""),
            name=vendor.get("name"),
            waba_id=vendor.get("waba_id"),
        )
        for vendor in vendors
    ]


@router.post("", response_model=VendorResponse, status_code=201)
async def create_vendor(payload: VendorCreatePayload):
    vendor = repository.upsert_vendor(
        phone_number_id=payload.phone_number_id,
        name=payload.name,
    )
    return VendorResponse(
        vendor_id=vendor["vendor_id"],
        phone_number_id=vendor["phone_number_id"],
        name=vendor.get("name"),
        waba_id=vendor.get("waba_id"),
    )


@router.get("/{vendor_id}/customers")
async def list_vendor_customers(vendor_id: str):
    vendor = repository.get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    customers = repository.list_customers(vendor_id)
    return {"customers": customers}


@router.get("/{vendor_id}/customers/{customer_phone}/messages")
async def list_customer_messages(vendor_id: str, customer_phone: str):
    vendor = repository.get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    normalized_phone = _normalize_phone(customer_phone)
    search_number = normalized_phone or customer_phone
    messages = repository.list_messages(vendor_id, search_number)
    if not messages and normalized_phone and normalized_phone != customer_phone:
        messages = repository.list_messages(vendor_id, customer_phone)
    return {"messages": messages}


def _normalize_phone(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit())


def _mask_token(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    if len(token) <= 4:
        return "***"
    return f"…{token[-4:]}"


@router.get("/{vendor_id}/settings", response_model=VendorSettingsResponse)
async def get_vendor_settings(vendor_id: str):
    vendor = repository.get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    settings = vendor.get("settings", {})
    return VendorSettingsResponse(
        vendor_id=vendor["vendor_id"],
        phone_number_id=vendor.get("phone_number_id"),
        waba_id=vendor.get("waba_id"),
        facebook_app_id=settings.get("facebook_app_id"),
        has_access_token=bool(vendor.get("access_token")),
        access_token_suffix=_mask_token(vendor.get("access_token")),
    )


@router.post("/{vendor_id}/settings", response_model=VendorSettingsResponse)
async def update_vendor_settings_endpoint(
    vendor_id: str,
    payload: VendorSettingsPayload,
    request: Request,
):
    # Validate credentials with Meta API first
    http_client = request.app.state.http_client
    try:
        await validate_phone_number(
            client=http_client,
            phone_number_id=payload.phone_number_id,
            access_token=payload.access_token,
        )
    except Exception as exc:  # pragma: no cover - network failure detail logging only
        logger.warning("Meta validation failed: %s", exc)
        raise HTTPException(status_code=400, detail="Meta API validation failed") from exc

    # Try to update existing vendor, or create if not found
    try:
        updated = repository.update_vendor_settings(
            vendor_id,
            phone_number_id=payload.phone_number_id,
            waba_id=payload.waba_id,
            access_token=payload.access_token,
            settings={"facebook_app_id": payload.facebook_app_id} if payload.facebook_app_id else None,
        )
    except KeyError:
        # Vendor not found, get existing data or create new
        existing_vendor = repository.get_vendor(vendor_id)
        updated = repository.upsert_vendor(
            phone_number_id=payload.phone_number_id,
            name=existing_vendor.get("name") if existing_vendor else f"Vendor {payload.phone_number_id}",
            waba_id=payload.waba_id,
            access_token=payload.access_token,
            settings={"facebook_app_id": payload.facebook_app_id} if payload.facebook_app_id else None,
        )

    return VendorSettingsResponse(
        vendor_id=updated["vendor_id"],
        phone_number_id=updated.get("phone_number_id"),
        waba_id=updated.get("waba_id"),
        facebook_app_id=updated.get("settings", {}).get("facebook_app_id"),
        has_access_token=True,
        access_token_suffix=_mask_token(updated.get("access_token")),
    )


@router.post("/{vendor_id}/customers/{customer_phone}/messages")
async def send_vendor_message(
    vendor_id: str,
    customer_phone: str,
    payload: SendMessagePayload,
    request: Request,
):
    vendor = repository.get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    access_token = vendor.get("access_token")
    phone_number_id = vendor.get("phone_number_id")
    if not access_token or not phone_number_id:
        raise HTTPException(status_code=400, detail="Vendor is missing phone credentials")

    normalized_phone = _normalize_phone(customer_phone)
    if not normalized_phone:
        raise HTTPException(status_code=400, detail="Customer phone number must contain digits")

    http_client = request.app.state.http_client
    repository.upsert_customer(vendor_id, phone=normalized_phone)
    try:
        response = await send_text_message(
            client=http_client,
            phone_number_id=phone_number_id,
            access_token=access_token,
            to=normalized_phone,
            body=payload.text,
        )
    except WhatsAppAPIError as exc:
        failure_payload: Dict[str, Any] = {
            "status": "send_failed",
            "source": "whatsapp_api",
            "error": exc.payload,
        }
        if exc.status_code is not None:
            failure_payload["http_status"] = exc.status_code
        repository.record_message(
            vendor_id=vendor_id,
            customer_phone=normalized_phone,
            direction="outbound",
            text=payload.text,
            raw_payload=failure_payload,
        )
        status_code = exc.status_code or 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - unexpected failure path
        logger.exception("Failed to send message via WhatsApp API: %s", exc)
        repository.record_message(
            vendor_id=vendor_id,
            customer_phone=normalized_phone,
            direction="outbound",
            text=payload.text,
            raw_payload={"status": "send_failed", "source": "unexpected_error", "error": str(exc)},
        )
        raise HTTPException(status_code=502, detail="Failed to send WhatsApp message") from exc

    repository.record_message(
        vendor_id=vendor_id,
        customer_phone=normalized_phone,
        direction="outbound",
        text=payload.text,
        raw_payload=response,
    )

    return {"status": "sent", "response": response}
