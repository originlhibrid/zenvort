"""001_initial

Revision ID: 001
Revises:
Create Date: 2026-04-26 00:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password", sa.String(255), nullable=True),
        sa.Column("api_key", sa.String(64), nullable=False, unique=True),
        sa.Column("api_key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("credits", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("webhook_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_api_key", "users", ["api_key"], unique=True)

    # ── Credit Logs ───────────────────────────────────────────────────────────
    op.create_table(
        "credit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("credit_logs_user_id_idx", "credit_logs", ["user_id"])
    op.create_index("credit_logs_user_id_created_at_idx", "credit_logs", ["user_id", "created_at"])

    # ── Jobs ────────────────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("input_url", sa.String(1000), nullable=False),
        sa.Column("output_url", sa.String(1000), nullable=True),
        sa.Column("input_format", sa.String(20), nullable=False),
        sa.Column("output_format", sa.String(20), nullable=False),
        sa.Column("error", sa.String(2000), nullable=True),
        sa.Column("converter_used", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("jobs_user_id_idx", "jobs", ["user_id"])
    op.create_index("jobs_status_idx", "jobs", ["status"])
    op.create_index("jobs_user_id_created_at_idx", "jobs", ["user_id", "created_at"])
    op.create_index("jobs_input_url_output_format_status_idx", "jobs", ["input_url", "output_format", "status"])


def downgrade() -> None:
    op.drop_table("jobs")
    op.drop_table("credit_logs")
    op.drop_table("users")
