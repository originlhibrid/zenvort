import hmac
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.config import get_settings
from app.db import (
    create_api_key,
    list_keys,
    deactivate_key,
    get_usage_logs,
    get_key_by_id,
    reset_daily_counts,
)

settings = get_settings()
router = APIRouter(prefix="/v1/admin", tags=["admin"])


async def verify_admin_secret(x_admin_secret: str = Query(..., alias="admin_secret")) -> None:
    if not settings.ADMIN_SECRET or not hmac.compare_digest(
        x_admin_secret.encode(),
        settings.ADMIN_SECRET.encode(),
    ):
        raise HTTPException(
            status_code=403,
            detail={"error": "Forbidden", "code": "FORBIDDEN"},
        )


class CreateKeyBody(BaseModel):
    name: str
    tier: str = "free"


@router.post("/keys")
async def admin_create_key(
    body: CreateKeyBody,
    _: None = Depends(verify_admin_secret),
):
    result = await create_api_key(name=body.name, tier=body.tier)
    return result


@router.get("/keys")
async def admin_list_keys(
    _: None = Depends(verify_admin_secret),
):
    return await list_keys()


@router.delete("/keys/{key_id}")
async def admin_deactivate_key(
    key_id: str,
    _: None = Depends(verify_admin_secret),
):
    key = await get_key_by_id(key_id)
    if not key:
        raise HTTPException(status_code=404, detail={"error": "Key not found", "code": "NOT_FOUND"})
    await deactivate_key(key_id)
    return {"message": "Key deactivated"}


@router.get("/usage/{key_id}")
async def admin_get_usage(
    key_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _: None = Depends(verify_admin_secret),
):
    key = await get_key_by_id(key_id)
    if not key:
        raise HTTPException(status_code=404, detail={"error": "Key not found", "code": "NOT_FOUND"})
    logs = await get_usage_logs(key_id, limit=limit, offset=offset)
    return {"key_id": key_id, "logs": logs}


@router.post("/reset-daily")
async def admin_reset_daily(
    _: None = Depends(verify_admin_secret),
):
    await reset_daily_counts()
    return {"message": "Daily counts reset"}
