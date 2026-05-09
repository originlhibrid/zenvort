from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form
from typing import Annotated

from app.auth import verify_api_key
from app.db import create_job, increment_usage
from app.response import abort
from app.utils.temp import new_job_id, save_upload
from app.utils.validation import validate_file_size, check_rate_limit
from app.worker import celery_app


router = APIRouter(prefix="/v1/image", tags=["image"])

SUPPORTED_INPUTS = {"jpg", "jpeg", "png", "webp", "avif", "bmp", "tiff", "gif", "svg"}


@router.post("/convert")
async def image_convert(
    file: Annotated[UploadFile, File(description="Image file to convert")],
    to: Annotated[str, Form(description="Target format")],
    quality: Annotated[int, Form(description="Quality 1-100")] = 85,
    webhook_url: Annotated[str | None, Form(description="Webhook URL for completion notification")] = None,
    key: dict = Depends(verify_api_key),
):
    job_id = new_job_id()
    endpoint = "/v1/image/convert"
    file_size_bytes = 0

    await check_rate_limit(key)

    try:
        file_size_bytes = validate_file_size(file)

        input_ext = Path(file.filename or "file").suffix.lstrip(".").lower()
        if input_ext not in SUPPORTED_INPUTS:
            abort(400, f"Unsupported input format: {input_ext}", "UNSUPPORTED_FORMAT", job_id)

        output_format = to.lower()
        if output_format == "svg":
            abort(400, "SVG output not supported", "UNSUPPORTED_FORMAT", job_id)

        if not 1 <= quality <= 100:
            abort(400, "quality must be between 1 and 100", "INVALID_INPUT", job_id)

        content = await file.read()
        input_path = save_upload(content, job_id, f"input.{input_ext}")

        await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
        celery_app.send_task(
            "tasks.process_image",
            args=[job_id, "convert", str(input_path), {
                "input_ext": input_ext,
                "output_format": output_format,
                "quality": quality,
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


@router.post("/resize")
async def image_resize(
    file: Annotated[UploadFile, File(description="Image file to resize")],
    width: Annotated[int | None, Form(description="Target width")] = None,
    height: Annotated[int | None, Form(description="Target height")] = None,
    maintain_aspect: Annotated[bool, Form(description="Maintain aspect ratio")] = True,
    webhook_url: Annotated[str | None, Form(description="Webhook URL for completion notification")] = None,
    key: dict = Depends(verify_api_key),
):
    job_id = new_job_id()
    endpoint = "/v1/image/resize"
    file_size_bytes = 0

    await check_rate_limit(key)

    try:
        file_size_bytes = validate_file_size(file)

        if width is None and height is None:
            abort(400, "At least one of width or height required", "INVALID_INPUT", job_id)

        input_ext = Path(file.filename or "file").suffix.lstrip(".").lower()
        if input_ext not in {"jpg", "jpeg", "png", "webp", "avif", "bmp", "tiff", "gif"}:
            abort(400, f"Unsupported input format: {input_ext}", "UNSUPPORTED_FORMAT", job_id)

        content = await file.read()
        input_path = save_upload(content, job_id, f"input.{input_ext}")

        await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
        celery_app.send_task(
            "tasks.process_image",
            args=[job_id, "resize", str(input_path), {
                "input_ext": input_ext,
                "width": width,
                "height": height,
                "maintain_aspect": maintain_aspect,
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
