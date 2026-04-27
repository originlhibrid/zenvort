from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import secrets
import hashlib
import bcrypt

from api.database import get_db
from api.models import User, CreditLog
from api.deps import get_current_user
from api.schemas import (
    SignupRequest,
    LoginRequest,
    UserSignupResponse,
    UserLoginResponse,
)
from api.config import get_settings
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

settings = get_settings()
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


@router.post("/signup", response_model=UserSignupResponse, status_code=201)
@limiter.limit("5000/hour")
async def signup(
    request: Request,
    body: SignupRequest,
    db: AsyncSession = Depends(get_db),
):
    # Check uniqueness
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    api_key = secrets.token_urlsafe(32)
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    user = User(
        email=body.email,
        password=hash_password(body.password),
        api_key=api_key,          # raw key — returned on login so client can re-auth
        api_key_hash=api_key_hash,  # hash — used for server-side auth lookup
        credits=100,
        role="user",
    )
    db.add(user)
    await db.flush()

    credit_log = CreditLog(
        user_id=user.id,
        amount=100,
        reason="signup",
    )
    db.add(credit_log)
    await db.commit()

    return UserSignupResponse(
        apiKey=api_key,
        user={
            "id": user.id,
            "email": user.email,
            "credits": user.credits,
            "role": user.role,
            "webhookUrl": user.webhook_url,
            "createdAt": user.created_at,
        },
    )


@router.post("/login", response_model=UserLoginResponse)
@limiter.limit("30/15minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.password or not verify_password(body.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return UserLoginResponse(
        apiKey=user.api_key,
        user={
            "id": user.id,
            "email": user.email,
            "credits": user.credits,
            "role": user.role,
            "webhookUrl": user.webhook_url,
            "createdAt": user.created_at,
        },
    )
