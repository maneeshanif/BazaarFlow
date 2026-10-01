"""Customers API: the first DB-backed, tenant-scoped slice (PRD F-009, build-plan vertical slice).

It is the pattern later modules copy: role gate -> tenant-scoped session -> CRUD with explicit
tenant filter -> Postgres RLS as the backstop -> audit row for every write.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.auth import ALL_ROLES, MANAGER_UP, get_tenant_db, require_role
from app.core.tenancy import Principal
from app.crud import crud_customer
from app.schemas.customer import CustomerCreate, CustomerOut

router = APIRouter()


@router.get("/", response_model=list[CustomerOut])
async def list_customers(
    principal: Principal = Depends(require_role(*ALL_ROLES)),
    db: AsyncSession = Depends(get_tenant_db),
) -> list[CustomerOut]:
    customers = await crud_customer.get_customers(db, principal.tenant_id)
    return [CustomerOut.model_validate(c) for c in customers]


@router.post("/", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
async def create_customer(
    body: CustomerCreate,
    principal: Principal = Depends(require_role(*ALL_ROLES)),
    db: AsyncSession = Depends(get_tenant_db),
) -> CustomerOut:
    if await crud_customer.get_customer_by_phone(db, principal.tenant_id, body.phone):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Customer with this phone already exists")
    customer = await crud_customer.upsert_customer(
        db, principal.tenant_id, body.phone, name=body.name, email=body.email, address=body.address
    )
    record_audit(
        db,
        "customer.created",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="customer",
        entity_id=customer.id,
    )
    return CustomerOut.model_validate(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: str,
    principal: Principal = Depends(require_role(*MANAGER_UP)),
    db: AsyncSession = Depends(get_tenant_db),
) -> None:
    from uuid import UUID

    try:
        cid = UUID(customer_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found") from exc
    customers = await crud_customer.get_customers(db, principal.tenant_id)
    target = next((c for c in customers if c.id == cid), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    await db.delete(target)
    record_audit(
        db,
        "customer.deleted",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="customer",
        entity_id=customer_id,
    )
