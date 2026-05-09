from fastapi import APIRouter, Depends, UploadFile, File, Form
from typing import Annotated

from app.auth import verify_api_key
from app.db import create_job, increment_usage
from app.response import abort
from app.utils.temp import new_job_id, save_upload
from app.utils.validation import validate_file_size, check_rate_limit
from app.worker import celery_app


router = APIRouter(prefix="/v1", tags=["ocr"])

SUPPORTED_INPUTS = {"jpg", "jpeg", "png", "webp", "bmp", "tiff", "gif", "avif", "pdf"}


@router.post("/ocr")
async def ocr(
    file: Annotated[UploadFile, File(description="Image or PDF file for OCR")],
    language: Annotated[str, Form(description="Language(s) e.g. eng, eng+hin")] = "eng",
    webhook_url: Annotated[str | None, Form(description="Webhook URL for completion notification")] = None,
    key: dict = Depends(verify_api_key),
):
    job_id = new_job_id()
    endpoint = "/v1/ocr"
    file_size_bytes = 0

    await check_rate_limit(key)

    try:
        file_size_bytes = validate_file_size(file)

        input_ext = file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
        if input_ext not in SUPPORTED_INPUTS:
            abort(400, f"Unsupported file format: {input_ext}", "UNSUPPORTED_FORMAT", job_id)

        content = await file.read()
        input_path = save_upload(content, job_id, f"input.{input_ext}")

        await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
        celery_app.send_task(
            "tasks.process_ocr",
            args=[job_id, str(input_path), {
                "language": language,
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
