from datetime import datetime, timezone, timedelta

from fastapi import HTTPException, UploadFile

from app.config import get_settings

TIER_LIMITS = {
    "free": 50,
    "pro": 500,
    "enterprise": 10000,
}


def validate_file_size(file: UploadFile, max_mb: int | None = None) -> int:
    if max_mb is None:
        max_mb = get_settings().MAX_FILE_SIZE_MB
    limit = max_mb * 1024 * 1024
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > limit:
        raise HTTPException(
            status_code=413,
            detail={"error": f"File exceeds {max_mb}MB limit", "code": "FILE_TOO_LARGE"},
        )
    if size == 0:
        raise HTTPException(
            status_code=400,
            detail={"error": "Empty file", "code": "INVALID_INPUT"},
        )
    return size


async def check_rate_limit(key: dict) -> None:
    tier = key.get("tier", "free")
    limit = TIER_LIMITS.get(tier, 50)
    if key.get("requests_today", 0) >= limit:
        now = datetime.now(timezone.utc)
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Daily rate limit exceeded",
                "code": "RATE_LIMIT_EXCEEDED",
                "tier": tier,
                "limit": limit,
                "resets_at": next_midnight.isoformat(),
            },
        )
