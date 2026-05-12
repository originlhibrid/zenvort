import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Annotated

from app.auth import verify_api_key
from app.config import get_settings
from app.db import create_job, check_and_increment_usage, update_job
from app.response import abort
from app.utils.temp import new_job_id, save_upload
from app.utils.validation import validate_file_size
from app.worker import celery_app
from app.handlers.pdf_ops import read_metadata, get_bookmarks


router = APIRouter(prefix="/v1/pdf", tags=["pdf"])
settings = get_settings()


def _validate_pdf(file: UploadFile) -> tuple[str, int]:
    size = validate_file_size(file)
    ext = Path(file.filename or "file.pdf").suffix.lstrip(".").lower()
    if ext != "pdf":
        abort(400, "Input file must be a PDF", "INVALID_FORMAT")
    return ext, size


@router.post("/merge")
async def pdf_merge(
    files: Annotated[list[UploadFile], File(description="2-20 PDF files to merge, in order")],
    webhook_url: Annotated[str | None, Form(description="Webhook URL for completion notification")] = None,
    key: dict = Depends(verify_api_key),
):
    job_id = new_job_id()
    endpoint = "/v1/pdf/merge"
    total_bytes = 0
    tier = key.get("tier", "free")

    try:
        if len(files) < 2:
            abort(400, "At least 2 PDF files required", "INVALID_INPUT", job_id)
        if len(files) > 20:
            abort(400, "Maximum 20 files per merge", "INVALID_INPUT", job_id)

        for f in files:
            _, s = _validate_pdf(f)
            total_bytes += s

        input_paths = []
        for i, f in enumerate(files):
            content = await f.read()
            p = save_upload(content, job_id, f"input_{i}.pdf")
            input_paths.append(str(p))

        await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
        celery_app.send_task(
            "tasks.process_pdf",
            args=[job_id, "merge", input_paths[0], {
                "input_paths": input_paths,
                "output_ext": "pdf",
                "_webhook_url": webhook_url,
            }],
        )

        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, total_bytes, 200)
        return {"job_id": job_id, "status": "queued", "poll_url": f"/v1/jobs/{job_id}"}
    except HTTPException as e:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, total_bytes, e.status_code)
        raise
    except Exception:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, total_bytes, 500)
        raise


@router.post("/split")
async def pdf_split(
    file: Annotated[UploadFile, File(description="PDF file to split")],
    pages: Annotated[str, Form(description="Page ranges e.g. 1-3,5,7-9")],
    webhook_url: Annotated[str | None, Form(description="Webhook URL for completion notification")] = None,
    key: dict = Depends(verify_api_key),
):
    job_id = new_job_id()
    endpoint = "/v1/pdf/split"
    file_size_bytes = 0
    tier = key.get("tier", "free")

    try:
        _, file_size_bytes = _validate_pdf(file)
        content = await file.read()
        input_path = save_upload(content, job_id, "input.pdf")

        await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
        celery_app.send_task(
            "tasks.process_pdf",
            args=[job_id, "split", str(input_path), {
                "pages": pages,
                "output_ext": "pdf",
                "_webhook_url": webhook_url,
            }],
        )

        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 200)
        return {"job_id": job_id, "status": "queued", "poll_url": f"/v1/jobs/{job_id}"}
    except HTTPException as e:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, e.status_code)
        raise
    except Exception:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 500)
        raise


@router.post("/rotate")
async def pdf_rotate(
    file: Annotated[UploadFile, File(description="PDF file to rotate")],
    degrees: Annotated[int, Form(description="Rotation: 90, 180, or 270")],
    pages: Annotated[str | None, Form(description="Pages to rotate e.g. 1-3 (default all)")] = None,
    webhook_url: Annotated[str | None, Form(description="Webhook URL for completion notification")] = None,
    key: dict = Depends(verify_api_key),
):
    job_id = new_job_id()
    endpoint = "/v1/pdf/rotate"
    file_size_bytes = 0
    tier = key.get("tier", "free")

    try:
        _, file_size_bytes = _validate_pdf(file)
        if degrees not in (90, 180, 270):
            abort(400, "degrees must be 90, 180, or 270", "INVALID_INPUT", job_id)

        content = await file.read()
        input_path = save_upload(content, job_id, "input.pdf")

        await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
        celery_app.send_task(
            "tasks.process_pdf",
            args=[job_id, "rotate", str(input_path), {
                "degrees": degrees,
                "pages": pages,
                "output_ext": "pdf",
                "_webhook_url": webhook_url,
            }],
        )

        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 200)
        return {"job_id": job_id, "status": "queued", "poll_url": f"/v1/jobs/{job_id}"}
    except HTTPException as e:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, e.status_code)
        raise
    except Exception:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 500)
        raise


@router.post("/watermark")
async def pdf_watermark(
    file: Annotated[UploadFile, File(description="PDF file")],
    text: Annotated[str, Form(description="Watermark text")],
    opacity: Annotated[float, Form(description="Opacity 0.0-1.0")] = 0.3,
    font_size: Annotated[int, Form(description="Font size")] = 48,
    color: Annotated[str, Form(description="Hex color e.g. #FF0000")] = "#FF0000",
    angle: Annotated[int, Form(description="Angle in degrees")] = 45,
    webhook_url: Annotated[str | None, Form(description="Webhook URL for completion notification")] = None,
    key: dict = Depends(verify_api_key),
):
    job_id = new_job_id()
    endpoint = "/v1/pdf/watermark"
    file_size_bytes = 0
    tier = key.get("tier", "free")

    try:
        _, file_size_bytes = _validate_pdf(file)
        if not 0.0 <= opacity <= 1.0:
            abort(400, "opacity must be between 0.0 and 1.0", "INVALID_INPUT", job_id)

        content = await file.read()
        input_path = save_upload(content, job_id, "input.pdf")

        await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
        celery_app.send_task(
            "tasks.process_pdf",
            args=[job_id, "watermark", str(input_path), {
                "text": text,
                "opacity": opacity,
                "font_size": font_size,
                "color": color,
                "angle": angle,
                "output_ext": "pdf",
                "_webhook_url": webhook_url,
            }],
        )

        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 200)
        return {"job_id": job_id, "status": "queued", "poll_url": f"/v1/jobs/{job_id}"}
    except HTTPException as e:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, e.status_code)
        raise
    except Exception:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 500)
        raise


@router.post("/stamp")
async def pdf_stamp(
    file: Annotated[UploadFile, File(description="PDF file")],
    stamp: Annotated[UploadFile, File(description="Image stamp file")],
    position: Annotated[str, Form(description="Position: top-left, top-right, bottom-left, bottom-right, center")] = "bottom-right",
    scale: Annotated[float, Form(description="Scale 0.1-1.0")] = 0.2,
    webhook_url: Annotated[str | None, Form(description="Webhook URL for completion notification")] = None,
    key: dict = Depends(verify_api_key),
):
    job_id = new_job_id()
    endpoint = "/v1/pdf/stamp"
    total_bytes = 0
    tier = key.get("tier", "free")

    try:
        _, s1 = _validate_pdf(file)
        total_bytes += s1

        valid_positions = {"top-left", "top-right", "bottom-left", "bottom-right", "center"}
        if position not in valid_positions:
            abort(400, f"position must be one of: {valid_positions}", "INVALID_INPUT", job_id)
        if not 0.1 <= scale <= 1.0:
            abort(400, "scale must be between 0.1 and 1.0", "INVALID_INPUT", job_id)

        stamp.file.seek(0, 2)
        total_bytes += stamp.file.tell()
        stamp.file.seek(0)

        content = await file.read()
        input_path = save_upload(content, job_id, "input.pdf")
        stamp_ext = Path(stamp.filename or "stamp.png").suffix.lstrip(".").lower()
        stamp_path = save_upload(await stamp.read(), job_id, f"stamp.{stamp_ext}")

        await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
        celery_app.send_task(
            "tasks.process_pdf",
            args=[job_id, "stamp", str(input_path), {
                "stamp_path": str(stamp_path),
                "position": position,
                "scale": scale,
                "output_ext": "pdf",
                "_webhook_url": webhook_url,
            }],
        )

        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, total_bytes, 200)
        return {"job_id": job_id, "status": "queued", "poll_url": f"/v1/jobs/{job_id}"}
    except HTTPException as e:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, total_bytes, e.status_code)
        raise
    except Exception:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, total_bytes, 500)
        raise


@router.post("/encrypt")
async def pdf_encrypt(
    file: Annotated[UploadFile, File(description="PDF file to encrypt")],
    password: Annotated[str, Form(description="Encryption password")],
    owner_password: Annotated[str | None, Form(description="Owner password")] = None,
    permissions: Annotated[str | None, Form(description="Comma-separated: print,copy,edit")] = None,
    webhook_url: Annotated[str | None, Form(description="Webhook URL for completion notification")] = None,
    key: dict = Depends(verify_api_key),
):
    job_id = new_job_id()
    endpoint = "/v1/pdf/encrypt"
    file_size_bytes = 0
    tier = key.get("tier", "free")

    try:
        _, file_size_bytes = _validate_pdf(file)
        if len(password) < 4:
            abort(400, "password must be at least 4 characters", "INVALID_INPUT", job_id)

        content = await file.read()
        input_path = save_upload(content, job_id, "input.pdf")

        await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
        celery_app.send_task(
            "tasks.process_pdf",
            args=[job_id, "encrypt", str(input_path), {
                "password": password,
                "owner_password": owner_password,
                "permissions": permissions,
                "output_ext": "pdf",
                "_webhook_url": webhook_url,
            }],
        )

        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 200)
        return {"job_id": job_id, "status": "queued", "poll_url": f"/v1/jobs/{job_id}"}
    except HTTPException as e:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, e.status_code)
        raise
    except Exception:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 500)
        raise


@router.post("/decrypt")
async def pdf_decrypt(
    file: Annotated[UploadFile, File(description="Encrypted PDF file")],
    password: Annotated[str, Form(description="PDF password")],
    webhook_url: Annotated[str | None, Form(description="Webhook URL for completion notification")] = None,
    key: dict = Depends(verify_api_key),
):
    job_id = new_job_id()
    endpoint = "/v1/pdf/decrypt"
    file_size_bytes = 0
    tier = key.get("tier", "free")

    try:
        _, file_size_bytes = _validate_pdf(file)
        content = await file.read()
        input_path = save_upload(content, job_id, "input.pdf")

        await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
        celery_app.send_task(
            "tasks.process_pdf",
            args=[job_id, "decrypt", str(input_path), {
                "password": password,
                "output_ext": "pdf",
                "_webhook_url": webhook_url,
            }],
        )

        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 200)
        return {"job_id": job_id, "status": "queued", "poll_url": f"/v1/jobs/{job_id}"}
    except HTTPException as e:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, e.status_code)
        raise
    except Exception:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 500)
        raise


@router.post("/compress")
async def pdf_compress(
    file: Annotated[UploadFile, File(description="PDF file to compress")],
    quality: Annotated[str, Form(description="Quality: low, medium, high")] = "medium",
    webhook_url: Annotated[str | None, Form(description="Webhook URL for completion notification")] = None,
    key: dict = Depends(verify_api_key),
):
    job_id = new_job_id()
    endpoint = "/v1/pdf/compress"
    file_size_bytes = 0
    tier = key.get("tier", "free")

    try:
        _, file_size_bytes = _validate_pdf(file)
        if quality not in ("low", "medium", "high"):
            abort(400, "quality must be low, medium, or high", "INVALID_INPUT", job_id)

        content = await file.read()
        input_path = save_upload(content, job_id, "input.pdf")

        await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
        celery_app.send_task(
            "tasks.process_pdf",
            args=[job_id, "compress", str(input_path), {
                "quality": quality,
                "output_ext": "pdf",
                "_webhook_url": webhook_url,
            }],
        )

        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 200)
        return {"job_id": job_id, "status": "queued", "poll_url": f"/v1/jobs/{job_id}"}
    except HTTPException as e:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, e.status_code)
        raise
    except Exception:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 500)
        raise


@router.post("/metadata")
async def pdf_metadata(
    file: Annotated[UploadFile, File(description="PDF file")],
    title: Annotated[str | None, Form(description="Title")] = None,
    author: Annotated[str | None, Form(description="Author")] = None,
    subject: Annotated[str | None, Form(description="Subject")] = None,
    keywords: Annotated[str | None, Form(description="Keywords")] = None,
    creator: Annotated[str | None, Form(description="Creator")] = None,
    webhook_url: Annotated[str | None, Form(description="Webhook URL for completion notification")] = None,
    key: dict = Depends(verify_api_key),
):
    job_id = new_job_id()
    endpoint = "/v1/pdf/metadata"
    file_size_bytes = 0
    tier = key.get("tier", "free")

    try:
        _, file_size_bytes = _validate_pdf(file)
        content = await file.read()
        input_path = save_upload(content, job_id, "input.pdf")

        metadata_updates = {}
        if title is not None:
            metadata_updates["title"] = title
        if author is not None:
            metadata_updates["author"] = author
        if subject is not None:
            metadata_updates["subject"] = subject
        if keywords is not None:
            metadata_updates["keywords"] = keywords
        if creator is not None:
            metadata_updates["creator"] = creator

        if metadata_updates:
            await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
            celery_app.send_task(
                "tasks.process_pdf",
                args=[job_id, "write_metadata", str(input_path), {
                    "metadata": metadata_updates,
                    "output_ext": "pdf",
                    "_webhook_url": webhook_url,
                }],
            )
            await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 200)
            return {"job_id": job_id, "status": "queued", "poll_url": f"/v1/jobs/{job_id}"}
        else:
            result = read_metadata(str(input_path))
            await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
            await update_job(job_id, "done", result_url=None, filename="input.pdf")
            await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 200)
            return {"job_id": job_id, "status": "done", "metadata": result, "filename": "input.pdf"}
    except HTTPException as e:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, e.status_code)
        raise
    except Exception:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 500)
        raise


@router.post("/bookmarks")
async def pdf_bookmarks(
    file: Annotated[UploadFile, File(description="PDF file")],
    bookmarks: Annotated[str | None, Form(description="JSON array of bookmarks")] = None,
    webhook_url: Annotated[str | None, Form(description="Webhook URL for completion notification")] = None,
    key: dict = Depends(verify_api_key),
):
    job_id = new_job_id()
    endpoint = "/v1/pdf/bookmarks"
    file_size_bytes = 0
    tier = key.get("tier", "free")

    try:
        _, file_size_bytes = _validate_pdf(file)
        content = await file.read()
        input_path = save_upload(content, job_id, "input.pdf")

        if bookmarks:
            parsed = json.loads(bookmarks)
            if not isinstance(parsed, list):
                abort(400, "bookmarks must be a JSON array", "INVALID_INPUT", job_id)
            await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
            celery_app.send_task(
                "tasks.process_pdf",
                args=[job_id, "write_bookmarks", str(input_path), {
                    "bookmarks": parsed,
                    "output_ext": "pdf",
                    "_webhook_url": webhook_url,
                }],
            )
            await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 200)
            return {"job_id": job_id, "status": "queued", "poll_url": f"/v1/jobs/{job_id}"}
        else:
            result = get_bookmarks(str(input_path))
            await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
            await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 200)
            return {"job_id": job_id, "status": "done", "bookmarks": result, "filename": "input.pdf"}
    except json.JSONDecodeError:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 400)
        abort(400, "Invalid JSON for bookmarks", "INVALID_INPUT", job_id)
    except HTTPException as e:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, e.status_code)
        raise
    except Exception:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 500)
        raise


@router.post("/flatten")
async def pdf_flatten(
    file: Annotated[UploadFile, File(description="PDF file to flatten")],
    webhook_url: Annotated[str | None, Form(description="Webhook URL for completion notification")] = None,
    key: dict = Depends(verify_api_key),
):
    job_id = new_job_id()
    endpoint = "/v1/pdf/flatten"
    file_size_bytes = 0
    tier = key.get("tier", "free")

    try:
        _, file_size_bytes = _validate_pdf(file)
        content = await file.read()
        input_path = save_upload(content, job_id, "input.pdf")

        await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
        celery_app.send_task(
            "tasks.process_pdf",
            args=[job_id, "flatten", str(input_path), {
                "output_ext": "pdf",
                "_webhook_url": webhook_url,
            }],
        )

        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 200)
        return {"job_id": job_id, "status": "queued", "poll_url": f"/v1/jobs/{job_id}"}
    except HTTPException as e:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, e.status_code)
        raise
    except Exception:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 500)
        raise


@router.post("/pdfa")
async def pdf_pdfa(
    file: Annotated[UploadFile, File(description="PDF file to convert to PDF/A")],
    standard: Annotated[str, Form(description="PDF/A standard: PDF/A-1b, PDF/A-2b, PDF/A-3b")] = "PDF/A-2b",
    webhook_url: Annotated[str | None, Form(description="Webhook URL for completion notification")] = None,
    key: dict = Depends(verify_api_key),
):
    job_id = new_job_id()
    endpoint = "/v1/pdf/pdfa"
    file_size_bytes = 0
    tier = key.get("tier", "free")

    try:
        _, file_size_bytes = _validate_pdf(file)
        valid_standards = {"PDF/A-1b", "PDF/A-2b", "PDF/A-3b"}
        if standard not in valid_standards:
            abort(400, f"standard must be one of: {valid_standards}", "INVALID_INPUT", job_id)

        content = await file.read()
        input_path = save_upload(content, job_id, "input.pdf")

        await create_job(job_id, endpoint=endpoint, webhook_url=webhook_url)
        celery_app.send_task(
            "tasks.process_pdf",
            args=[job_id, "pdfa", str(input_path), {
                "standard": standard,
                "output_ext": "pdfa",
                "_webhook_url": webhook_url,
            }],
        )

        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 200)
        return {"job_id": job_id, "status": "queued", "poll_url": f"/v1/jobs/{job_id}"}
    except HTTPException as e:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, e.status_code)
        raise
    except Exception:
        await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, file_size_bytes, 500)
        raise