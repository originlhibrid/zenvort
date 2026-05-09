from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Annotated

from app.auth import verify_api_key
from app.config import get_settings
from app.db import create_job, increment_usage
from app.response import error_response
from app.utils.temp import new_job_id, save_upload
from app.utils.validation import validate_file_size, check_rate_limit
from app.worker import celery_app


router = APIRouter(prefix="/v1", tags=["convert"])
settings = get_settings()

SUPPORTED_FORMATS = {
    "docx", "pptx", "odt", "xlsx", "ods", "odp",
    "md", "html", "rtf", "txt",
    "jpg", "jpeg", "png", "webp", "avif", "bmp", "tiff", "gif", "svg",
    "pdf",
    "mp3", "wav", "ogg", "flac",
    "mp4", "avi", "mov", "webm",
}


@router.post("/convert")
async def convert(
    file: Annotated[UploadFile, File(description="File to convert")],
    to: Annotated[str, Form(description="Target format")],
    webhook_url: Annotated[str | None, Form(description="Webhook URL for completion notification")] = None,
    key: dict = Depends(verify_api_key),
):
    job_id = new_job_id()
    endpoint = "/v1/convert"
    file_size_bytes = 0

    await check_rate_limit(key)

    try:
        input_format = Path(file.filename or "file").suffix.lstrip(".").lower()
        if input_format not in SUPPORTED_FORMATS:
            detail = error_response(
                f"Format {input_format} not supported",
                "UNSUPPORTED_FORMAT",
                job_id,
            )
            detail["supported"] = sorted(SUPPORTED_FORMATS)
            raise HTTPException(status_code=400, detail=detail)

        file_size_bytes = validate_file_size(file)
        content = await file.read()
        input_path = save_upload(content, job_id, f"input.{input_format}")
        output_format = to.lower()

        await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
        celery_app.send_task(
            "tasks.process_convert",
            args=[job_id, str(input_path), {
                "input_format": input_format,
                "output_format": output_format,
                "output_ext": output_format,
                "_webhook_url": webhook_url,
            }],
        )

        await increment_usage(key["key_id"], endpoint, job_id, file_size_bytes, 200)
        return {"job_id": job_id, "status": "queued", "poll_url": f"/v1/jobs/{job_id}"}
    except HTTPException as e:
        await increment_usage(key["key_id"], endpoint, job_id, file_size_bytes, e.status_code)
        raise
    except Exception:
        await increment_usage(key["key_id"], endpoint, job_id, file_size_bytes, 500)
        raise
