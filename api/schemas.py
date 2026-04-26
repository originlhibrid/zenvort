from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
import re


# ── helpers ────────────────────────────────────────────────────────────────────────


def to_camel(s: str) -> str:
    """snake_case → camelCase."""
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


# ── User ─────────────────────────────────────────────────────────────────────


class UserSchema(BaseModel):
    """Used for API responses. Fields are camelCase (alias) so JSON is camelCase.
    validation_alias lets Pydantic read snake_case SQLAlchemy model attributes."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    id: str
    email: str
    credits: int
    role: str = "user"
    webhook_url: str | None = Field(default=None, validation_alias="webhookUrl")
    created_at: datetime | None = Field(default=None, validation_alias="createdAt")


class UserSignupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)

    api_key: str = Field(validation_alias="apiKey")
    user: UserSchema


class UserLoginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)

    api_key: str = Field(validation_alias="apiKey")
    user: UserSchema


class WebhookUpdateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    ok: bool = True
    webhook_url: str = Field(validation_alias="webhookUrl")


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
    """API response schema. camelCase fields via alias_generator.
    validation_alias reads snake_case SQLAlchemy model attributes."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    id: str
    status: str
    input_url: str = Field(validation_alias="inputUrl")
    output_url: str | None = Field(default=None, validation_alias="outputUrl")
    input_format: str = Field(validation_alias="inputFormat")
    output_format: str = Field(validation_alias="outputFormat")
    error: str | None = None
    converter_used: str | None = Field(default=None, validation_alias="converterUsed")
    created_at: datetime | None = Field(default=None, validation_alias="createdAt")
    updated_at: datetime | None = Field(default=None, validation_alias="updatedAt")


class JobCreateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    job_id: str = Field(validation_alias="jobId")
    status: str = "PENDING"
    message: str = "Job queued successfully"


class JobListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

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
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    id: str
    amount: int
    reason: str
    job_id: str | None = Field(default=None, validation_alias="jobId")
    created_at: datetime | None = Field(default=None, validation_alias="createdAt")


class BillingUsageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    credits: int
    total_jobs: int = Field(validation_alias="totalJobs")
    jobs_today: int = Field(validation_alias="jobsToday")
    success_rate: float = Field(validation_alias="successRate")
    daily_usage: list[dict[str, Any]] = Field(default=[], validation_alias="dailyUsage")


class BillingTransactionsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    logs: list[CreditLogSchema]


# ── Admin ──────────────────────────────────────────────────────────────────────


class AdminUserSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    id: str
    email: str
    credits: int
    role: str
    created_at: datetime | None = Field(default=None, validation_alias="createdAt")


class AdminUserListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    users: list[AdminUserSchema]
    total: int
    page: int
    limit: int


class AdminStatsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    total_users: int = Field(validation_alias="totalUsers")
    total_jobs: int = Field(validation_alias="totalJobs")
    total_credits: int = Field(validation_alias="totalCredits")
    jobs_by_status: dict[str, int] = Field(validation_alias="jobsByStatus")


class AdminCreditUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    amount: int = Field(..., ge=-10000, le=10000)
    reason: str = "manual_add"


# ── Webhook update ─────────────────────────────────────────────────────────────


class WebhookUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    webhook_url: str = Field(validation_alias="webhookUrl")

    @field_validator("webhook_url")
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
