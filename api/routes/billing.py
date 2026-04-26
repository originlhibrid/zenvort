from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from api.database import get_db
from api.models import User, Job, CreditLog
from api.deps import get_current_user
from api.schemas import (
    PlanSchema,
    BillingPurchaseResponse,
    BillingUsageResponse,
    BillingTransactionsResponse,
    CreditLogSchema,
)

router = APIRouter()

PLANS = [
    PlanSchema(pack="starter", credits=500, amount=199, currency="INR", name="Starter Pack"),
    PlanSchema(pack="pro", credits=2000, amount=599, currency="INR", name="Pro Pack"),
    PlanSchema(pack="enterprise", credits=10000, amount=1999, currency="INR", name="Enterprise Pack"),
]


@router.get("/plans", response_model=list[PlanSchema])
async def get_plans():
    return PLANS


@router.post("/purchase", response_model=BillingPurchaseResponse)
async def purchase_credits(
    current_user: User = Depends(get_current_user),
):
    return BillingPurchaseResponse(ok=True, message="Payment integration coming soon")


@router.get("/usage", response_model=BillingUsageResponse)
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Total jobs
    count_result = await db.execute(
        select(func.count()).select_from(Job).where(Job.user_id == current_user.id)
    )
    total_jobs = count_result.scalar() or 0

    # Jobs today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count())
        .select_from(Job)
        .where(Job.user_id == current_user.id, Job.created_at >= today_start)
    )
    jobs_today = today_result.scalar() or 0

    # Success rate
    done_result = await db.execute(
        select(func.count()).select_from(Job).where(Job.user_id == current_user.id, Job.status == "DONE")
    )
    done_count = done_result.scalar() or 0
    success_rate = (done_count / total_jobs * 100) if total_jobs > 0 else 0.0

    # Last 30 days daily usage
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_usage = []
    # (Simplified - real implementation would group by date)
    daily_usage.append({"date": datetime.utcnow().strftime("%Y-%m-%d"), "count": jobs_today})

    return BillingUsageResponse(
        credits=current_user.credits,
        totalJobs=total_jobs,
        jobsToday=jobs_today,
        successRate=round(success_rate, 2),
        dailyUsage=daily_usage,
    )


@router.get("/transactions", response_model=BillingTransactionsResponse)
async def get_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CreditLog)
        .where(CreditLog.user_id == current_user.id)
        .order_by(CreditLog.created_at.desc())
        .limit(100)
    )
    logs = result.scalars().all()
    return BillingTransactionsResponse(logs=[CreditLogSchema.model_validate(l) for l in logs])
