# api/routes/pdf_jobs.py
# Special job endpoints for multi-input PDF operations: merge, split,
# compress, PDF/A conversion, encrypt, and decrypt.
#
# All dispatch the Celery task worker.tasks.process_pdf_job, which reads
# operation details from the job's converter_used field (stored as
# '_pdfop:{...}' JSON).  The pdf_tools converter receives extra_inputs
# and split_range kwargs as needed.

import json
import re
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from typing import Annotated
import aiosqlite

from api.database import DB_PATH
from api.deps import get_current_user, get_optional_user
from api.schemas import JobCreateResponse
from api.storage import upload_file
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

MAX_FILE_SIZE = 100 * 1024 * 1024   # 100MB per file
MAX_MERGE_FILES = 20                 # max PDFs per merge operation
MAX_CONVERSIONS_PER_DAY = 50


def sanitize_filename(filename: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\.\-]", "_", filename)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _raise_daily_limit() -> None:
    raise HTTPException(
        status_code=429,
        detail=f"Daily conversion limit reached ({MAX_CONVERSIONS_PER_DAY}/day). Resets at midnight UTC.",
    )


async def _submit_pdf_job(
    files: list[UploadFile],
    output_format: str,
    current_user: dict | None,
    operation: str,
    metadata: dict | None = None,
) -> JobCreateResponse:
    """Shared job-submission logic for all PDF operations.

    Writes files to temp, uploads to R2, records job in DB with
    metadata JSON in the converter_used field, then dispatches
    the Celery task.
    """
    user_id = current_user["id"] if current_user else None

    # Daily limit check.
    if user_id:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT COUNT(*) as cnt FROM jobs
                   WHERE user_id = ?
                   AND date(created_at) = date('now', 'utc')
                   AND status = 'done'""",
                (user_id,),
            )
            row = await cursor.fetchone()
            today = row["cnt"] if row else 0
        if today >= MAX_CONVERSIONS_PER_DAY:
            _raise_daily_limit()

    job_id = str(uuid.uuid4())
    now = _iso_now()
    tmp_paths: list[str] = []

    try:
        storage_keys: list[str] = []
        for i, file in enumerate(files):
            filename = sanitize_filename(file.filename or f"file_{i}.pdf")
            safe_name = re.sub(r"[^a-zA-Z0-9_\.\-]", "_", filename)

            if not safe_name.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail="All input files must be PDFs")

            tmp_fd = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp_paths.append(tmp_fd.name)
            shutil.copyfileobj(file.file, tmp_fd)
            tmp_fd.close()

            size = os.path.getsize(tmp_fd.name)
            if size > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail=f"File '{safe_name}' exceeds 100MB limit")
            if size == 0:
                raise HTTPException(status_code=400, detail=f"File '{safe_name}' is empty")

            storage_key = f"inputs/{job_id}/{i}_{safe_name}"
            upload_file(tmp_fd.name, storage_key, "application/pdf")
            storage_keys.append(storage_key)

        # Encode full operation metadata as JSON in converter_used field.
        # worker.tasks.process_pdf_job parses this back out.
        job_metadata = {
            "operation": operation,
            "input_keys": storage_keys,
            **(metadata or {}),
        }

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO jobs
                   (id, user_id, status, input_url, input_format, output_format,
                    created_at, updated_at, converter_used)
                   VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, ?)""",
                (
                    job_id,
                    user_id,
                    storage_keys[0] if storage_keys else None,
                    "pdf",
                    output_format,
                    now,
                    now,
                    f"_pdfop:{json.dumps(job_metadata)}",
                ),
            )
            await db.commit()

        from api.celery_client import celery_app
        celery_app.send_task("worker.tasks.process_pdf_job", args=[job_id])

    finally:
        for p in tmp_paths:
            if os.path.exists(p):
                os.unlink(p)

    return JobCreateResponse(
        jobId=job_id,
        status="PENDING",
        message=f"PDF {operation} job queued successfully",
    )


# ── Merge ─────────────────────────────────────────────────────────────────────

@router.post("/merge", response_model=JobCreateResponse, status_code=201)
@limiter.limit("100/hour")
async def pdf_merge(
    request: Request,
    files: Annotated[list[UploadFile], File(description="2–20 PDF files to merge, in order")],
    current_user: dict = Depends(get_current_user),
):
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="At least 2 PDF files required to merge")
    if len(files) > MAX_MERGE_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_MERGE_FILES} files per merge")

    return await _submit_pdf_job(files, "pdf", current_user, "merge")


# ── Split ─────────────────────────────────────────────────────────────────────

@router.post("/split", response_model=JobCreateResponse, status_code=201)
@limiter.limit("100/hour")
async def pdf_split(
    request: Request,
    file: Annotated[UploadFile, File(description="Single PDF file to split")],
    start_page: Annotated[int, Form(description="First page to include (1-indexed)")] = 1,
    end_page: Annotated[int, Form(description="Last page to include (-1 for last page)")] = -1,
    current_user: dict = Depends(get_current_user),
):
    filename = sanitize_filename(file.filename or "file.pdf")
    safe_name = re.sub(r"[^a-zA-Z0-9_\.\-]", "_", filename)
    if not safe_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Input file must be a PDF")

    return await _submit_pdf_job(
        [file],
        "pdf",
        current_user,
        "split",
        metadata={"start_page": start_page, "end_page": end_page},
    )


# ── Encrypt / Decrypt ─────────────────────────────────────────────────────────

@router.post("/encrypt", response_model=JobCreateResponse, status_code=201)
@limiter.limit("100/hour")
async def pdf_encrypt(
    request: Request,
    file: Annotated[UploadFile, File(description="PDF file to encrypt")],
    password: Annotated[str, Form(min_length=4, max_length=64, description="Encryption password (AES-256)")],
    current_user: dict = Depends(get_current_user),
):
    return await _submit_pdf_job(
        [file], "enc", current_user, "encrypt",
        metadata={"password": password},
    )


@router.post("/decrypt", response_model=JobCreateResponse, status_code=201)
@limiter.limit("100/hour")
async def pdf_decrypt(
    request: Request,
    file: Annotated[UploadFile, File(description="Encrypted PDF file to decrypt")],
    password: Annotated[str, Form(min_length=4, max_length=64, description="PDF user password")],
    current_user: dict = Depends(get_current_user),
):
    return await _submit_pdf_job(
        [file], "dec", current_user, "decrypt",
        metadata={"password": password},
    )


# ── Compress / PDF-A ─────────────────────────────────────────────────────────

@router.post("/compress", response_model=JobCreateResponse, status_code=201)
@limiter.limit("100/hour")
async def pdf_compress(
    request: Request,
    file: Annotated[UploadFile, File(description="PDF file to compress")],
    current_user: dict = Depends(get_current_user),
):
    return await _submit_pdf_job([file], "pdf", current_user, "compress")


@router.post("/pdfa", response_model=JobCreateResponse, status_code=201)
@limiter.limit("100/hour")
async def pdf_to_pdfa(
    request: Request,
    file: Annotated[UploadFile, File(description="PDF file to convert to PDF/A archival format")],
    current_user: dict = Depends(get_current_user),
):
    return await _submit_pdf_job([file], "pdfa", current_user, "pdfa")