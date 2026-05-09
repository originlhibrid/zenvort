import secrets
import hashlib
import bcrypt
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
import aiosqlite

from api.database import DB_PATH
from api.deps import get_current_user
from api.schemas import (
    SignupRequest,
    LoginRequest,
    UserSignupResponse,
    UserLoginResponse,
    UserSchema,
)
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


def _hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _generate_api_key() -> tuple[str, str]:
    """Generate a new API key and its SHA256 hash. Returns (api_key, api_key_hash)."""
    api_key = secrets.token_urlsafe(32)
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    return api_key, api_key_hash


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/signup", response_model=UserSignupResponse, status_code=201)
@limiter.limit("5000/hour")
async def signup(request: Request, body: SignupRequest):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id FROM users WHERE email = ?", (body.email,)
        ) as cur:
            if await cur.fetchone():
                raise HTTPException(status_code=409, detail="Email already registered")

        api_key, api_key_hash = _generate_api_key()
        user_id = str(uuid.uuid4())
        now = _iso_now()

        await db.execute(
            """INSERT INTO users (id, email, password, api_key, api_key_hash, role, created_at)
               VALUES (?, ?, ?, ?, ?, 'user', ?)""",
            (user_id, body.email, _hash_password(body.password), api_key, api_key_hash, now),
        )
        await db.commit()

    return UserSignupResponse(
        apiKey=api_key,
        user=UserSchema(
            id=user_id,
            email=body.email,
            role="user",
            webhook_url=None,
            created_at=now,
        ),
    )


@router.post("/login", response_model=UserLoginResponse)
@limiter.limit("30/15minute")
async def login(request: Request, body: LoginRequest):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE email = ?", (body.email,)
        ) as cur:
            row = await cur.fetchone()
            user = dict(row) if row else None

    if not user or not user.get("password") or not _verify_password(body.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return UserLoginResponse(
        apiKey=user["api_key"],
        user=UserSchema(
            id=user["id"],
            email=user["email"],
            role=user["role"],
            webhook_url=user.get("webhook_url"),
            created_at=user.get("created_at"),
        ),
    )
