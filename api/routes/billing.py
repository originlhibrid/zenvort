from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from api.database import get_db
from api.models import User, Job, CreditLog
from api.deps import get_current_user
from api.schemas import (
    PlanSchema,
    BillingPurchaseResponse,
    BillingPurchaseRequest,
    BillingUsageResponse,
    BillingTransactionsResponse,
    CreditLogSchema,
)
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

PLANS = [
    PlanSchema(pack="starter", credits=500, amount=199, currency="INR", name="Starter Pack"),
    PlanSchema(pack="pro", credits=2000, amount=599, currency="INR", name="Pro Pack"),
    PlanSchema(pack="enterprise", credits=10000, amount=1999, currency="INR", name="Enterprise Pack"),
]


@router.get("/plans", response_model=list[PlanSchema])
async def get_plans():
    return PLANS


@router.post("/purchase", response_model=BillingPurchaseResponse)
@limiter.limit("5/minute")
async def purchase_credits(
    request: Request,
    body: BillingPurchaseRequest,
    current_user: User = Depends(get_current_user),
):
    return BillingPurchaseResponse(ok=True, message="Payment integration coming soon")


@router.get("/usage", response_model=BillingUsageResponse)
@limiter.limit("30/minute")
async def get_usage(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    agg_result = await db.execute(
        select(
            func.count().label("total"),
            func.sum(case((Job.status == "DONE", 1), else_=0)).label("done"),
            func.sum(case((Job.created_at >= today_start, 1), else_=0)).label("today"),
        ).where(Job.user_id == current_user.id)
    )
    row = agg_result.one()
    total_jobs = row.total or 0
    done_count = row.done or 0
    jobs_today = row.today or 0
    success_rate = (done_count / total_jobs * 100) if total_jobs > 0 else 0.0

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    daily_query = await db.execute(
        select(
            func.date(Job.created_at).label("date"),
            func.count(Job.id).label("count"),
        )
        .where(
            Job.user_id == current_user.id,
            Job.created_at >= thirty_days_ago,
            Job.status == "DONE",
        )
        .group_by(func.date(Job.created_at))
        .order_by(func.date(Job.created_at))
    )
    daily_counts = {str(row.date): row.count for row in daily_query.all()}

    daily_usage = []
    for i in range(30):
        day = (datetime.utcnow() - timedelta(days=29 - i)).replace(hour=0, minute=0, second=0, microsecond=0)
        date_str = day.strftime("%Y-%m-%d")
        daily_usage.append({"date": date_str, "count": daily_counts.get(date_str, 0)})

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