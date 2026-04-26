from fastapi import APIRouter, Depends, HTTPException
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

router = APIRouter()


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
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
async def get_stats(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    total_users_result = await db.execute(select(func.count()).select_from(User))
    total_users = total_users_result.scalar() or 0

    total_jobs_result = await db.execute(select(func.count()).select_from(Job))
    total_jobs = total_jobs_result.scalar() or 0

    total_credits_result = await db.execute(select(func.sum(User.credits)))
    total_credits = total_credits_result.scalar() or 0

    # Jobs by status
    status_counts = {}
    for status in ["PENDING", "PROCESSING", "DONE", "FAILED"]:
        count_result = await db.execute(
            select(func.count()).select_from(Job).where(Job.status == status)
        )
        status_counts[status] = count_result.scalar() or 0

    return AdminStatsResponse(
        totalUsers=total_users,
        totalJobs=total_jobs,
        totalCredits=int(total_credits),
        jobsByStatus=status_counts,
    )


@router.patch("/users/{user_id}/credits")
async def update_user_credits(
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
