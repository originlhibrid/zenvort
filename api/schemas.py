from datetime import datetime
from typing import Any, Self
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
import re


# ── helpers ────────────────────────────────────────────────────────────────────────


def to_camel(s: str) -> str:
    """snake_case → camelCase."""
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


# ── User ─────────────────────────────────────────────────────────────────────


class UserSchema(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    id: str
    email: str
    credits: int
    role: str = "user"
    webhookUrl: str | None = None
    createdAt: datetime | None = None


class UserSignupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    apiKey: str
    user: UserSchema


class UserLoginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    apiKey: str
    user: UserSchema


class WebhookUpdateResponse(BaseModel):
    ok: bool = True
    webhookUrl: str


# ── Auth ─────────────────────────────────────────────────────────────────────


class SignupRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    password: str


# ── Jobs ─────────────────────────────────────────────────────────────────────


class JobSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    status: str
    inputUrl: str
    outputUrl: str | None = None
    inputFormat: str
    outputFormat: str
    error: str | None = None
    converterUsed: str | None = None
    createdAt: datetime | None = None
    updatedAt: datetime | None = None


class JobCreateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    jobId: str
    status: str = "PENDING"
    message: str = "Job queued successfully"


class JobListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    jobs: list[JobSchema]
    total: int
    page: int
    limit: int


# ── Billing ───────────────────────────────────────────────────────────────────


class PlanSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pack: str
    credits: int
    amount: int
    currency: str
    name: str


class BillingPurchaseResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ok: bool = True
    message: str = "Payment integration coming soon"


class BillingPurchaseRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pack: str


class CreditLogSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    amount: int
    reason: str
    jobId: str | None = None
    createdAt: datetime | None = None


class BillingUsageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    credits: int
    totalJobs: int
    jobsToday: int
    successRate: float
    dailyUsage: list[dict[str, Any]] = []


class BillingTransactionsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    logs: list[CreditLogSchema]


# ── Admin ──────────────────────────────────────────────────────────────────────


class AdminUserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    email: str
    credits: int
    role: str
    createdAt: datetime | None = None


class AdminUserListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    users: list[AdminUserSchema]
    total: int
    page: int
    limit: int


class AdminStatsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    totalUsers: int
    totalJobs: int
    totalCredits: int
    jobsByStatus: dict[str, int]


class AdminCreditUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    amount: int = Field(..., ge=-10000, le=10000)
    reason: str = Field(default="manual_add")


# ── Webhook update ─────────────────────────────────────────────────────────────


class WebhookUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    webhookUrl: str

    @field_validator("webhookUrl")
    @classmethod
    def must_be_valid_url(cls, v: str) -> str:
        url_pattern = re.compile(
            r"^https?://"
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
            r"localhost|"
            r"(?:[A-Z0-9-]+\.)+[A-Z]{2,6})"
            r"(?::\d+)?"
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )
        if not url_pattern.match(v):
            raise ValueError("Invalid URL format")
        return v


# ── Health ─────────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    ok: bool = True
    timestamp: str
