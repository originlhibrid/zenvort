from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models import User
from api.deps import get_current_user
from api.schemas import UserSchema, WebhookUpdateResponse, WebhookUpdateRequest

router = APIRouter()


@router.get("/me", response_model=UserSchema)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserSchema.model_validate(current_user)


@router.patch("/webhook", response_model=WebhookUpdateResponse)
async def update_webhook(
    body: WebhookUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.webhook_url = body.webhookUrl
    await db.commit()
    return WebhookUpdateResponse(ok=True, webhookUrl=body.webhookUrl)
