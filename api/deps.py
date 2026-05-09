import hashlib
import asyncio
from fastapi import Depends, HTTPException, Header
import aiosqlite

from api.database import get_db, DB_PATH


async def _fetch_user_by_hash(db: aiosqlite.Connection, api_key_hash: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM users WHERE api_key_hash = ?", (api_key_hash,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    api_key = authorization.split(" ", 1)[1]
    api_key_hash = await asyncio.to_thread(
        lambda: hashlib.sha256(api_key.encode()).hexdigest()
    )

    user = await _fetch_user_by_hash(None, api_key_hash)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return user


async def get_admin_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def get_optional_user(
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict | None:
    """Get user if authenticated, otherwise return None (allows anonymous access)."""
    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        return None

    api_key = authorization.split(" ", 1)[1]
    api_key_hash = await asyncio.to_thread(
        lambda: hashlib.sha256(api_key.encode()).hexdigest()
    )

    user = await _fetch_user_by_hash(None, api_key_hash)
    return user
