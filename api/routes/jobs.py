import re
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
import aiosqlite

from api.database import DB_PATH, get_db
from api.deps import get_current_user, get_optional_user
from api.schemas import JobSchema, JobCreateResponse, JobListResponse
from api.storage import upload_file, generate_download_url
from worker.routes import VALID_INPUT_FORMATS, VALID_OUTPUT_FORMATS
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


def sanitize_filename(filename: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\.\-]", "_", filename)


def _get_signed_url(key: str) -> str:
    """Generate a presigned download URL for an R2 storage key."""
    return generate_download_url(key)


def _expires_at(updated_at: str) -> str:
    """Calculate expiry timestamp: 20 minutes after the given timestamp."""
    try:
        updated = datetime.fromisoformat(updated_at)
    except Exception:
        updated = datetime.now(timezone.utc)
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return (updated + timedelta(minutes=20)).isoformat()


def _sign_job_urls(job: dict) -> dict:
    d = dict(job)
    d["inputUrl"] = _get_signed_url(d["input_url"]) if d.get("input_url") else None
    d["outputUrl"] = _get_signed_url(d["output_url"]) if d.get("output_url") else None
    return d


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("", response_model=JobListResponse)
@limiter.limit("100/minute")
async def list_jobs(
    request: Request,
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    offset = (page - 1) * limit

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute(
            "SELECT COUNT(*) FROM jobs WHERE user_id = ?", (current_user["id"],)
        ) as cur:
            row = await cur.fetchone()
            total = row[0] if row else 0

        async with db.execute(
            """SELECT * FROM jobs WHERE user_id = ?
               ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (current_user["id"], limit, offset),
        ) as cur:
            rows = await cur.fetchall()
            jobs = [dict(r) for r in rows]

    signed_jobs = [_sign_job_urls(j) for j in jobs]
    job_schemas = [JobSchema(**_fix_job_schema(j)) for j in signed_jobs]

    return JobListResponse(
        jobs=job_schemas,
        total=total,
        page=page,
        limit=limit,
    )


def _fix_job_schema(j: dict) -> dict:
    """Map raw dict fields to JobSchema field names."""
    return {
        "id": j["id"],
        "status": j["status"],
        "inputUrl": j.get("inputUrl"),
        "outputUrl": j.get("outputUrl"),
        "inputFormat": j.get("input_format"),
        "outputFormat": j.get("output_format"),
        "error": j.get("error"),
        "converterUsed": j.get("converter_used"),
        "createdAt": j.get("created_at"),
        "updatedAt": j.get("updated_at"),
    }


@router.get("/{job_id}", response_model=JobSchema)
@limiter.limit("100/minute")
async def get_job(
    request: Request,
    job_id: str,
    current_user: dict | None = Depends(get_optional_user),
):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM jobs WHERE id = ?", (job_id,)
        ) as cur:
            row = await cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    job = dict(row)

    if job["user_id"] is not None:
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        if current_user["id"] != job["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

    signed = _sign_job_urls(job)

    if job["status"] == "done" and job.get("output_url"):
        updated_str = job.get("updated_at") or job.get("created_at") or _iso_now()
        signed["expiresAt"] = _expires_at(updated_str)

    return JobSchema(**_fix_job_schema(signed))


@router.post("", response_model=JobCreateResponse, status_code=201)
@limiter.limit("100/hour")
async def create_job(
    request: Request,
    file: UploadFile = File(...),
    outputFormat: str = Form(...),
    current_user: dict | None = Depends(get_optional_user),
):
    MAX_CONVERSIONS_PER_DAY = 50

    if current_user:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT COUNT(*) as cnt FROM jobs
                   WHERE user_id = ?
                   AND date(created_at) = date('now', 'utc')
                   AND status = 'done'""",
                (current_user["id"],),
            )
            row = await cursor.fetchone()
            today = row["cnt"] if row else 0
        if today >= MAX_CONVERSIONS_PER_DAY:
            raise HTTPException(
                status_code=429,
                detail=f"Daily conversion limit reached ({MAX_CONVERSIONS_PER_DAY}/day). Resets at midnight UTC.",
            )

    if outputFormat not in VALID_OUTPUT_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported output format: {outputFormat}")

    filename = sanitize_filename(file.filename or "file")
    safe_name = re.sub(r"[^a-zA-Z0-9_\.\-]", "_", filename)

    if "." not in safe_name:
        raise HTTPException(status_code=400, detail="File must have a detectable extension")

    input_format = safe_name.rsplit(".", 1)[-1].lower()

    if input_format not in VALID_INPUT_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported input format: {input_format}")

    if input_format == outputFormat:
        raise HTTPException(status_code=400, detail="Input and output formats must differ")

    job_id = str(uuid.uuid4())
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        if os.path.getsize(tmp_path) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large")
        if os.path.getsize(tmp_path) == 0:
            raise HTTPException(status_code=400, detail="Empty file")

        storage_key = f"inputs/{job_id}/{safe_name}"
        now = _iso_now()

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO jobs
                   (id, user_id, status, input_url, input_format, output_format, created_at, updated_at)
                   VALUES (?, ?, 'pending', ?, ?, ?, ?, ?)""",
                (job_id, current_user["id"] if current_user else None, storage_key,
                 input_format, outputFormat, now, now),
            )
            await db.commit()

        try:
            upload_file(tmp_path, storage_key, "application/octet-stream")
        except Exception:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
                await db.commit()
            raise HTTPException(status_code=500, detail="File upload failed")

        from api.celery_client import celery_app
        celery_app.send_task("worker.tasks.process_job", args=[job_id])

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return JobCreateResponse(
        jobId=job_id,
        status="PENDING",
        message="Job queued successfully",
    )
