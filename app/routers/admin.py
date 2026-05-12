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


class StorageCleanupBody(BaseModel):
    retention_days: int = 30
    max_age_hours: int = 24


@router.post("/storage/cleanup")
async def admin_cleanup_storage(
    body: StorageCleanupBody | None = None,
    _: None = Depends(verify_admin_secret),
):
    """
    Clean up old files from R2 storage.
    
    Deletes:
    - Orphaned input files older than max_age_hours (default: 24)
    - Output files older than retention_days (default: 30)
    """
    from app.storage_cleanup import cleanup_all, get_storage_stats
    
    retention = body.retention_days if body else 30
    max_age = body.max_age_hours if body else 24
    
    stats_before = get_storage_stats()
    results = cleanup_all(retention_days=retention, max_age_hours=max_age)
    stats_after = get_storage_stats()
    
    return {
        "message": "Storage cleanup completed",
        "results": results,
        "stats": {
            "before": stats_before,
            "after": stats_after,
            "freed_mb": (stats_before["total"]["size_bytes"] - stats_after["total"]["size_bytes"]) / 1024 / 1024,
        },
    }


@router.get("/storage/stats")
async def admin_storage_stats(
    _: None = Depends(verify_admin_secret),
):
    """
    Get current R2 storage usage statistics.
    """
    from app.storage_cleanup import get_storage_stats
    
    stats = get_storage_stats()
    
    return {
        "inputs": {
            "count": stats["inputs"]["count"],
            "size_mb": stats["inputs"]["size_bytes"] / 1024 / 1024,
        },
        "outputs": {
            "count": stats["outputs"]["count"],
            "size_mb": stats["outputs"]["size_bytes"] / 1024 / 1024,
        },
        "total": {
            "count": stats["total"]["count"],
            "size_mb": stats["total"]["size_bytes"] / 1024 / 1024,
        },
    }
