from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form
from typing import Annotated

from app.auth import verify_api_key
from app.db import create_job, increment_usage
from app.response import abort
from app.utils.temp import new_job_id, save_upload
from app.utils.validation import validate_file_size, check_rate_limit
from app.worker import celery_app


router = APIRouter(prefix="/v1/media", tags=["media"])

AUDIO_FORMATS = {"mp3", "wav", "ogg", "flac"}
VIDEO_FORMATS = {"mp4", "avi", "mov", "webm"}
ALL_SUPPORTED = AUDIO_FORMATS | VIDEO_FORMATS


@router.post("/convert")
async def media_convert(
    file: Annotated[UploadFile, File(description="Audio or video file to convert")],
    to: Annotated[str, Form(description="Target format")],
    webhook_url: Annotated[str | None, Form(description="Webhook URL for completion notification")] = None,
    key: dict = Depends(verify_api_key),
):
    job_id = new_job_id()
    endpoint = "/v1/media/convert"
    file_size_bytes = 0

    await check_rate_limit(key)

    try:
        file_size_bytes = validate_file_size(file)

        input_ext = Path(file.filename or "file").suffix.lstrip(".").lower()
        output_format = to.lower()

        if input_ext not in ALL_SUPPORTED:
            abort(400, f"Unsupported input format: {input_ext}", "UNSUPPORTED_FORMAT", job_id)

        valid = False
        if input_ext in AUDIO_FORMATS and output_format in AUDIO_FORMATS:
            valid = True
        elif input_ext in VIDEO_FORMATS and output_format in (VIDEO_FORMATS | AUDIO_FORMATS | {"gif"}):
            valid = True

        if not valid:
            abort(400, f"Conversion {input_ext}->{output_format} not supported", "UNSUPPORTED_FORMAT", job_id)

        content = await file.read()
        input_path = save_upload(content, job_id, f"input.{input_ext}")

        await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
        celery_app.send_task(
            "tasks.process_media",
            args=[job_id, str(input_path), {
                "input_ext": input_ext,
                "output_format": output_format,
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
