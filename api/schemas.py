from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
import re


# ── Error sanitisation ────────────────────────────────────────────────────────────────


def _strip_internal(s: str) -> str:
    """Final safety net: strip any remaining internal paths or module references."""
    s = re.sub(r"\bworker\.\S+", "", s)
    s = re.sub(r"/\S+\.py\b", "", s)
    s = re.sub(r"line \d+", "", s)
    s = re.sub(r"\bpdf2docx\b", "", s)
    s = re.sub(r"\bcairosvg\b", "", s)
    s = re.sub(r"\bpymupdf\b", "", s)
    s = re.sub(r"\bimg2pdf\b", "", s)
    s = re.sub(r"\bgotenberg\b", "", s)
    s = re.sub(r"\btesseract\b", "", s)
    s = re.sub(r"\bffmpeg\b", "", s)
    s = re.sub(r"\bpillow\b", "", s)
    s = re.sub(r"\bpandoc\b", "", s)
    s = re.sub(r"\bcalibre\b", "", s)
    s = re.sub(r"\bworker\b", "", s)
    return " ".join(s.split()).strip()


# ── helpers ────────────────────────────────────────────────────────────────────────


def to_camel(s: str) -> str:
    """snake_case → camelCase."""
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


# ── User ─────────────────────────────────────────────────────────────────────


class UserSchema(BaseModel):
    """API response schema for user profile data."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    id: str
    email: str
    role: str = "user"
    webhook_url: str | None = Field(default=None, validation_alias="webhookUrl")
    created_at: datetime | None = Field(default=None, validation_alias="createdAt")
    daily_usage: int = Field(default=0, validation_alias="dailyUsage", description="Number of successful conversions today")
    daily_limit: int = Field(default=50, validation_alias="dailyLimit", description="Max conversions per day")
    quota_reset_at: str | None = Field(default=None, validation_alias="quotaResetAt", description="ISO timestamp when daily quota resets")


class UserSignupResponse(BaseModel):
    """Response returned after successful user registration."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)

    api_key: str = Field(validation_alias="apiKey")
    user: UserSchema


class UserLoginResponse(BaseModel):
    """Response returned after successful user login."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)

    api_key: str = Field(validation_alias="apiKey")
    user: UserSchema


class WebhookUpdateResponse(BaseModel):
    """Response returned after updating a user's webhook URL."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    ok: bool = True
    webhook_url: str = Field(validation_alias="webhookUrl")


# ── Auth ─────────────────────────────────────────────────────────────────────


class SignupRequest(BaseModel):
    """Request body for user registration."""

    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    """Request body for user login."""

    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    password: str


# ── Jobs ─────────────────────────────────────────────────────────────────────


class JobSchema(BaseModel):
    """API response schema for a conversion job."""

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
    expires_at: str | None = Field(default=None, validation_alias="expiresAt")

    @field_validator("error", mode="before")
    @classmethod
    def sanitize_error(cls, v):
        if v is None:
            return None
        cleaned = _strip_internal(str(v))
        return cleaned if cleaned else "Conversion failed. Please try again."

    @field_validator("converter_used", mode="before")
    @classmethod
    def mask_converter(cls, v):
        return "zenvort-engine" if v is not None else None


class JobCreateResponse(BaseModel):
    """Response returned after successfully creating a conversion job."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    job_id: str = Field(validation_alias="jobId")
    status: str = "PENDING"
    message: str = "Job queued successfully"


class JobListResponse(BaseModel):
    """Paginated list of conversion jobs."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    jobs: list[JobSchema]
    total: int
    page: int
    limit: int


# ── Admin ──────────────────────────────────────────────────────────────────────


class AdminUserSchema(BaseModel):
    """Schema for admin user list entries."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    id: str
    email: str
    role: str
    created_at: datetime | None = Field(default=None, validation_alias="createdAt")


class AdminUserListResponse(BaseModel):
    """Paginated list of users for admin view."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    users: list[AdminUserSchema]
    total: int
    page: int
    limit: int


class AdminStatsResponse(BaseModel):
    """System-wide statistics for admin dashboard."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    total_users: int = Field(validation_alias="totalUsers")
    total_jobs: int = Field(validation_alias="totalJobs")
    jobs_by_status: dict[str, int] = Field(validation_alias="jobsByStatus")


# ── Webhook update ─────────────────────────────────────────────────────────────


class WebhookUpdateRequest(BaseModel):
    """Request body for updating a user's webhook URL."""

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
    """Health check endpoint response."""

    ok: bool = True
    timestamp: str
