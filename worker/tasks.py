import glob
import logging
import os
import shutil
import httpx
import sqlite3
from datetime import datetime, timezone
from urllib.parse import urlparse
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from worker.celery_app import celery_app
from worker.config import get_settings
from worker.storage import upload_file, download_file, delete_file
from worker.executor import execute_conversion
from worker.security.path_guard import TMP_DIR, sanitize_and_assert_tmp_path
from worker.security.mime_guard import assert_mime_type_matches
from worker.utils import _sanitize_error

settings = get_settings()

DB_PATH = settings.DB_PATH

logger = logging.getLogger("zenvort.worker")


def _r2_download(key: str, local_path: str) -> None:
    """Download a file from R2 to a local path."""
    try:
        download_file(key, local_path)
    except Exception as e:
        raise RuntimeError(f"R2 download failed for key={key}: {e}") from e


def _r2_upload(local_path: str, key: str, content_type: str = "application/octet-stream") -> None:
    """Upload a local file to R2."""
    try:
        upload_file(local_path, key, content_type)
    except Exception as e:
        raise RuntimeError(f"R2 upload failed for key={key}: {e}") from e


def _r2_delete(key: str) -> None:
    """Delete a file from R2."""
    try:
        delete_file(key)
    except Exception as e:
        raise RuntimeError(f"R2 delete failed for key={key}: {e}") from e


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row
    return conn


def _get_ext_from_url(storage_key: str, fallback_format: str) -> str:
    filename = storage_key.split("/")[-1]
    _, ext = os.path.splitext(filename)
    if ext and len(ext) <= 10:
        return ext.lstrip(".")
    return fallback_format


def _cleanup_local(job_id: str) -> None:
    """Remove temp files from local disk."""
    for f in glob.glob(f"{TMP_DIR}/{job_id}-*"):
        try:
            os.unlink(f)
        except OSError:
            pass


def _delete_input_from_r2(job_id: str, input_url: str) -> None:
    """Delete the uploaded input file from R2 immediately after conversion."""
    try:
        key = input_url
        if input_url.startswith("http"):
            parsed = urlparse(input_url)
            path = parsed.path.lstrip("/")
            bucket = settings.R2_BUCKET_NAME
            if path.startswith(bucket + "/"):
                key = path[len(bucket) + 1:]
            else:
                key = path
        _r2_delete(key)
        logger.info(f"[worker][{job_id}] Input file deleted from R2")
    except Exception as e:
        logger.warning(f"[worker][{job_id}] Failed to delete input from R2: {e}")


def _fire_webhook(user_id: str, job_id: str, status: str) -> None:
    try:
        conn = _get_db()
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT webhook_url FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        webhook_url = dict(row)["webhook_url"] if row else None
        conn.close()
    except Exception:
        webhook_url = None

    if not webhook_url:
        return
    try:
        httpx.post(webhook_url, json={"jobId": job_id, "status": status}, timeout=5.0)
    except Exception as exc:
        logger.warning(f"[webhook] failed for user {user_id} job {job_id}: {exc}")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    throws=(SoftTimeLimitExceeded,),
)
def process_job(self, job_id: str) -> dict:
    conn = _get_db()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        conn.close()
        return {"error": f"Job {job_id} not found"}

    job = dict(row)
    input_url = job["input_url"]
    input_format = job["input_format"]
    output_format = job["output_format"]
    user_id = job["user_id"]

    conn.execute("UPDATE jobs SET status = 'processing' WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()

    if input_format == output_format:
        conn = _get_db()
        conn.execute(
            "UPDATE jobs SET status = 'failed', error = ? WHERE id = ?",
            ("Unrecoverable: input and output formats are identical", job_id),
        )
        conn.commit()
        conn.close()
        _cleanup_local(job_id)
        return {"error": "unrecoverable"}

    logger.info(f"[job:{job_id}] START fmt={input_format}→{output_format}")
    job_start = time.time()

    _, _, free = shutil.disk_usage(TMP_DIR)
    if free < 2 * (1024 ** 3):
        logger.warning(f"[worker][{job_id}] Disk space low ({free} bytes free) — retrying")
        raise self.retry(exc=Exception("Disk space low"), countdown=60)

    try:
        input_ext = _get_ext_from_url(input_url, input_format)
        local_input = f"{TMP_DIR}/{job_id}-input.{input_ext}"
        os.makedirs(TMP_DIR, exist_ok=True)

        _r2_download(input_url, local_input)
        sanitize_and_assert_tmp_path(local_input)

        if os.path.getsize(local_input) > 200 * (1024 ** 2):
            conn = _get_db()
            conn.execute(
                "UPDATE jobs SET status = 'failed', error = ? WHERE id = ?",
                (_sanitize_error("Input file exceeds 200MB limit", input_format, output_format), job_id),
            )
            conn.commit()
            conn.close()
            _cleanup_local(job_id)
            _delete_input_from_r2(job_id, input_url)
            return {"error": "unrecoverable"}

        # Cache check
        conn = _get_db()
        conn.row_factory = sqlite3.Row
        cached_row = conn.execute(
            """SELECT output_url FROM jobs
               WHERE input_url = ? AND output_format = ? AND status = 'done'""",
            (input_url, output_format),
        ).fetchone()
        conn.close()

        if cached_row and cached_row["output_url"]:
            output_key = cached_row["output_url"]
            conn = _get_db()
            conn.execute(
                "UPDATE jobs SET status = 'done', output_url = ?, converter_used = 'cache' WHERE id = ?",
                (output_key, job_id),
            )
            conn.commit()
            conn.close()
            _cleanup_local(job_id)
            _delete_input_from_r2(job_id, input_url)
            if user_id:
                _fire_webhook(user_id, job_id, "done")
            elapsed = time.time() - job_start
            logger.info(f"[job:{job_id}] DONE elapsed={elapsed:.2f}s (cached)")
            return {"status": "done", "cached": True}

        local_output = f"{TMP_DIR}/{job_id}-output.{output_format}"
        logger.info(f"[worker][{job_id}] Conversion started")

        result_conv = execute_conversion(
            job_id, local_input, local_output, input_format, output_format
        )
        converter_used = result_conv.get("converter_used", "unknown")

        logger.info(f"[worker][{job_id}] Conversion done {{converter_used={converter_used}}}")

        output_size = os.path.getsize(local_output)
        if output_size > 500 * (1024 ** 2):
            conn = _get_db()
            conn.execute(
                "UPDATE jobs SET status = 'failed', error = ? WHERE id = ?",
                (_sanitize_error("Output file exceeds 500MB limit", input_format, output_format), job_id),
            )
            conn.commit()
            conn.close()
            _cleanup_local(job_id)
            _delete_input_from_r2(job_id, input_url)
            return {"error": "unrecoverable"}

        assert_mime_type_matches(local_output, output_format)

        output_key = f"outputs/{job_id}/output.{output_format}"
        _r2_upload(local_output, output_key)

        now = _iso_now()
        conn = _get_db()
        conn.execute(
            "UPDATE jobs SET status = 'done', output_url = ?, converter_used = ?, updated_at = ? WHERE id = ?",
            (output_key, converter_used, now, job_id),
        )
        conn.commit()
        conn.close()

        _delete_input_from_r2(job_id, input_url)
        _cleanup_local(job_id)

        delete_output_file.apply_async(
            args=[output_key, job_id],
            countdown=1200,
        )
        logger.info(f"[worker][{job_id}] Output deletion scheduled in 20 minutes")

        if user_id:
            _fire_webhook(user_id, job_id, "done")

        elapsed = time.time() - job_start
        logger.info(f"[job:{job_id}] DONE elapsed={elapsed:.2f}s")
        return {"status": "done", "output_url": output_key}

    except SoftTimeLimitExceeded:
        conn = _get_db()
        conn.execute(
            "UPDATE jobs SET status = 'failed', error = ? WHERE id = ?",
            (_sanitize_error("Time limit exceeded", input_format, output_format), job_id),
        )
        conn.commit()
        conn.close()
        _cleanup_local(job_id)
        _delete_input_from_r2(job_id, input_url)
        raise

    except ValueError as exc:
        conn = _get_db()
        conn.execute(
            "UPDATE jobs SET status = 'failed', error = ? WHERE id = ?",
            (_sanitize_error(str(exc), input_format, output_format), job_id),
        )
        conn.commit()
        conn.close()
        _cleanup_local(job_id)
        _delete_input_from_r2(job_id, input_url)
        return {"error": str(exc)}

    except Exception as exc:
        logger.error(f"[worker][{job_id}] Conversion failed: {exc}", exc_info=True)
        conn = _get_db()
        conn.execute(
            "UPDATE jobs SET status = 'failed', error = ? WHERE id = ?",
            (_sanitize_error(str(exc), input_format, output_format), job_id),
        )
        conn.commit()
        conn.close()
        _cleanup_local(job_id)
        _delete_input_from_r2(job_id, input_url)
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="worker.tasks.delete_output_file", ignore_result=True)
def delete_output_file(output_key: str, job_id: str) -> None:
    """Deletes output file from R2 20 minutes after job completes."""
    try:
        _r2_delete(output_key)
        logger.info(f"[cleanup][{job_id}] Output file deleted from R2: {output_key}")
    except Exception as e:
        logger.warning(f"[cleanup][{job_id}] Failed to delete output from R2: {e}")


@celery_app.task(name="worker.tasks.wipe_r2_bucket", ignore_result=True)
def wipe_r2_bucket() -> None:
    """Wipes ALL objects from R2 bucket. Runs every 5 hours via Celery Beat."""
    from worker.storage import _get_s3_client, get_settings
    settings = get_settings()

    try:
        s3 = _get_s3_client()
        bucket = settings.R2_BUCKET_NAME

        paginator = s3.get_paginator('list_objects_v2')

        total_deleted = 0
        for page in paginator.paginate(Bucket=bucket):
            objects = page.get('Contents', [])
            if not objects:
                continue

            keys = [{'Key': obj['Key']} for obj in objects]
            s3.delete_objects(
                Bucket=bucket,
                Delete={'Objects': keys, 'Quiet': True}
            )
            total_deleted += len(keys)

        logger.info(f"[cleanup][wipe_r2_bucket] Deleted {total_deleted} objects from R2 bucket")
    except Exception as e:
        logger.error(f"[cleanup][wipe_r2_bucket] Failed to wipe R2 bucket: {e}")


# ── PDF multi-operation task ─────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    throws=(SoftTimeLimitExceeded,),
)
def process_pdf_job(self, job_id: str) -> dict:
    """Handle PDF operations that require multiple inputs or extra metadata.

    Reads operation details from the job's converter_used field (stored as
    '_pdfop:{"operation": ..., "input_keys": [...], ...}' JSON).
    Dispatches to pdf_tools.convert() with the appropriate kwargs.
    """
    import json
    import time as time_module

    conn = _get_db()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        conn.close()
        return {"error": f"Job {job_id} not found"}

    job = dict(row)
    user_id = job["user_id"]
    converter_meta = job.get("converter_used") or ""

    conn.execute("UPDATE jobs SET status = 'processing' WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()

    logger.info(f"[pdf_job:{job_id}] START")
    job_start = time.time()

    _, _, free = shutil.disk_usage(TMP_DIR)
    if free < 2 * (1024 ** 3):
        logger.warning(f"[pdf_job][{job_id}] Disk space low — retrying")
        raise self.retry(exc=Exception("Disk space low"), countdown=60)

    # Parse metadata JSON from converter_used field.
    op_marker = "_pdfop:"
    if not converter_meta.startswith(op_marker):
        logger.error(f"[pdf_job:{job_id}] Missing _pdfop metadata")
        return {"error": "Invalid job — no PDF operation metadata found"}

    try:
        metadata = json.loads(converter_meta[len(op_marker):])
    except json.JSONDecodeError as exc:
        logger.error(f"[pdf_job:{job_id}] Corrupt metadata: {exc}")
        return {"error": "Invalid job metadata"}

    operation = metadata.get("operation", "unknown")
    input_keys: list[str] = metadata.get("input_keys", [])

    os.makedirs(TMP_DIR, exist_ok=True)
    tmp_paths: list[str] = []

    try:
        # Download all input files from R2.
        for i, key in enumerate(input_keys):
            ext = _get_ext_from_url(key, "pdf")
            local = f"{TMP_DIR}/{job_id}-input-{i}.{ext}"
            tmp_paths.append(local)
            _r2_download(key, local)
            sanitize_and_assert_tmp_path(local)

        # Resolve operation → (output_format, pdf_tools kwargs).
        if operation == "merge":
            output_format = "pdf"
            pdf_kwargs = {"extra_inputs": tmp_paths[1:]}
        elif operation == "split":
            output_format = "pdf"
            sp = metadata.get("start_page", 1)
            ep = metadata.get("end_page", -1)
            pdf_kwargs = {"split_range": (sp, ep)}
        elif operation == "encrypt":
            output_format = "enc"
            pdf_kwargs = {"password": metadata.get("password", "")}
        elif operation == "decrypt":
            output_format = "dec"
            pdf_kwargs = {"password": metadata.get("password", "")}
        elif operation == "compress":
            output_format = "pdf"
            pdf_kwargs = {}
        elif operation == "pdfa":
            output_format = "pdfa"
            pdf_kwargs = {}
        else:
            logger.error(f"[pdf_job:{job_id}] Unknown operation: {operation}")
            return {"error": f"Unknown PDF operation: {operation}"}

        # Determine output extension.
        if output_format in ("enc", "dec"):
            out_ext = "pdf"
        else:
            out_ext = output_format

        local_output = f"{TMP_DIR}/{job_id}-output.{out_ext}"

        from worker.converters.pdf_tools import convert as pdf_tools_convert
        logger.info(f"[pdf_job:{job_id}] op={operation} {len(tmp_paths)} inputs")

        pdf_tools_convert(
            input_path=tmp_paths[0],
            output_path=local_output,
            input_format="pdf",
            output_format=output_format,
            **pdf_kwargs,
        )

        # Upload output to R2.
        content_type = "application/pdf"
        output_key = f"outputs/{job_id}/output.{out_ext}"
        _r2_upload(local_output, output_key, content_type)

        now = _iso_now()
        conn = _get_db()
        conn.execute(
            "UPDATE jobs SET status = 'done', output_url = ?, "
            "converter_used = ?, updated_at = ? WHERE id = ?",
            (output_key, f"pdf_tools.{operation}", now, job_id),
        )
        conn.commit()
        conn.close()

        # Delete all input keys from R2.
        for key in input_keys:
            _delete_input_from_r2(job_id, key)

        _cleanup_local(job_id)

        delete_output_file.apply_async(
            args=[output_key, job_id],
            countdown=1200,
        )

        if user_id:
            _fire_webhook(user_id, job_id, "done")

        elapsed = time.time() - job_start
        logger.info(f"[pdf_job:{job_id}] DONE op={operation} elapsed={elapsed:.2f}s")
        return {"status": "done", "output_url": output_key}

    except SoftTimeLimitExceeded:
        _update_failed(job_id, "Time limit exceeded", "pdf", "pdf")
        _cleanup_local(job_id)
        for key in input_keys:
            _delete_input_from_r2(job_id, key)
        raise

    except Exception as exc:
        logger.error(f"[pdf_job:{job_id}] Failed: {exc}", exc_info=True)
        _update_failed(job_id, str(exc), "pdf", "pdf")
        _cleanup_local(job_id)
        for key in input_keys:
            _delete_input_from_r2(job_id, key)
        raise self.retry(exc=exc, countdown=30)


def _update_failed(job_id: str, error: str, input_format: str, output_format: str) -> None:
    conn = _get_db()
    conn.execute(
        "UPDATE jobs SET status = 'failed', error = ?, updated_at = ? WHERE id = ?",
        (_sanitize_error(error, input_format, output_format), _iso_now(), job_id),
    )
    conn.commit()
    conn.close()


# ── Spreadsheet task ─────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    throws=(SoftTimeLimitExceeded,),
)
def process_spreadsheet_job(self, job_id: str) -> dict:
    """Handle spreadsheet conversions: xlsx↔csv/json/html.

    Reads output_format and sheet_name from the converter_used field
    (stored as '_spreadsheet:{"operation":..., "output_format":..., "sheet_name":...}').
    """
    import json
    import time as time_module

    conn = _get_db()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        conn.close()
        return {"error": f"Job {job_id} not found"}

    job = dict(row)
    user_id = job["user_id"]
    converter_meta = job.get("converter_used") or ""

    conn.execute("UPDATE jobs SET status = 'processing' WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()

    logger.info(f"[spreadsheet_job:{job_id}] START")
    job_start = time.time()

    _, _, free = shutil.disk_usage(TMP_DIR)
    if free < 2 * (1024 ** 3):
        logger.warning(f"[spreadsheet_job][{job_id}] Disk space low — retrying")
        raise self.retry(exc=Exception("Disk space low"), countdown=60)

    op_marker = "_spreadsheet:"
    if not converter_meta.startswith(op_marker):
        logger.error(f"[spreadsheet_job:{job_id}] Missing _spreadsheet metadata")
        return {"error": "Invalid job — no spreadsheet operation metadata found"}

    try:
        metadata = json.loads(converter_meta[len(op_marker):])
    except json.JSONDecodeError as exc:
        logger.error(f"[spreadsheet_job:{job_id}] Corrupt metadata: {exc}")
        return {"error": "Invalid job metadata"}

    output_format = metadata.get("output_format", "")
    sheet_name    = metadata.get("sheet_name")
    input_url     = job.get("input_url")
    input_format  = job.get("input_format", "xlsx")

    if not output_format:
        return {"error": "Missing output format in spreadsheet job metadata"}

    os.makedirs(TMP_DIR, exist_ok=True)

    try:
        # Download the single input file.
        input_ext = _get_ext_from_url(input_url, input_format)
        local_input = f"{TMP_DIR}/{job_id}-input.{input_ext}"
        _r2_download(input_url, local_input)
        sanitize_and_assert_tmp_path(local_input)

        # Validate input file exists.
        if os.path.getsize(local_input) == 0:
            raise ValueError("Input file is empty")

        # Output extension mapping.
        ext_map = {"csv": "csv", "json": "json", "html": "html", "xlsx": "xlsx"}
        out_ext = ext_map.get(output_format, output_format)
        local_output = f"{TMP_DIR}/{job_id}-output.{out_ext}"

        from worker.converters.spreadsheet import convert as spreadsheet_convert
        logger.info(
            f"[spreadsheet_job:{job_id}] "
            f"{input_format}→{output_format} sheet={sheet_name}"
        )

        spreadsheet_convert(
            input_path=local_input,
            output_path=local_output,
            input_format=input_format,
            output_format=output_format,
            sheet_name=sheet_name,
        )

        # Determine content type for upload.
        mime_map = {
            "csv":   "text/csv; charset=utf-8",
            "json":  "application/json",
            "html":  "text/html; charset=utf-8",
            "xlsx":  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        content_type = mime_map.get(output_format, "application/octet-stream")
        output_key = f"outputs/{job_id}/output.{out_ext}"
        _r2_upload(local_output, output_key, content_type)

        now = _iso_now()
        conn = _get_db()
        conn.execute(
            "UPDATE jobs SET status = 'done', output_url = ?, "
            "converter_used = 'spreadsheet.convert', updated_at = ? WHERE id = ?",
            (output_key, now, job_id),
        )
        conn.commit()
        conn.close()

        _delete_input_from_r2(job_id, input_url)
        _cleanup_local(job_id)

        delete_output_file.apply_async(
            args=[output_key, job_id],
            countdown=1200,
        )

        if user_id:
            _fire_webhook(user_id, job_id, "done")

        elapsed = time.time() - job_start
        logger.info(
            f"[spreadsheet_job:{job_id}] DONE "
            f"{input_format}→{output_format} elapsed={elapsed:.2f}s"
        )
        return {"status": "done", "output_url": output_key}

    except SoftTimeLimitExceeded:
        _update_failed(job_id, "Time limit exceeded", input_format, output_format)
        _cleanup_local(job_id)
        if input_url:
            _delete_input_from_r2(job_id, input_url)
        raise

    except Exception as exc:
        logger.error(f"[spreadsheet_job:{job_id}] Failed: {exc}", exc_info=True)
        _update_failed(job_id, str(exc), input_format, output_format)
        _cleanup_local(job_id)
        if input_url:
            _delete_input_from_r2(job_id, input_url)
        raise self.retry(exc=exc, countdown=30)
