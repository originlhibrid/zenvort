import glob
import logging
import os
import shutil
import httpx
import uuid
from datetime import datetime
from urllib.parse import urlparse
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from worker.celery_app import celery_app
from worker.config import get_settings
from worker.storage import upload_file, download_file
from worker.executor import execute_conversion
from worker.security.path_guard import TMP_DIR, sanitize_and_assert_tmp_path
from worker.security.mime_guard import assert_mime_type_matches
from api.models import User, Job, CreditLog

settings = get_settings()

sync_engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
SyncSession = sessionmaker(sync_engine)

logger = logging.getLogger("zenvort.worker")


def _get_ext_from_url(storage_key: str, fallback_format: str) -> str:
    filename = storage_key.split("/")[-1]
    _, ext = os.path.splitext(filename)
    if ext and len(ext) <= 10:
        return ext.lstrip(".")
    return fallback_format


def _cleanup(job_id: str) -> None:
    for f in glob.glob(f"{TMP_DIR}/{job_id}-*"):
        try:
            os.unlink(f)
        except OSError:
            pass


def _fire_webhook(user_id: str, job_id: str, status: str) -> None:
    with SyncSession() as db:
        user = db.query(User).filter(User.id == user_id).first()
    webhook_url = getattr(user, "webhook_url", None) if user else None
    if not webhook_url:
        return
    try:
        httpx.post(webhook_url, json={"jobId": job_id, "status": status}, timeout=5.0)
    except Exception as exc:
        logger.warning(f"[webhook] failed for user {user_id} job {job_id}: {exc}")


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    throws=(SoftTimeLimitExceeded,),
)
def process_job(self, job_id: str) -> dict:
    with SyncSession() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {"error": f"Job {job_id} not found"}

        input_url = job.input_url
        input_format = job.input_format
        output_format = job.output_format
        user_id = job.user_id

        job.status = "PROCESSING"
        db.commit()

    if input_format == output_format:
        with SyncSession() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            job.status = "FAILED"
            job.error = "Unrecoverable: input and output formats are identical"
            db.commit()
        _cleanup(job_id)
        return {"error": "unrecoverable"}

    print(f"[worker][{job_id}] Job received "
          f"{{input_format={input_format}, output_format={output_format}, user_id={user_id}}}")

    _, _, free = shutil.disk_usage(TMP_DIR)
    if free < 2 * (1024 ** 3):
        print(f"[worker][{job_id}] Disk space low ({free} bytes free) — retrying")
        raise self.retry(exc=Exception("Disk space low"), countdown=60)

    try:
        input_ext = _get_ext_from_url(input_url, input_format)
        local_input = f"{TMP_DIR}/{job_id}-input.{input_ext}"
        os.makedirs(TMP_DIR, exist_ok=True)

        download_file(input_url, local_input)
        sanitize_and_assert_tmp_path(local_input)

        if os.path.getsize(local_input) > 200 * (1024 ** 2):
            with SyncSession() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                job.status = "FAILED"
                job.error = "Input file exceeds 200MB limit"
                db.commit()
            _cleanup(job_id)
            return {"error": "unrecoverable"}

        with SyncSession() as db:
            cached = (
                db.query(Job)
                .filter(
                    Job.input_url == input_url,
                    Job.output_format == output_format,
                    Job.status == "DONE",
                )
                .first()
            )

        if cached and cached.output_url:
            with SyncSession() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                job.status = "DONE"
                job.output_url = cached.output_url
                job.converter_used = "cache"
                db.commit()
            _cleanup(job_id)
            if user_id:
                _fire_webhook(user_id, job_id, "DONE")
            return {"status": "DONE", "cached": True}

        local_output = f"{TMP_DIR}/{job_id}-output.{output_format}"
        print(f"[worker][{job_id}] Conversion started")

        result_conv = execute_conversion(
            job_id, local_input, local_output, input_format, output_format
        )
        converter_used = result_conv.get("converter_used", "unknown")

        print(f"[worker][{job_id}] Conversion done {{converter_used={converter_used}}}")

        output_size = os.path.getsize(local_output)
        if output_size > 500 * (1024 ** 2):
            with SyncSession() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                job.status = "FAILED"
                job.error = "Output file exceeds 500MB limit"
                db.commit()
            _cleanup(job_id)
            return {"error": "unrecoverable"}

        assert_mime_type_matches(local_output, output_format)

        output_key = f"outputs/{job_id}/output.{output_format}"
        upload_file(local_output, output_key, "application/octet-stream")

        if user_id:
            with SyncSession() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                user = db.query(User).filter(User.id == user_id).first()

                job.status = "DONE"
                job.output_url = output_key
                job.converter_used = converter_used
                job.updated_at = datetime.utcnow()

                if user:
                    if user.credits >= 1:
                        user.credits -= 1
                        credit_log = CreditLog(
                            id=str(uuid.uuid4()),
                            user_id=user_id,
                            amount=-1,
                            reason="conversion",
                            job_id=job_id,
                            created_at=datetime.utcnow(),
                        )
                        db.add(credit_log)
                    else:
                        logger.warning(f"[worker][{job_id}] User {user_id} has no credits — skipping deduction")

                db.commit()
        else:
            with SyncSession() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                job.status = "DONE"
                job.output_url = output_key
                job.converter_used = converter_used
                job.updated_at = datetime.utcnow()
                db.commit()

        if user_id:
            _fire_webhook(user_id, job_id, "DONE")

        return {"status": "DONE", "output_url": output_key}

    except SoftTimeLimitExceeded:
        with SyncSession() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            job.status = "FAILED"
            job.error = "Time limit exceeded"
            db.commit()
        raise

    except ValueError as exc:
        with SyncSession() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "FAILED"
                job.error = f"Invalid input: {exc}"
                db.commit()
        return {"error": str(exc)}

    except Exception as exc:
        error_str = str(exc)[:2000]
        print(f"[worker][{job_id}] Error: {error_str}")
        with SyncSession() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            job.status = "FAILED"
            job.error = error_str
            db.commit()
        raise self.retry(exc=exc, countdown=30)

    finally:
        _cleanup(job_id)