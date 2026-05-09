from fastapi import APIRouter, Depends, Request
import aiosqlite
from api.deps import get_admin_user

from api.database import DB_PATH
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


def _admin_stats_from_db() -> dict:
    """Fetch admin stats directly from SQLite (no user auth needed)."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status"
    ).fetchall()
    status_counts = {row["status"]: row["cnt"] for row in rows}
    for s in ["pending", "processing", "done", "failed"]:
        status_counts.setdefault(s, 0)

    conn.close()
    return {
        "totalUsers": total_users,
        "totalJobs": total_jobs,
        "jobsByStatus": status_counts,
    }


@router.get("/users")
@limiter.limit("60/minute")
async def list_users(
    request: Request,
    page: int = 1,
    limit: int = 20,
    current_admin: dict = Depends(get_admin_user),
):
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    offset = (page - 1) * limit

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            row = await cur.fetchone()
            total = row[0] if row else 0

        async with db.execute(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ) as cur:
            rows = await cur.fetchall()
            users = [dict(r) for r in rows]

    # Convert to camelCase for response
    from api.schemas import AdminUserSchema
    return {
        "users": [AdminUserSchema(**_to_admin_user(u)) for u in users],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/stats")
@limiter.limit("60/minute")
async def get_stats(
    request: Request,
    current_admin: dict = Depends(get_admin_user),
):
    stats = _admin_stats_from_db()
    from api.schemas import AdminStatsResponse
    return AdminStatsResponse(**stats)


def _to_admin_user(u: dict) -> dict:
    return {
        "id": u["id"],
        "email": u["email"],
        "role": u.get("role", "user"),
        "createdAt": u.get("created_at"),
    }
