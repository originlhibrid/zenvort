# api/routes/spreadsheet_jobs.py
# Endpoints for spreadsheet conversions: xlsx ↔ csv/json/html.
# xlsx→csv and xlsx→json accept an optional 'sheetName' query param
# to select a specific worksheet instead of the active sheet.

import re
import os
import json
import shutil
import tempfile
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Query
from typing import Annotated
import aiosqlite

from api.database import DB_PATH
from api.deps import get_current_user
from api.schemas import JobCreateResponse
from api.storage import upload_file
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024    # 50MB — spreadsheets are small
MAX_CONVERSIONS_PER_DAY = 50


def sanitize_filename(filename: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\.\-]", "_", filename)


def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


async def _submit_spreadsheet_job(
    file: UploadFile,
    output_format: str,
    current_user,
    metadata: dict | None = None,
) -> JobCreateResponse:
    user_id = current_user["id"]

    # Daily limit check.
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
        if row and row["cnt"] >= MAX_CONVERSIONS_PER_DAY:
            raise HTTPException(
                status_code=429,
                detail=f"Daily conversion limit reached ({MAX_CONVERSIONS_PER_DAY}/day). Resets at midnight UTC.",
            )

    job_id = str(uuid.uuid4())
    now = _iso_now()
    tmp_path = None

    try:
        filename = sanitize_filename(file.filename or f"input.{output_format if output_format in ('xlsx', 'csv', 'json') else 'xlsx'}")
        safe_name = re.sub(r"[^a-zA-Z0-9_\.\-]", "_", filename)

        # Validate extensions match expected input.
        input_ext = "xlsx" if output_format not in ("xlsx", "csv", "json") else (
            "csv" if output_format == "xlsx" else "json" if output_format == "xlsx" else "xlsx"
        )
        if not safe_name.lower().endswith(f".{input_ext}"):
            raise HTTPException(
                status_code=400,
                detail=f"Input file must have .{input_ext} extension",
            )

        tmp_fd = tempfile.NamedTemporaryFile(delete=False, suffix=f".{input_ext}")
        tmp_path = tmp_fd.name
        shutil.copyfileobj(file.file, tmp_fd)
        tmp_fd.close()

        size = os.path.getsize(tmp_path)
        if size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File exceeds {MAX_FILE_SIZE // 1024 // 1024}MB limit")
        if size == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        # Determine input format from filename extension.
        if safe_name.lower().endswith(".csv"):
            input_format = "csv"
        elif safe_name.lower().endswith(".json"):
            input_format = "json"
        else:
            input_format = "xlsx"

        storage_key = f"inputs/{job_id}/{safe_name}"
        upload_file(tmp_path, storage_key, "application/octet-stream")

        # Encode operation metadata in converter_used field.
        job_metadata = {
            "operation": "spreadsheet",
            "output_format": output_format,
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
                    storage_key,
                    input_format,
                    output_format,
                    now,
                    now,
                    f"_spreadsheet:{json.dumps(job_metadata)}",
                ),
            )
            await db.commit()

        from api.celery_client import celery_app
        celery_app.send_task("worker.tasks.process_spreadsheet_job", args=[job_id])

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return JobCreateResponse(
        jobId=job_id,
        status="PENDING",
        message=f"Spreadsheet conversion queued",
    )


# ── xlsx → csv ───────────────────────────────────────────────────────────────

@router.post("/xlsx-csv", response_model=JobCreateResponse, status_code=201)
@limiter.limit("100/hour")
async def xlsx_to_csv(
    request: Request,
    file: Annotated[UploadFile, File(description="XLSX file to convert")],
    sheet_name: Annotated[str | None, Query(description="Sheet name to convert (default: active sheet)")] = None,
    current_user=Depends(get_current_user),
):
    return await _submit_spreadsheet_job(
        file, "csv", current_user,
        metadata={"sheet_name": sheet_name} if sheet_name else None,
    )


# ── xlsx → json ──────────────────────────────────────────────────────────────

@router.post("/xlsx-json", response_model=JobCreateResponse, status_code=201)
@limiter.limit("100/hour")
async def xlsx_to_json(
    request: Request,
    file: Annotated[UploadFile, File(description="XLSX file to convert")],
    sheet_name: Annotated[str | None, Query(description="Sheet name to convert (default: active sheet)")] = None,
    current_user=Depends(get_current_user),
):
    return await _submit_spreadsheet_job(
        file, "json", current_user,
        metadata={"sheet_name": sheet_name} if sheet_name else None,
    )


# ── xlsx → html ───────────────────────────────────────────────────────────────

@router.post("/xlsx-html", response_model=JobCreateResponse, status_code=201)
@limiter.limit("100/hour")
async def xlsx_to_html(
    request: Request,
    file: Annotated[UploadFile, File(description="XLSX file to convert")],
    current_user=Depends(get_current_user),
):
    return await _submit_spreadsheet_job(file, "html", current_user)


# ── csv → xlsx ───────────────────────────────────────────────────────────────

@router.post("/csv-xlsx", response_model=JobCreateResponse, status_code=201)
@limiter.limit("100/hour")
async def csv_to_xlsx(
    request: Request,
    file: Annotated[UploadFile, File(description="CSV file to convert")],
    current_user=Depends(get_current_user),
):
    return await _submit_spreadsheet_job(file, "xlsx", current_user)


# ── json → xlsx ───────────────────────────────────────────────────────────────

@router.post("/json-xlsx", response_model=JobCreateResponse, status_code=201)
@limiter.limit("100/hour")
async def json_to_xlsx(
    request: Request,
    file: Annotated[UploadFile, File(description="JSON file to convert (array of objects)")],
    current_user=Depends(get_current_user),
):
    return await _submit_spreadsheet_job(file, "xlsx", current_user)