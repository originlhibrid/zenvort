from datetime import datetime
import uuid
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    api_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, default=100)
    role: Mapped[str] = mapped_column(String(20), default="user")
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="user")
    credit_logs: Mapped[list["CreditLog"]] = relationship("CreditLog", back_populates="user")


class CreditLog(Base):
    __tablename__ = "credit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="credit_logs")

    __table_args__ = (
        Index("credit_logs_user_id_idx", "user_id"),
        Index("credit_logs_user_id_created_at_idx", "user_id", "created_at"),
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    input_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    output_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    input_format: Mapped[str] = mapped_column(String(20), nullable=False)
    output_format: Mapped[str] = mapped_column(String(20), nullable=False)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    converter_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User | None"] = relationship("User", back_populates="jobs")

    __table_args__ = (
        Index("jobs_user_id_idx", "user_id"),
        Index("jobs_status_idx", "status"),
        Index("jobs_user_id_created_at_idx", "user_id", "created_at"),
        Index("jobs_input_url_output_format_status_idx", "input_url", "output_format", "status"),
    )
