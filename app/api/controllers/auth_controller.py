"""Auth endpoints � login, register, token."""
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.user import LoginRequest, UserCreate, UserOut, TokenOut

router = APIRouter()

@router.post("/login", response_model=TokenOut)
async def login(body: LoginRequest):
    # TODO: implement JWT auth with database lookup
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Auth not yet implemented")

@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: UserCreate):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Registration not yet implemented")
