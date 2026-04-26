import hashlib
import asyncio
from fastapi import Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import get_db
from api.models import User


async def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    api_key = authorization.split(" ", 1)[1]
    api_key_hash = await asyncio.to_thread(
        lambda: hashlib.sha256(api_key.encode()).hexdigest()
    )

    result = await db.execute(select(User).where(User.api_key_hash == api_key_hash))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return user


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user