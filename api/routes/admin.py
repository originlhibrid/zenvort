from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models import User, Job, CreditLog
from api.deps import get_admin_user
from api.schemas import (
    AdminUserSchema,
    AdminUserListResponse,
    AdminStatsResponse,
    AdminCreditUpdateRequest,
)
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/users", response_model=AdminUserListResponse)
@limiter.limit("60/minute")
async def list_users(
    request: Request,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    offset = (page - 1) * limit

    count_result = await db.execute(select(func.count()).select_from(User))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    )
    users = result.scalars().all()

    return AdminUserListResponse(
        users=[AdminUserSchema.model_validate(u) for u in users],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/stats", response_model=AdminStatsResponse)
@limiter.limit("60/minute")
async def get_stats(
    request: Request,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    total_users_result = await db.execute(select(func.count()).select_from(User))
    total_users = total_users_result.scalar() or 0

    total_jobs_result = await db.execute(select(func.count()).select_from(Job))
    total_jobs = total_jobs_result.scalar() or 0

    total_credits_result = await db.execute(select(func.sum(User.credits)))
    total_credits = total_credits_result.scalar() or 0

    # Jobs by status — single grouped query
    status_result = await db.execute(
        select(Job.status, func.count(Job.id))
        .group_by(Job.status)
    )
    status_counts = {row[0]: row[1] for row in status_result.all()}
    for status in ["PENDING", "PROCESSING", "DONE", "FAILED"]:
        if status not in status_counts:
            status_counts[status] = 0

    return AdminStatsResponse(
        totalUsers=total_users,
        totalJobs=total_jobs,
        totalCredits=int(total_credits or 0),
        jobsByStatus=status_counts,
    )


@router.patch("/users/{user_id}/credits")
@limiter.limit("10/minute")
async def update_user_credits(
    request: Request,
    user_id: str,
    body: AdminCreditUpdateRequest,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.credits += body.amount

    credit_log = CreditLog(
        user_id=user_id,
        amount=body.amount,
        reason=body.reason,
    )
    db.add(credit_log)
    await db.commit()

    return {"ok": True, "credits": user.credits}