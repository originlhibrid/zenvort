import glob
import os
import time
import httpx
import threading
import uuid
from datetime import datetime
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, declarative_base

from worker.celery_app import celery_app
from worker.config import get_settings
from worker.storage import upload_file, download_file
from worker.executor import execute_conversion
from worker.security.path_guard import TMP_DIR, sanitize_and_assert_tmp_path
from worker.security.mime_guard import assert_mime_type_matches

settings = get_settings()

# Sync DB engine for Celery worker (not async)
sync_engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
SyncSession = sessionmaker(sync_engine)

# Concurrency semaphore
_semaphore = threading.Semaphore(settings.WORKER_CONCURRENCY)

# ── Minimal ORM models (copy of db/models.py for worker) ────────────────────


Base = declarative_base()


class _User(Base):
    __tablename__ = "users"
    id = __tablename__  # fill below
    id = None
    credits = None
    webhook_url = None


# We import the same models from the api package so they stay in sync
# (paths are adjusted for when worker runs as a module)
try:
    from api.models import User as _UserModel
    from api.models import Job as _JobModel
    from api.models import CreditLog as _CreditLogModel
except ImportError:
    # Fallback: define inline — avoids import errors during container build
    class _UserModel(Base):
        __tablename__ = "users"
        id = None
        credits = None
        webhook_url = None

    class _JobModel(Base):
        __tablename__ = "jobs"
        id = None

    class _CreditLogModel(Base):
        __tablename__ = "credit_logs"
        id = None


# ── helpers ───────────────────────────────────────────────────────────────────


def _get_ext_from_url(input_url: str, fallback_format: str) -> str:
    """Extract extension from R2 URL path segment, fall back to input_format."""
    filename = input_url.split("/")[-1]
    _, ext = os.path.splitext(filename)
    if ext and len(ext) <= 10:
        return ext.lstrip(".")
    return fallback_format


def _cleanup(job_id: str) -> None:
    """Delete all /tmp/zenvort/<job_id>-* files."""
    for f in glob.glob(f"{TMP_DIR}/{job_id}-*"):
        try:
            os.unlink(f)
        except OSError:
            pass


def _fire_webhook(user_id: str, job_id: str, status: str) -> None:
    """Fire user webhook (fire-and-forget, no await)."""
    with SyncSession() as db:
        user = db.query(_UserModel).filter(_UserModel.id == user_id).first()
    webhook_url = getattr(user, "webhook_url", None) if user else None
    if not webhook_url:
        return
    try:
        httpx.post(webhook_url, json={"jobId": job_id, "status": status}, timeout=5.0)
    except Exception:
        pass


# ── Celery task ────────────────────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    throws=(SoftTimeLimitExceeded,),
)
def process_job(self, job_id: str) -> dict:
    with SyncSession() as db:
        job = db.query(_JobModel).filter(_JobModel.id == job_id).first()
        if not job:
            return {"error": f"Job {job_id} not found"}

        job.status = "PROCESSING"
        db.commit()

    input_format = job.input_format
    output_format = job.output_format
    user_id = job.user_id

    # ── Guard: same format → unrecoverable ──────────────────────────────
    if input_format == output_format:
        with SyncSession() as db:
            job = db.query(_JobModel).filter(_JobModel.id == job_id).first()
            job.status = "FAILED"
            job.error = "Unrecoverable: input and output formats are identical"
            db.commit()
        _cleanup(job_id)
        return {"error": "unrecoverable"}

    print(f"[worker][{job_id}] Job received "
          f"{{input_format={input_format}, output_format={output_format}, user_id={user_id}}}")

    # ── Disk space check (2GB limit) ─────────────────────────────────────
    _, _, free = os.disk_usage(TMP_DIR)
    if free < 2 * (1024 ** 3):
        print(f"[worker][{job_id}] Disk space low ({free} bytes free) — retrying")
        raise self.retry(exc=Exception("Disk space low"), countdown=60)

    # ── Concurrency semaphore ─────────────────────────────────────────────
    acquired = _semaphore.acquire(blocking=False)
    if not acquired:
        print(f"[worker][{job_id}] Concurrency limit reached — retrying")
        raise self.retry(exc=Exception("Concurrency limit reached"), countdown=30)

    try:
        # ── Download from R2 ─────────────────────────────────────────────
        input_ext = _get_ext_from_url(job.input_url, input_format)
        local_input = f"{TMP_DIR}/{job_id}-input.{input_ext}"
        os.makedirs(TMP_DIR, exist_ok=True)

        # Extract R2 key from input_url
        parts = job.input_url.rstrip("/").split("/")
        # R2 key is everything after the bucket host — last 2 path segments: inputs/{jobId}/...
        storage_key = "/".join(parts[-2:])
        download_file(storage_key, local_input)
        sanitize_and_assert_tmp_path(local_input)

        # ── Input file size check (200MB) ─────────────────────────────────
        if os.path.getsize(local_input) > 200 * (1024 ** 2):
            with SyncSession() as db:
                job = db.query(_JobModel).filter(_JobModel.id == job_id).first()
                job.status = "FAILED"
                job.error = "Input file exceeds 200MB limit"
                db.commit()
            _cleanup(job_id)
            return {"error": "unrecoverable"}

        # ── Cache lookup ────────────────────────────────────────────────────
        with SyncSession() as db:
            cached = (
                db.query(_JobModel)
                .filter(
                    _JobModel.input_url == job.input_url,
                    _JobModel.output_format == output_format,
                    _JobModel.status == "DONE",
                )
                .first()
            )

        if cached and cached.output_url:
            with SyncSession() as db:
                job = db.query(_JobModel).filter(_JobModel.id == job_id).first()
                job.status = "DONE"
                job.output_url = cached.output_url
                job.converter_used = "cache"
                db.commit()
            _cleanup(job_id)
            if user_id:
                _fire_webhook(user_id, job_id, "DONE")
            return {"status": "DONE", "cached": True}

        # ── Execute conversion ────────────────────────────────────────────
        local_output = f"{TMP_DIR}/{job_id}-output.{output_format}"
        print(f"[worker][{job_id}] Conversion started")

        result_conv = execute_conversion(
            job_id, local_input, local_output, input_format, output_format
        )
        converter_used = result_conv.get("converter_used", "unknown")

        print(f"[worker][{job_id}] Conversion done {{converter_used={converter_used}}}")

        # ── Output file size check (500MB) ────────────────────────────────
        output_size = os.path.getsize(local_output)
        if output_size > 500 * (1024 ** 2):
            with SyncSession() as db:
                job = db.query(_JobModel).filter(_JobModel.id == job_id).first()
                job.status = "FAILED"
                job.error = "Output file exceeds 500MB limit"
                db.commit()
            _cleanup(job_id)
            return {"error": "unrecoverable"}

        # ── MIME validation ────────────────────────────────────────────────
        assert_mime_type_matches(local_output, output_format)

        # ── Upload to R2 ──────────────────────────────────────────────────
        output_key = f"outputs/{job_id}/output.{output_format}"
        output_url = upload_file(local_output, output_key, "application/octet-stream")

        # ── Mark DONE ─────────────────────────────────────────────────────
        with SyncSession() as db:
            job = db.query(_JobModel).filter(_JobModel.id == job_id).first()
            job.status = "DONE"
            job.output_url = output_url
            job.converter_used = converter_used
            job.updated_at = datetime.utcnow()
            db.commit()

        # ── Deduct 1 credit ─────────────────────────────────────────────────
        if user_id:
            with SyncSession() as db:
                user = db.query(_UserModel).filter(_UserModel.id == user_id).first()
                if user and user.credits > 0:
                    user.credits -= 1

                    credit_log = _CreditLogModel()
                    credit_log.id = str(uuid.uuid4())
                    credit_log.user_id = user_id
                    credit_log.amount = -1
                    credit_log.reason = "conversion"
                    credit_log.job_id = job_id
                    credit_log.created_at = datetime.utcnow()
                    db.add(credit_log)
                    db.commit()

        # ── Webhook ────────────────────────────────────────────────────────
        if user_id:
            _fire_webhook(user_id, job_id, "DONE")

        return {"status": "DONE", "output_url": output_url}

    except SoftTimeLimitExceeded:
        with SyncSession() as db:
            job = db.query(_JobModel).filter(_JobModel.id == job_id).first()
            job.status = "FAILED"
            job.error = "Time limit exceeded"
            db.commit()
        raise

    except Exception as exc:
        error_str = str(exc)[:2000]
        print(f"[worker][{job_id}] Error: {error_str}")
        with SyncSession() as db:
            job = db.query(_JobModel).filter(_JobModel.id == job_id).first()
            job.status = "FAILED"
            job.error = error_str
            db.commit()
        raise self.retry(exc=exc, countdown=30)

    finally:
        _semaphore.release()
        _cleanup(job_id)
