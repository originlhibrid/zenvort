import socket
import urllib.parse
import ipaddress
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite

from api.database import DB_PATH
from api.deps import get_current_user
from api.schemas import UserSchema, WebhookUpdateResponse, WebhookUpdateRequest

router = APIRouter()

MAX_CONVERSIONS_PER_DAY = 50


def _midnight_utc() -> str:
    """Return the ISO timestamp for the next midnight UTC."""
    now = datetime.now(timezone.utc)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if now > midnight:
        midnight += timedelta(days=1)
    return midnight.isoformat()


async def _daily_success_count(db: aiosqlite.Connection, user_id: str) -> int:
    """Count successful jobs for this user today (UTC)."""
    cursor = await db.execute(
        """SELECT COUNT(*) as cnt FROM jobs
           WHERE user_id = ?
           AND date(created_at) = date('now', 'utc')
           AND status = 'done'""",
        (user_id,),
    )
    row = await cursor.fetchone()
    return row["cnt"] if row else 0


@router.get("/me", response_model=UserSchema)
async def get_me(current_user: dict = Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        daily_usage = await _daily_success_count(db, current_user["id"])

    return UserSchema(
        id=current_user["id"],
        email=current_user["email"],
        role=current_user.get("role", "user"),
        webhook_url=current_user.get("webhook_url"),
        created_at=current_user.get("created_at"),
        daily_usage=daily_usage,
        daily_limit=MAX_CONVERSIONS_PER_DAY,
        quota_reset_at=_midnight_utc(),
    )


@router.patch("/webhook", response_model=WebhookUpdateResponse)
async def update_webhook(
    body: WebhookUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        host = urllib.parse.urlparse(body.webhook_url).hostname
        ip = socket.gethostbyname(host)
        if ipaddress.ip_address(ip).is_private or ipaddress.ip_address(ip).is_reserved:
            raise HTTPException(400, "Webhook URL must not point to a private or reserved network")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Could not resolve webhook URL")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET webhook_url = ? WHERE id = ?",
            (body.webhook_url, current_user["id"]),
        )
        await db.commit()

    return WebhookUpdateResponse(ok=True, webhook_url=body.webhook_url)