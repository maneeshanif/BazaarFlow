"""Vendor endpoints — exact port of backend/controllers/vendors_controller.py"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


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


def _normalize_phone(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit())

def _mask_token(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    return f"***{token[-4:]}" if len(token) > 4 else "***"


@router.get("", response_model=List[VendorResponse])
async def list_vendors():
    # TODO: replace with DB query via SQLAlchemy
    return []


@router.post("", response_model=VendorResponse, status_code=201)
async def create_vendor(payload: VendorCreatePayload):
    # TODO: replace with DB insert
    pass


@router.get("/{vendor_id}/customers")
async def list_vendor_customers(vendor_id: str):
    # TODO: query customers table filtered by vendor_id
    return {"customers": []}


@router.get("/{vendor_id}/customers/{customer_phone}/messages")
async def list_customer_messages(vendor_id: str, customer_phone: str):
    normalized = _normalize_phone(customer_phone)
    # TODO: query messages table
    return {"messages": []}


@router.get("/{vendor_id}/settings", response_model=VendorSettingsResponse)
async def get_vendor_settings(vendor_id: str):
    # TODO: query vendor from DB
    raise HTTPException(status_code=404, detail="Vendor not found")


@router.post("/{vendor_id}/settings", response_model=VendorSettingsResponse)
async def update_vendor_settings(vendor_id: str, payload: VendorSettingsPayload, request: Request):
    # TODO: validate Meta credentials then upsert vendor settings
    raise HTTPException(status_code=501, detail="Not yet implemented")


@router.post("/{vendor_id}/customers/{customer_phone}/messages")
async def send_vendor_message(vendor_id: str, customer_phone: str, payload: SendMessagePayload, request: Request):
    normalized = _normalize_phone(customer_phone)
    if not normalized:
        raise HTTPException(status_code=400, detail="Customer phone number must contain digits")
    # TODO: send via meta_whatsapp integration + record message
    raise HTTPException(status_code=501, detail="Not yet implemented")
