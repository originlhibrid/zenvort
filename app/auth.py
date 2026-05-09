import hashlib
from fastapi import HTTPException, Header

from app.db import get_key_by_hash


async def verify_api_key(x_api_key: str = Header(alias="X-API-Key")) -> dict:
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "Missing X-API-Key header", "code": "UNAUTHORIZED"},
        )

    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    key = await get_key_by_hash(key_hash)

    if not key or not key.get("is_active"):
        raise HTTPException(
            status_code=401,
            detail={"error": "Invalid or revoked API key", "code": "UNAUTHORIZED"},
        )

    return key
