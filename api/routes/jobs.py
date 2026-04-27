import re
import os
import shutil
import tempfile
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models import User, Job
from api.deps import get_current_user
from api.schemas import JobSchema, JobCreateResponse, JobListResponse
from api.config import get_settings
from api.storage import upload_file, generate_download_url
from slowapi import Limiter
from slowapi.util import get_remote_address

settings = get_settings()
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

from worker.routes import VALID_INPUT_FORMATS, VALID_OUTPUT_FORMATS


def sanitize_filename(filename: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\.\-]", "_", filename)


def _sign_url_for_job(job: JobSchema) -> dict:
    d = job.model_dump()
    if d.get("input_url"):
        d["input_url"] = generate_download_url(d["input_url"])
    if d.get("output_url"):
        d["output_url"] = generate_download_url(d["output_url"])
    return d


@router.get("", response_model=JobListResponse)
@limiter.limit("100/minute")
async def list_jobs(
    request: Request,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit

    count_result = await db.execute(
        select(func.count()).select_from(Job).where(Job.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Job)
        .where(Job.user_id == current_user.id)
        .order_by(Job.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    jobs = result.scalars().all()

    return JobListResponse(
        jobs=[_sign_url_for_job(JobSchema.model_validate(j)) for j in jobs],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{job_id}", response_model=JobSchema)
@limiter.limit("100/minute")
async def get_job(
    request: Request,
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.user_id is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    job_data = JobSchema.model_validate(job).model_dump()
    if job_data.get("input_url"):
        job_data["input_url"] = generate_download_url(job_data["input_url"])
    if job_data.get("output_url"):
        job_data["output_url"] = generate_download_url(job_data["output_url"])
    return job_data


@router.post("", response_model=JobCreateResponse, status_code=201)
@limiter.limit("100/hour")
async def create_job(
    request: Request,
    file: UploadFile = File(...),
    outputFormat: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.credits < 1:
        raise HTTPException(status_code=402, detail="Insufficient credits")

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
        job = Job(
            id=job_id,
            user_id=current_user.id,
            status="PENDING",
            input_url=storage_key,
            input_format=input_format,
            output_format=outputFormat,
        )
        db.add(job)
        await db.commit()

        try:
            upload_file(tmp_path, storage_key, "application/octet-stream")
        except Exception:
            await db.delete(job)
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