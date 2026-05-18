"""
VortexRAG — Auth Endpoints
Register, login, and token refresh.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter()

# ── Temporary in-memory user store (Phase 1 placeholder) ──────────────────────
# This will be replaced with a proper DB in Phase 2
_users: dict[str, dict] = {}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    if body.email in _users:
        raise HTTPException(status_code=400, detail="Email already registered")

    _users[body.email] = {
        "email": body.email,
        "full_name": body.full_name,
        "hashed_password": hash_password(body.password),
    }

    token = create_access_token(subject=body.email)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    user = _users.get(body.email)
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(subject=body.email)
    return TokenResponse(access_token=token)
