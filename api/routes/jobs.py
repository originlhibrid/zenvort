import re
import os
import time
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models import User, Job
from api.deps import get_current_user
from api.schemas import JobSchema, JobCreateResponse, JobListResponse
from api.config import get_settings
from api.storage import upload_file
from slowapi import Limiter
from slowapi.util import get_remote_address
from worker.routes import VALID_OUTPUT_FORMATS, VALID_INPUT_FORMATS

settings = get_settings()
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


def sanitize_filename(filename: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\.\-]", "_", filename)


@router.get("", response_model=JobListResponse)
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
        jobs=[JobSchema.model_validate(j) for j in jobs],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{job_id}", response_model=JobSchema)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.user_id and job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return JobSchema.model_validate(job)


@router.post("", response_model=JobCreateResponse, status_code=201)
@limiter.limit("10/hour")
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

    # Read and size-check the file
    contents = b""
    chunk_size = 1024 * 1024  # 1MB chunks
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        if len(contents) + len(chunk) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large")
        contents += chunk

    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    # Infer input format from filename
    filename = sanitize_filename(file.filename or "file")
    safe_name = re.sub(r"[^a-zA-Z0-9_\.\-]", "_", filename)
    input_format = safe_name.rsplit(".", 1)[-1].lower()

    if input_format not in VALID_INPUT_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported input format: {input_format}")

    if input_format == outputFormat:
        raise HTTPException(status_code=400, detail="Input and output formats must differ")

    # Save to /tmp for R2 upload
    import uuid
    job_id = str(uuid.uuid4())
    local_input_path = f"/tmp/zenvort/{job_id}-input.{input_format}"
    os.makedirs("/tmp/zenvort", exist_ok=True)
    with open(local_input_path, "wb") as f:
        f.write(contents)

    try:
        # Upload to R2
        storage_key = f"inputs/{job_id}/{safe_name}"
        input_url = upload_file(local_input_path, storage_key, "application/octet-stream")

        # Create job record
        job = Job(
            id=job_id,
            user_id=current_user.id,
            status="PENDING",
            input_url=input_url,
            input_format=input_format,
            output_format=outputFormat,
        )
        db.add(job)
        await db.commit()

        # Dispatch Celery task (lazy import to avoid worker dependency)
        from worker.tasks import process_job
        process_job.delay(job_id)

    finally:
        if os.path.exists(local_input_path):
            os.unlink(local_input_path)

    return JobCreateResponse(
        jobId=job_id,
        status="PENDING",
        message="Job queued successfully",
    )
